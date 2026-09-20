import argparse
import csv
from io import BytesIO
from itertools import combinations
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parent.parent
STUDENT_CSV = PROJECT_ROOT / "private-data" / "student-roster.csv"
SCHEDULE_MANIFEST = PROJECT_ROOT / "data" / "class-schedules.json"
OUTPUT_PATH = PROJECT_ROOT / "private-data" / "student-calendars.json"
DAYS = ("Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato")
CLASS_PATTERN = re.compile(r"^([1-5])([A-Z])(\d*)$")
SPECIALIZATIONS = {
    "1": "MEC",
    "2": "INF",
    "5": "LOG",
    "6": "BS",
}
ROOM_SUFFIX_PATTERN = re.compile(
    r"(?P<room>"
    r"LAB(?:[\s_-]*[A-Z0-9]+(?:[\s_/-]*[A-Z0-9]+)*)?"
    r"|[A-Z]{1,5}\s*\d[A-Z0-9_/-]*"
    r"|A\s*\d{1,3}[A-Z]?"
    r"|AOL"
    r"|AODT"
    r")$",
    re.IGNORECASE,
)
ROOM_CORRECTIONS = {"AOL": "A01", "AODT": "A01"}
GYM_LOCATION_PATTERN = re.compile(
    r"(?:CATELLANI\s*\d+|SAN\s*PAOLO\s*\d+|VERDE\??)",
    re.IGNORECASE,
)
SUBJECT_CORRECTIONS = {
    "INGLE SE": "INGLESE",
    "MATE MATICA": "MATEMATICA",
}


