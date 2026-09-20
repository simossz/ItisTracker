import argparse
import json
from datetime import datetime
from pathlib import Path

from build_student_calendars import load_roster


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ROSTER = PROJECT_ROOT / "private-data" / "student-roster.csv"
DEFAULT_CLASSES = PROJECT_ROOT / "data" / "class-calendars.json"
DEFAULT_OUTPUT = PROJECT_ROOT / "private-data" / "student-index.json"


def build_student_index(roster_path, classes_path, output_path):
    classes_manifest = json.loads(classes_path.read_text(encoding="utf-8"))
    classes = classes_manifest.get("classes", {})
    if not classes:
        raise ValueError(f"Nessun calendario di classe disponibile: {classes_path}")

    students = load_roster(roster_path, classes)
    output = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "students": students,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Indice studenti generato: {len(students)} record.")
    return len(students)


def main():
    parser = argparse.ArgumentParser(
        description="Crea l'indice studenti dal roster locale senza ripetere l'OCR degli orari."
    )
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--classes", type=Path, default=DEFAULT_CLASSES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        build_student_index(args.roster, args.classes, args.output)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
