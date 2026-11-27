import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build():
    source = json.loads((PROJECT_ROOT / "data" / "class-calendars.json").read_text(encoding="utf-8"))
    compact = {
        name: [
            [lesson.get("day", ""), lesson.get("start", ""), lesson.get("end", ""),
             lesson.get("subject") or lesson.get("text") or "Lezione", lesson.get("room", "")]
            for lesson in entry.get("lessons", [])
        ]
        for name, entry in source.get("classes", {}).items()
    }
    target = PROJECT_ROOT / "data" / "class-calendar-web.json"
    target.write_text(json.dumps({"classes": compact}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    student_source = PROJECT_ROOT / "private-data" / "student-index.json"
    if student_source.is_file():
        students = json.loads(student_source.read_text(encoding="utf-8")).get("students", [])
        rows = [[s.get("name", ""), s.get("schedule_class", "")] for s in students]
        target = PROJECT_ROOT / "private-data" / "student-index-web.json"
        target.write_text(json.dumps({"students": rows}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    print("dati web generati")


if __name__ == "__main__":
    build()