def normalize_subject(subject):
    normalized = re.sub(r"\s+", " ", subject).strip()
    for recognized, corrected in SUBJECT_CORRECTIONS.items():
        normalized = re.sub(
            rf"\b{re.escape(recognized)}\b",
            corrected,
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


def add_subject_and_room(lesson):
    raw_text = lesson.get("text", "").strip()
    gym_location = GYM_LOCATION_PATTERN.search(raw_text)
    if gym_location:
        location = re.sub(r"\s+", " ", gym_location.group()).strip().upper()
        location = re.sub(r"^SAN\s*PAOLO", "SAN PAOLO", location)
        subject = raw_text[:gym_location.start()].strip(" \t-")
        subject = re.sub(r"\bA{1,2}PAL\b$", "", subject, flags=re.IGNORECASE).strip()
        lesson["subject"] = normalize_subject(subject)
        lesson["room"] = f"PALESTRA {location}"
        return

    match = ROOM_SUFFIX_PATTERN.search(raw_text)
    if not match:
        lesson["subject"] = normalize_subject(raw_text)
        lesson["room"] = "DA VERIFICARE"
        return

    room = match.group("room").strip()
    normalized_room = re.sub(r"\s+", "", room).upper()
    normalized_room = ROOM_CORRECTIONS.get(normalized_room, normalized_room)
    if normalized_room.startswith("LAB") and normalized_room[3:4].isalpha():
        normalized_room = "LAB_" + normalized_room[3:]
    lesson["room"] = normalized_room
    lesson["subject"] = normalize_subject(raw_text[:match.start()].strip(" \t-"))


def timetable_class(roster_class):
    code = roster_class.split(" - ", 1)[0].strip().upper()
    match = CLASS_PATTERN.fullmatch(code)
    if not match:
        return None

    year, section, suffix = match.groups()
    if year in {"1", "2"}:
        return f"{year}{section}" if not suffix else None
    if year == "3" and section == "C" and suffix == "5":
        return "3C LOG/INF"
    if suffix:
        specialization = SPECIALIZATIONS.get(suffix)
        return f"{year}{section} {specialization}" if specialization else None
    specialization = "EL/BA" if section == "A" else "AU"
    return f"{year}{section} {specialization}"


def grouped_positions(values, threshold, minimum_gap=2):
    positions = [index for index, value in enumerate(values) if value >= threshold]
    groups = []
    for position in positions:
        if not groups or position - groups[-1][-1] > minimum_gap:
            groups.append([])
        groups[-1].append(position)
    return [round(sum(group) / len(group)) for group in groups]


def dark_pixel_ratio(image, start, end, coordinate, vertical):
    if vertical:
        pixels = [image.getpixel((coordinate, point)) for point in range(start, end)]
    else:
        pixels = [image.getpixel((point, coordinate)) for point in range(start, end)]
    return sum(pixel < 145 for pixel in pixels) / max(1, len(pixels))


def detect_grid(image):
    width, height = image.size
    vertical_start = round(height * 0.08)
    vertical_end = round(height * 0.94)
    vertical_ratios = [
        sum(image.getpixel((x, y)) < 145 for y in range(vertical_start, vertical_end))
        / (vertical_end - vertical_start)
        for x in range(width)
    ]
    vertical_lines = [
        x
        for x in grouped_positions(vertical_ratios, 0.8)
        if width * 0.04 < x < width * 0.98
    ]
    if len(vertical_lines) < len(DAYS) + 1:
        raise ValueError(
            f"attese almeno 7 linee verticali della tabella, "
            f"trovate {len(vertical_lines)}"
        )
    if len(vertical_lines) > len(DAYS) + 1:
        first, last = vertical_lines[0], vertical_lines[-1]
        expected_width = (last - first) / len(DAYS)
        vertical_lines = min(
            combinations(vertical_lines, len(DAYS) + 1),
            key=lambda lines: sum(
                (right - left - expected_width) ** 2
                for left, right in zip(lines, lines[1:])
            ),
        )

    grid_top = round(height * 0.08)
    grid_bottom = round(height * 0.94)
    day_segments = []
    for left, right in zip(vertical_lines, vertical_lines[1:]):
        ratios = [
            dark_pixel_ratio(image, left + 2, right - 2, y, vertical=False)
            for y in range(grid_top, grid_bottom)
        ]
        local_lines = [
            grid_top + position
            for position in grouped_positions(ratios, 0.55)
        ]
        if len(local_lines) < 2:
            raise ValueError("impossibile rilevare le righe orarie")
        day_segments.append((left, right, local_lines))

    grid_top = min(lines[0] for _, _, lines in day_segments)
    grid_bottom = max(lines[-1] for _, _, lines in day_segments)
    if grid_bottom <= grid_top:
        raise ValueError("limiti della griglia oraria non validi")
    return vertical_lines, (grid_top, grid_bottom), day_segments


def format_time(hour):
    return (datetime(2000, 1, 1, 8, 0) + timedelta(hours=hour)).strftime("%H:%M")


def ocr_cell(image, tesseract, language, left, top, right, bottom, tessdata_dir):
    crop = image.crop((left + 4, top + 4, right - 4, bottom - 4))
    if crop.width < 5 or crop.height < 5:
        return ""
    crop = crop.resize((crop.width * 3, crop.height * 3), Image.Resampling.LANCZOS)
    encoded_image = BytesIO()
    crop.convert("RGB").save(encoded_image, format="PNG")
    command = [tesseract]
    if tessdata_dir:
        command.extend(["--tessdata-dir", str(tessdata_dir)])
    command.extend(
        [
            "stdin",
            "stdout",
            "--psm",
            "6",
            "-l",
            language,
        ]
    )
    result = subprocess.run(
        command,
        input=encoded_image.getvalue(),
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            result.stderr.decode("utf-8", errors="replace").strip()
            or "errore Tesseract durante la lettura della cella"
        )
    return " ".join(result.stdout.decode("utf-8", errors="replace").split())


def extract_class_calendar(image_path, tesseract, language, tessdata_dir=None):
    with Image.open(image_path) as source:
        image = source.convert("L")
    _, (first_mark, last_mark), day_segments = detect_grid(image)
    total_hours = 7
    lessons = []

    for day_index, (left, right, boundaries) in enumerate(day_segments):
        for top, bottom in zip(boundaries, boundaries[1:]):
            text = ocr_cell(
                image,
                tesseract,
                language,
                left,
                top,
                right,
                bottom,
                tessdata_dir,
            )
            if not text:
                continue
            start_hour = round((top - first_mark) / (last_mark - first_mark) * total_hours)
            end_hour = round((bottom - first_mark) / (last_mark - first_mark) * total_hours)
            if end_hour <= start_hour:
                raise ValueError(f"intervallo orario non valido per {DAYS[day_index]}")
            lessons.append(
                {
                    "day": DAYS[day_index],
                    "start": format_time(start_hour),
                    "end": format_time(end_hour),
                    "text": text,
                }
            )
    return lessons


def resolve_tesseract(requested_path):
    executable = requested_path or shutil.which("tesseract")
    if not executable and sys.platform == "win32":
        windows_installation = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if windows_installation.is_file():
            executable = str(windows_installation)
    if not executable:
        raise RuntimeError(
            "Tesseract OCR non trovato. Installa Tesseract OCR oppure specifica "
            "il percorso con --tesseract."
        )
    version = subprocess.run(
        [executable, "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    if version.returncode:
        raise RuntimeError(f"Impossibile avviare Tesseract: {version.stderr.strip()}")
    return executable


def resolve_tessdata_dir(tesseract, language):
    candidates = [
        Path.home() / "AppData/Local/Tesseract-OCR/tessdata",
        Path(tesseract).resolve().parent / "tessdata",
    ]
    for candidate in candidates:
        if candidate.is_dir() and (candidate / f"{language}.traineddata").is_file():
            return candidate
    return None


def project_asset_path(path):
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_roster(csv_path, schedules_by_name):
    students = []
    with csv_path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";")
        required = {"Nome", "Cognome", "Classe"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(
                "Il CSV deve contenere le colonne Nome, Cognome e Classe "
                "separate da punto e virgola."
            )
        for row in reader:
            first_name = (row.get("Nome") or "").strip()
            last_name = (row.get("Cognome") or "").strip()
            roster_class = (row.get("Classe") or "").strip()
            if not first_name or not last_name or not roster_class:
                continue
            schedule_name = timetable_class(roster_class)
            students.append(
                {
                    "name": f"{first_name} {last_name}",
                    "class": roster_class,
                    "schedule_class": (
                        schedule_name if schedule_name in schedules_by_name else None
                    ),
                }
            )
    if not students:
        raise ValueError("Il CSV non contiene studenti con nome e classe.")
    return students


def build_calendars(
    csv_path,
    manifest_path,
    output_path,
    tesseract_path,
    language,
    refresh=False,
):
    tesseract = resolve_tesseract(tesseract_path)
    tessdata_dir = resolve_tessdata_dir(tesseract, language)
    language_command = [tesseract]
    if tessdata_dir:
        language_command.extend(["--tessdata-dir", str(tessdata_dir)])
    language_command.append("--list-langs")
    available_languages = subprocess.run(
        language_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if available_languages.returncode:
        raise RuntimeError(
            f"Impossibile leggere i language pack di Tesseract: "
            f"{available_languages.stderr.strip()}"
        )
    installed_languages = set(available_languages.stdout.splitlines()[1:])
    if language not in installed_languages:
        raise RuntimeError(
            f"Language pack '{language}' non installato. "
            "Installa i dati OCR italiani (ita) e ripeti il comando."
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schedules = {
        item["name"]: item
        for item in manifest.get("classes", [])
        if item.get("status") == "done" and item.get("local_file")
    }
    if not schedules:
        raise ValueError("Il manifest non contiene PNG di orari scaricati.")

    calendars = {}
    if output_path.is_file() and not refresh:
        try:
            previous = json.loads(output_path.read_text(encoding="utf-8"))
            previous_classes = previous.get("classes", {})
            calendars = {
                name: item
                for name, item in previous_classes.items()
                if name in schedules
                and item.get("status") == "done"
                and item.get("lessons")
            }
            if calendars:
                print(f"Riprendo gli OCR già validi per {len(calendars)} classi.")
        except (OSError, json.JSONDecodeError, AttributeError):
            calendars = {}

    for index, (name, schedule) in enumerate(schedules.items(), start=1):
        if name in calendars:
            continue
        image_path = Path(schedule["local_file"])
        if not image_path.is_absolute():
            image_path = PROJECT_ROOT / image_path
        try:
            lessons = extract_class_calendar(
                image_path,
                tesseract,
                language,
                tessdata_dir,
            )
            if not lessons:
                raise ValueError("nessuna lezione riconosciuta")
            for lesson in lessons:
                add_subject_and_room(lesson)
            calendars[name] = {
                "status": "done",
                "local_file": project_asset_path(image_path),
                "lessons": lessons,
            }
            print(f"{name} + fatto ({index}/{len(schedules)})")
        except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as error:
            calendars[name] = {"status": "failed", "error": str(error), "lessons": []}
            print(f"{name} + non fatto ({error})", file=sys.stderr)

    students = load_roster(csv_path, schedules)
    output = {
        "source": str(manifest.get("source_page", "")),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "note": (
            "Calendari derivati localmente tramite OCR dai PNG degli orari. "
            "Il testo riconosciuto può contenere errori e va confrontato con "
            "l'immagine ufficiale. Non contiene email o credenziali."
        ),
        "classes": calendars,
        "students": students,
    }
    for calendar in calendars.values():
        for lesson in calendar.get("lessons", []):
            add_subject_and_room(lesson)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    finished = sum(item["status"] == "done" for item in calendars.values())
    print(
        f"Completato: OCR riuscito per {finished}/{len(calendars)} classi. "
        f"Studenti inclusi: {len(students)}. File locale: {output_path}"
    )
    return finished == len(calendars)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Estrae con OCR le lezioni dai PNG delle classi e crea un indice "
            "locale per cercare il calendario settimanale di uno studente."
        )
    )
    parser.add_argument("--students", type=Path, default=STUDENT_CSV)
    parser.add_argument("--schedules", type=Path, default=SCHEDULE_MANIFEST)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--tesseract", help="Percorso a tesseract.exe se non è nel PATH.")
    parser.add_argument("--language", default="ita", help="Language pack OCR (default: ita).")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Riesegui l'OCR di tutte le classi invece di riprendere i risultati.",
    )
    args = parser.parse_args()

    try:
        complete = build_calendars(
            args.students,
            args.schedules,
            args.output,
            args.tesseract,
            args.language,
            args.refresh,
        )
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
