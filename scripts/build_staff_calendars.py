import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from pathlib import Path

from PIL import Image

from build_student_calendars import (
    DAYS,
    detect_grid,
    format_time,
    resolve_tesseract,
    resolve_tessdata_dir,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "private-data" / "staff-timetables.json"
DEFAULT_CLASS_MANIFEST = PROJECT_ROOT / "data" / "class-schedules.json"
DEFAULT_STUDENT_CALENDARS = PROJECT_ROOT / "private-data" / "student-calendars.json"

ROOM_CORRECTIONS = {
    "APNI1": "APN1",
    "ASNI1": "ASN1",
    "ASNS5": "ASN5",
    "TLAS": "TLA5",
    "MLAS5S_CNC": "MLA5_CNC",
    "MLAS_CNC": "MLA5_CNC",
    "TLA4LAB_LOG3": "TLA4_LAB_LOG3",
    "TLC4__GDP": "TLC4_GDP",
    "LOO06N_SIS2": "LOO6N_SIS2",
    "LO02N_INF1": "LOO2N_INF1",
    "LOO3N_S1S1": "LOO3N_SIS1",
    "LAB_02": "LAB02",
    "AO003N": "A003N",
    "TLC1_MIS_EN": "TLC1_SIS_EN",
    "ATNI": "ATN1",
    "ASNS": "ASN5",
    "APNS3": "APN3",
    "ASNI": "ASN1",
    "L0O01N_TLC": "LOO1N_TLC",
}
AIRC_CORRECTIONS = {
    "AIRC 3B LO/4C ME": "AIRC 3B LOG / 4C MEC",
}
SUBJECT_CORRECTIONS = (
    (r"\bLE\s*TTE\s*RE\b", "LETTERE"),
    (r"\bLETTE\s*RE\b", "LETTERE"),
    (r"\bINGLE\s*SE\b", "INGLESE"),
    (r"\bMATE\s*MATICA\b", "MATEMATICA"),
    (r"\bMICRO\s*BIO\s*LO\s*GIA\b", "MICROBIOLOGIA"),
    (r"\bMICROBIOLO\s*GIA\b", "MICROBIOLOGIA"),
    (r"\bINFOR\s*MATICA\b", "INFORMATICA"),
    (r"\bSCIE\s*NZE\b", "SCIENZE"),
    (r"\bSISTEMI\s+E\s+NEL\b", "SISTEMI ENEL"),
    (r"\bSISTE\s*MI\b", "SISTEMI"),
    (r"\bTE\s*CNOL\.", "TECNOL."),
    (r"\bTE\s*CN\.", "TECN."),
    (r"\bME\s*C/CANICA\b", "MECCANICA"),
    (r"\bME\s*CCANICA\b", "MECCANICA"),
    (r"\bENE\s*L\b", "ENEL"),
    (r"\bGE\s*ST\.", "GEST."),
    (r"\bCOMPL\.\s*MATE\s*M\.", "COMPL. MATEM."),
    (r"\bFOND\.\s*ME\s*C/DIS\.", "FOND. MEC/DIS."),
    (r"\bFOND\.\s*MECI/DIS\.", "FOND. MEC/DIS."),
    (r"\bTECN\.E\b", "TECN. E"),
    (r"\bDISEGNOE\b", "DISEGNO E"),
    (r"\(LO\s*G\)", "(LOG)"),
    (r"\(FI\s*SICA\)", "(FISICA)"),
    (r"\bDISPO\s*SIZIONE\b", "DISPOSIZIONE"),
    (r"\bVICEPRE\s*SIDE\s*NZA\b", "VICEPRESIDENZA"),
    (r"\bUFFICIO\s+TE\s+CNICO\b", "UFFICIO TECNICO"),
    (r"\bREFERENTE\s+F\s+SL\b", "REFERENTE FSL"),
    (r"\bPROGE\s*TTAZIONE\b", "PROGETTAZIONE"),
    (r"\bTECNOL\.\s*ME\s*CCANICHE\b", "TECNOL. MECCANICHE"),
    (r"\bDISE\s*GNO\s+E\s+PROG\.", "DISEGNO E PROG."),
    (r"\bLO\s*GISTICA\b", "LOGISTICA"),
)
NON_TEACHING_SUBJECTS = {
    "VICEPRESIDENZA",
    "SUPPORTO VP",
    "UFFICIO TECNICO",
    "REFERENTE FSL",
    "DISPOSIZIONE",
    "PROGETTAZIONE",
}
ROOM_PREFIXES = (
    "MLA",
    "TLA",
    "TLB",
    "TLC",
    "LOO",
    "LO",
    "LIN",
    "ELLAN",
    "ARLOG",
    "AL",
    "AT",
    "AF",
    "AI",
    "MAGIK",
)
CLASS_TOKEN = re.compile(
    r"\b([1-5])\s*([A-Z])(?:\s*(LOG/INF|EL/BA|MEC|INF|LOG|AU|BS|BA|EL|EU))?\b"
)


def load_known_classes(path):
    manifest = json.loads(path.read_text(encoding="utf-8"))
    classes = {
        item["name"]
        for item in manifest.get("classes", [])
        if item.get("status") == "done" and item.get("name")
    }
    if not classes:
        raise ValueError(f"Il manifest delle classi non contiene classi: {path}")
    return classes


def clean_line(line):
    return " ".join(str(line).replace("|", "/").split()).strip()


def fix_elba(text):
    text = text.upper()
    for source, target in (
        ("EL_BA", "EL/BA"),
        ("EL/IBA", "EL/BA"),
        ("ELUBA", "EL/BA"),
        ("EU/BA", "EL/BA"),
        ("EUBA", "EL/BA"),
    ):
        text = text.replace(source, target)
    text = re.sub(r"\bE\s*L\s*/\s*BA\b", "EL/BA", text)
    text = re.sub(r"\bE\s*L\s*I?BA\b", "EL/BA", text)
    text = re.sub(r"\bE\s*UBA\b", "EL/BA", text)
    text = re.sub(r"\bE\s*LIBA\b", "EL/BA", text)
    return text


def fix_leading_s(text):
    text = re.sub(r"\bS([A-D])(?=[\s/]|$)", r"5\1", text)
    text = re.sub(r"\bS([A-D])([A-Z])", r"5\1\2", text)
    text = re.sub(r"\bS(?=\d)", "", text)
    text = re.sub(r"(\d)S([A-Z])", r"\1\2", text)
    return text


def insert_class_spaces(text):
    text = re.sub(r"\b([1-5])\s*([A-Z])\s*([A-Z]{2,})\b", r"\1\2 \3", text)
    text = re.sub(
        r"\b([1-5])\s*([A-Z])\s*(LOG/INF|EL/BA|MEC|INF|LOG|AU|BS|BA)\b",
        r"\1\2 \3",
        text,
    )
    return text


def normalize_class(line, known_classes, allow_combined=False):
    original = clean_line(line)
    if not original:
        return None
    text = fix_elba(original)
    text = fix_leading_s(text)

    if "<" in text or ">" in text:
        if not allow_combined:
            return None
        text = text.replace("<", " ").replace(">", " ")
        text = insert_class_spaces(text)
        tokens = []
        for match in CLASS_TOKEN.finditer(text):
            year, section, specialization = match.groups()
            token = f"{year}{section}" + (
                f" {specialization}" if specialization else ""
            )
            if token not in tokens:
                tokens.append(token)
        return " / ".join(tokens) if tokens else None

    if re.match(r"^AIRC\b", text, re.IGNORECASE):
        text = insert_class_spaces(text)
        text = re.sub(r"\s+", " ", text).strip()
        return AIRC_CORRECTIONS.get(text, text)

    compact = re.sub(r"[^A-Z0-9/]", "", text)
    if re.fullmatch(r"\d{2}", compact):
        compact = compact[0] + {
            "1": "L",
            "8": "B",
            "0": "O",
        }.get(compact[1], compact[1])

    match = re.fullmatch(
        r"([1-5])([A-Z])(LOG/INF|EL/BA|MEC|INF|LOG|AU|BS|BA|EL|EU)?",
        compact,
    )
    if not match:
        return None
    year, section, specialization = match.groups()
    if specialization in {"EL", "EU"}:
        specialization = "EL/BA"
    candidate = f"{year}{section}" + (
        f" {specialization}" if specialization else ""
    )
    if candidate in known_classes:
        return candidate
    if specialization == "BA":
        return candidate
    if not specialization and year in {"3", "4", "5"}:
        options = [
            name
            for name in known_classes
            if name.startswith(f"{year}{section} ")
        ]
        if len(options) == 1:
            return options[0]
    return None


def looks_like_room(line):
    text = clean_line(line).upper()
    if not text:
        return False
    if text.startswith(("AAPAL", "PALESTRA")):
        return True
    if text.startswith(("AIRC", "ALTERN")):
        return False
    if re.fullmatch(r"Z\s*DISP\s*(?:\d+|PAGO\d+)", text):
        return True
    if re.fullmatch(r"A\s*\d+[A-Z]?(?:\s+A\s*\d+[A-Z]?)+", text):
        return True
    if "," in text and all(looks_like_room(part) for part in text.split(",")):
        return True
    compact = re.sub(r"[^A-Z0-9_/]", "", text)
    if re.fullmatch(r"Z(?:DISP|DSP)(?:\d+|PAGO\d+)", compact):
        return True
    if compact in ROOM_CORRECTIONS or compact == "DAVERIFICARE":
        return True
    if re.fullmatch(r"LAB_?[A-Z0-9_/]+", compact):
        return True
    if re.fullmatch(r"A[0-9A-Z]{1,6}", compact) and any(
        character.isdigit() for character in compact
    ):
        return True
    if any(compact.startswith(prefix) for prefix in ROOM_PREFIXES):
        if any(character.isdigit() for character in compact):
            return True
    return False


def normalize_room(line):
    text = clean_line(line).upper()
    if "," in text:
        parts = [normalize_room(part) for part in text.split(",")]
        return " / ".join(part for part in parts if part)
    multiple_rooms = re.fullmatch(
        r"A\s*\d+[A-Z]?(?:\s+A\s*\d+[A-Z]?)+", text
    )
    if multiple_rooms:
        rooms = re.findall(r"A\s*\d+[A-Z]?", text)
        return " / ".join(re.sub(r"\s+", "", room) for room in rooms)
    compact = re.sub(r"[^A-Z0-9_/]", "", text)
    disp_match = re.fullmatch(r"Z(?:DISP|DSP)(PAGO\d+|\d+)", compact)
    if disp_match:
        return f"Z DISP {disp_match.group(1)}"
    if text.startswith(("AAPAL", "PALESTRA")):
        compact = re.sub(r"[^A-Z0-9]", "", text)
        match = re.match(
            r"^(?:AAPAL|PALESTRA)"
            r"(CATELLANI|CATELLAN|SANPAOLO|SANPAQLO|VERDE|MAGIK)(\d?)$",
            compact,
        )
        if match:
            place, number = match.groups()
            if place in {"CATELLANI", "CATELLAN"}:
                return "PALESTRA CATELLANI" + (f" {number}" if number else "")
            if place in {"SANPAOLO", "SANPAQLO"}:
                return "PALESTRA SAN PAOLO" + (f" {number}" if number else "")
            if place == "VERDE":
                return "PALESTRA VERDE" + (f" {number}" if number else "")
            if place == "MAGIK":
                return f"MAGIK{number}"
        return text

    compact = re.sub(r"[^A-Z0-9_/]", "", text)
    compact = re.sub(r"_+", "_", compact).strip("_")
    return ROOM_CORRECTIONS.get(compact, compact)


def extract_room_suffix(line):
    text = clean_line(line).upper()
    room_token = (
        r"(?:LAB[_ ]?[A-Z0-9]+(?:[_/-][A-Z0-9]+)*"
        r"|A\s*\d+[A-Z]?\s+A\s*\d+[A-Z]?"
        r"|A\s*\d+[A-Z]?"
        r"|(?:APN|ASN|ATN|AFN|AIN|TLA|TLB|TLC|LOO|LO|MLA|MAGIK)"
        r"[A-Z0-9]*\d[A-Z0-9_/-]*"
        r"|ATNI|ASNI|ASNS|APNS\d*|L0O01N_TLC"
        r"|Z\s*(?:DISP|DSP)\s*(?:\d+|PAGO\d*))"
    )
    match = re.search(
        rf"(?P<room>{room_token}(?:\s*,\s*{room_token})*)$",
        text,
    )
    if not match:
        return text, None
    room = normalize_room(match.group("room"))
    return text[:match.start()].strip(), room


def normalize_subject(line):
    text = clean_line(line).upper()
    for pattern, replacement in SUBJECT_CORRECTIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\s+AIRC$", "", text)
    text = re.sub(r"\s+A{1,2}PAL$", "", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_class_from_text(line, known_classes):
    text = insert_class_spaces(fix_leading_s(fix_elba(clean_line(line))))
    for match in CLASS_TOKEN.finditer(text):
        candidate = normalize_class(
            match.group(0), known_classes, allow_combined=True
        )
        if candidate:
            return candidate, text, match.start(), match.end()
    return None, text, None, None


def strip_coteacher_suffix(text):
    words = text.split()
    for count in (2, 3):
        if len(words) <= count:
            continue
        surname_words = words[-count:-1]
        initial = words[-1].rstrip(".")
        if not re.fullmatch(r"[A-Z]", initial):
            continue
        if not all(re.fullmatch(r"[A-Z][A-Z'-]{2,}", word) for word in surname_words):
            continue
        prefix = words[:-count]
        if prefix and prefix[-1].upper() in {"DE", "DEL", "DI", "DA", "LA"}:
            prefix = prefix[:-1]
        return " ".join(prefix).strip()
    return text.strip()


def parse_staff_cell(lines, known_classes):
    cleaned = [clean_line(line) for line in lines if clean_line(line)]
    room = None
    if cleaned and looks_like_room(cleaned[-1]):
        room = normalize_room(cleaned.pop())
    elif cleaned:
        prefix, room = extract_room_suffix(cleaned[-1])
        if room:
            if prefix:
                cleaned[-1] = prefix
            else:
                cleaned.pop()

    class_name = None
    class_source = None
    class_span = None
    for index in range(len(cleaned) - 1, -1, -1):
        candidate, prepared, start, end = extract_class_from_text(
            cleaned[index], known_classes
        )
        if candidate:
            class_name = candidate
            class_source = (index, prepared)
            class_span = (start, end)
            cleaned.pop(index)
            break
        candidate = normalize_class(
            cleaned[index], known_classes, allow_combined=True
        )
        if candidate:
            class_name = candidate
            cleaned.pop(index)
            break

    if class_source and not cleaned:
        _, prepared = class_source
        start, _ = class_span
        subject = strip_coteacher_suffix(prepared[:start].strip())
        subject = normalize_subject(subject) if subject else "DA VERIFICARE"
    else:
        subject = normalize_subject(cleaned[0]) if cleaned else "DA VERIFICARE"
    notes = cleaned[1:] if len(cleaned) > 1 else []
    non_teaching = subject in NON_TEACHING_SUBJECTS
    return {
        "subject": subject,
        "class": class_name or ("" if non_teaching else "DA VERIFICARE"),
        "room": room or ("" if non_teaching else "DA VERIFICARE"),
        "notes": notes,
    }


def ocr_cell_lines(
    image,
    tesseract,
    language,
    tessdata_dir,
    left,
    top,
    right,
    bottom,
):
    crop = image.crop((left + 4, top + 4, right - 4, bottom - 4))
    if crop.width < 5 or crop.height < 5:
        return []
    if sum(crop.histogram()[:200]) < 8:
        return []
    crop = crop.resize(
        (crop.width * 4, crop.height * 4),
        Image.Resampling.LANCZOS,
    )
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
    return [
        line.strip()
        for line in result.stdout.decode("utf-8", errors="replace").splitlines()
        if line.strip()
    ]


def extract_staff_calendar(
    image_path,
    tesseract,
    language,
    tessdata_dir,
    known_classes,
):
    with Image.open(image_path) as source:
        image = source.convert("L")
    _, (first_mark, last_mark), day_segments = detect_grid(image)
    total_hours = 7
    lessons = []

    for day_index, (left, right, boundaries) in enumerate(day_segments):
        for top, bottom in zip(boundaries, boundaries[1:]):
            lines = ocr_cell_lines(
                image,
                tesseract,
                language,
                tessdata_dir,
                left,
                top,
                right,
                bottom,
            )
            if not lines:
                continue
            start_hour = round(
                (top - first_mark) / (last_mark - first_mark) * total_hours
            )
            end_hour = round(
                (bottom - first_mark) / (last_mark - first_mark) * total_hours
            )
            if end_hour <= start_hour:
                raise ValueError(f"intervallo orario non valido per {DAYS[day_index]}")
            parsed = parse_staff_cell(lines, known_classes)
            lesson = {
                "day": DAYS[day_index],
                "start": format_time(start_hour),
                "end": format_time(end_hour),
                "text": " ".join(lines),
                "subject": parsed["subject"],
                "class": parsed["class"],
                "room": parsed["room"],
            }
            if parsed["notes"]:
                lesson["notes"] = parsed["notes"]
            lessons.append(lesson)
    return lessons


def save_manifest(path, manifest):
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def match_key(value):
    return re.sub(r"[^A-Z0-9]", "", normalize_subject(value))


def build_student_lesson_index(path):
    if not path or not path.is_file():
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    index = {}
    for class_name, record in manifest.get("classes", {}).items():
        for lesson in record.get("lessons", []):
            key = (
                lesson.get("day"),
                lesson.get("start"),
                lesson.get("end"),
            )
            index.setdefault(key, []).append(
                (
                    class_name,
                    match_key(lesson.get("subject", "")),
                    match_key(lesson.get("room", "")),
                )
            )
    return index


def normalize_existing_lesson_rooms(teachers):
    normalized = 0
    for teacher in teachers:
        for lesson in teacher.get("lessons", []):
            if lesson.get("room") != "DA VERIFICARE":
                continue
            for note in reversed(lesson.get("notes", [])):
                if looks_like_room(note):
                    lesson["room"] = normalize_room(note)
                    normalized += 1
                    break
    return normalized


def normalize_existing_activity_fields(teachers):
    normalized = 0
    for teacher in teachers:
        for lesson in teacher.get("lessons", []):
            if lesson.get("subject") not in NON_TEACHING_SUBJECTS:
                continue
            if lesson.get("class") == "DA VERIFICARE":
                lesson["class"] = ""
                normalized += 1
            if lesson.get("room") == "DA VERIFICARE":
                lesson["room"] = ""
                normalized += 1
    return normalized


def infer_classes_from_student_schedules(teachers, student_index):
    inferred = 0
    if not student_index:
        return inferred
    for teacher in teachers:
        for lesson in teacher.get("lessons", []):
            if lesson.get("class") != "DA VERIFICARE":
                continue
            subject = match_key(lesson.get("subject", ""))
            room = match_key(lesson.get("room", ""))
            if not subject or not room or room == "DAVERIFICARE":
                continue
            key = (lesson.get("day"), lesson.get("start"), lesson.get("end"))
            candidates = {
                class_name
                for class_name, candidate_subject, candidate_room
                in student_index.get(key, [])
                if subject == candidate_subject and room == candidate_room
            }
            if len(candidates) == 1:
                lesson["class"] = candidates.pop()
                inferred += 1
    return inferred


def process_teacher(teacher, tesseract, language, tessdata_dir, known_classes):
    local_file = teacher.get("local_file")
    if not local_file:
        return {
            "calendar_status": "missing-image",
            "calendar_error": "immagine locale non disponibile",
        }
    image_path = PROJECT_ROOT / local_file
    if not image_path.is_file():
        return {
            "calendar_status": "failed",
            "calendar_error": f"immagine non trovata: {local_file}",
        }
    try:
        lessons = extract_staff_calendar(
            image_path,
            tesseract,
            language,
            tessdata_dir,
            known_classes,
        )
        return {
            "lessons": lessons,
            "calendar_status": "done",
            "calendar_error": None,
        }
    except (OSError, subprocess.SubprocessError, ValueError, RuntimeError) as error:
        return {
            "calendar_status": "failed",
            "calendar_error": str(error),
        }


def build_staff_calendars(
    manifest_path,
    tesseract_path,
    language,
    classes_path,
    refresh=False,
    workers=None,
    student_calendars_path=DEFAULT_STUDENT_CALENDARS,
):
    tesseract = resolve_tesseract(tesseract_path)
    tessdata_dir = resolve_tessdata_dir(tesseract, language)
    known_classes = load_known_classes(classes_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    teachers = manifest.get("teachers", [])
    if not teachers:
        raise ValueError("Il manifest non contiene docenti.")

    pending = [
        teacher
        for teacher in teachers
        if refresh
        or teacher.get("calendar_status") != "done"
        or "lessons" not in teacher
    ]
    skipped = len(teachers) - len(pending)
    if skipped:
        print(f"Riprendo i calendari già elaborati per {skipped} docenti.")

    workers = max(1, workers or min(8, os.cpu_count() or 1))
    processed = 0
    failed = 0
    completed = 0
    total = len(pending)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                process_teacher,
                teacher,
                tesseract,
                language,
                tessdata_dir,
                known_classes,
            ): teacher
            for teacher in pending
        }
        for future in as_completed(futures):
            teacher = futures[future]
            completed += 1
            try:
                result = future.result()
            except Exception as error:  # noqa: BLE001 - report and continue
                result = {
                    "calendar_status": "failed",
                    "calendar_error": str(error),
                }
            if result["calendar_status"] == "done":
                teacher["lessons"] = result["lessons"]
                teacher["calendar_status"] = "done"
                teacher.pop("calendar_error", None)
                processed += 1
                print(
                    f"{teacher.get('name', '?')} + fatto "
                    f"({completed}/{total}, {len(result['lessons'])} lezioni)"
                )
            else:
                teacher["calendar_status"] = result["calendar_status"]
                teacher["calendar_error"] = result["calendar_error"]
                teacher.pop("lessons", None)
                failed += 1
                print(
                    f"{teacher.get('name', '?')} + non fatto "
                    f"({completed}/{total}: {result['calendar_error']})",
                    file=sys.stderr,
                )
            if completed % 10 == 0:
                save_manifest(manifest_path, manifest)

    normalized_rooms = normalize_existing_lesson_rooms(teachers)
    if normalized_rooms:
        print(f"Aule riconosciute dalle note OCR: {normalized_rooms}.")

    normalized_activities = normalize_existing_activity_fields(teachers)
    if normalized_activities:
        print(
            f"Campi classe/aula non applicabili rimossi dalle attività non didattiche: "
            f"{normalized_activities}."
        )

    student_index = build_student_lesson_index(student_calendars_path)
    inferred = infer_classes_from_student_schedules(teachers, student_index)
    if inferred:
        print(
            f"Classi non lette dall'OCR ricostruite dagli orari delle classi: "
            f"{inferred}."
        )

    manifest["calendar_note"] = (
        "Lezioni docenti estratte localmente con OCR dalle immagini ufficiali; "
        "le classi non leggibili sono ricostruite solo con corrispondenza esatta "
        "di materia, aula e orario nei calendari di classe. "
        "Verificare i risultati con il PNG originale."
    )
    manifest["calendar_days"] = DAYS
    save_manifest(manifest_path, manifest)
    return processed, failed, skipped


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Estrae le lezioni degli orari docenti dalle immagini PNG, "
            "separando materia, classe e aula."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASS_MANIFEST)
    parser.add_argument(
        "--student-calendars",
        type=Path,
        default=DEFAULT_STUDENT_CALENDARS,
        help="Calendari di classe usati per disambiguare le classi non lette dall'OCR.",
    )
    parser.add_argument(
        "--tesseract",
        help="Percorso a tesseract.exe se non è nel PATH.",
    )
    parser.add_argument(
        "--language",
        default="ita",
        help="Lingua Tesseract (default: ita).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Numero di immagini elaborate in parallelo (default: 8).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Riesegui l'OCR di tutti i docenti invece di riprendere i risultati.",
    )
    args = parser.parse_args()
    try:
        processed, failed, skipped = build_staff_calendars(
            args.manifest,
            args.tesseract,
            args.language,
            args.classes,
            args.refresh,
            args.workers,
            args.student_calendars,
        )
    except (OSError, json.JSONDecodeError, RuntimeError, ValueError) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1
    print(
        f"Calendari docenti elaborati: {processed}; non riusciti: {failed}; "
        f"già presenti: {skipped}."
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
