import argparse
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = PROJECT_ROOT / "private-data" / "student-calendars.json"
DEFAULT_CLASSES_OUTPUT = PROJECT_ROOT / "data" / "class-calendars.json"
DEFAULT_STUDENTS_OUTPUT = PROJECT_ROOT / "private-data" / "student-index.json"


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def split_student_calendars(source, classes_output, students_output, cleanup=False):
    manifest = json.loads(source.read_text(encoding="utf-8"))
    classes = manifest.get("classes", {})
    students = manifest.get("students", [])
    if not classes:
        raise ValueError("Il manifest non contiene calendari delle classi.")
    if not students:
        raise ValueError("Il manifest non contiene l'indice degli studenti.")

    generated_at = manifest.get("generated_at")
    write_json(
        classes_output,
        {
            "source": manifest.get("source", ""),
            "generated_at": generated_at,
            "note": "Calendari delle classi senza dati personali degli studenti.",
            "classes": classes,
        },
    )
    write_json(
        students_output,
        {
            "generated_at": generated_at,
            "students": students,
        },
    )

    if cleanup:
        source.unlink(missing_ok=True)
        roster = PROJECT_ROOT / "private-data" / "student-roster.csv"
        roster.unlink(missing_ok=True)

    print(
        f"Creati {len(classes)} calendari di classe e un indice per "
        f"{len(students)} studenti."
    )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Separa i calendari pubblici delle classi dall'indice studenti "
            "generato localmente o in CI."
        )
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--classes-output", type=Path, default=DEFAULT_CLASSES_OUTPUT)
    parser.add_argument("--students-output", type=Path, default=DEFAULT_STUDENTS_OUTPUT)
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Rimuovi il CSV e il manifest sorgente dopo averli separati.",
    )
    args = parser.parse_args()
    try:
        split_student_calendars(
            args.source,
            args.classes_output,
            args.students_output,
            args.cleanup,
        )
    except (OSError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
