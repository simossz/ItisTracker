import json
import re
import shutil
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "person-pages"


def escape(value):
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def slugify(value, suffix=None):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if suffix:
        text = f"{text}-{str(suffix).lower()}"
    return text or "sconosciuto"


SOCIAL = '''<a class="icon-button" href="https://github.com/simossz" target="_blank" rel="noopener noreferrer" aria-label="GitHub simossz" title="GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .7a11.3 11.3 0 0 0-3.57 22c.57.1.78-.24.78-.54v-2.1c-3.18.69-3.85-1.35-3.85-1.35-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.75 2.67 1.24 3.32.95.1-.74.4-1.24.72-1.53-2.54-.29-5.21-1.27-5.21-5.65 0-1.25.44-2.27 1.17-3.07-.12-.29-.51-1.45.11-3.02 0 0 .96-.31 3.12 1.17A10.9 10.9 0 0 1 12 6.78c.97 0 1.94.13 2.85.38 2.16-1.48 3.12-1.17 3.12-1.17.62 1.57.23 2.73.11 3.02.73.8 1.17 1.82 1.17 3.07 0 4.39-2.68 5.36-5.23 5.64.41.36.78 1.06.78 2.14v3.17c0 .3.21.65.79.54A11.3 11.3 0 0 0 12 .7Z"/></svg></a>
      <a class="icon-button" href="https://instagram.com/21.simooo" target="_blank" rel="noopener noreferrer" aria-label="Instagram 21.simooo" title="Instagram"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.8 2h8.4A5.8 5.8 0 0 1 22 7.8v8.4a5.8 5.8 0 0 1-5.8 5.8H7.8A5.8 5.8 0 0 1 2 16.2V7.8A5.8 5.8 0 0 1 7.8 2Zm-.2 2A3.6 3.6 0 0 0 4 7.6v8.8A3.6 3.6 0 0 0 7.6 20h8.8a3.6 3.6 0 0 0 3.6-3.6V7.6A3.6 3.6 0 0 0 16.4 4H7.6Zm8.9 1.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg></a>'''

DAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]
HOURS = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]


def timetable_html(lessons):
    rows = []
    for lesson in lessons:
        day = lesson.get("day", "")
        start = lesson.get("start", "")
        end = lesson.get("end", "")
        subject = str(lesson.get("subject") or lesson.get("text") or "Lezione").replace("<", "&lt;")
        room = str(lesson.get("room") or "").replace("<", "&lt;")
        rows.append(f"<tr><th scope='row'>{day} {start}–{end}</th><td>{subject}" + (f" · Aula {room}" if room else "") + "</td></tr>")
    if not rows:
        return '<p class="empty">Orario non ancora disponibile.</p>'
    return '<table class="seo-table"><thead><tr><th>Giorno e ora</th><th>Lezione</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>"


def shell(title, description, page, key, body):
    nav = [
        ("Orario", "/orario/", "orario"),
        ("Studenti", "/studenti/", "studenti"),
        ("Docenti", "/docenti/", "docenti"),
    ]
    links = "\n      ".join(
        f'<a href="{href}"' + (' aria-current="page"' if (label == "Studenti" and page == "student") or (label == "Docenti" and page == "teacher") else '') + f'>{label}</a>'
        for label, href, _ in nav
    )
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f4ef">
  <title>{escape(title)} — Orario ITIS Parma | ItisTracker</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="{'noindex, nofollow' if page == 'student' else 'index, follow'}">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='32' fill='%23171715'/%3E%3Crect x='16' y='16' width='32' height='32' rx='4' fill='none' stroke='%23fff' stroke-width='4'/%3E%3Cpath d='M16 32h32M32 16v32' stroke='%23fff' stroke-width='4'/%3E%3Ccircle cx='32' cy='32' r='4' fill='%23171715' stroke='%23fff' stroke-width='3'/%3E%3C/svg%3E">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body data-page="{page}" data-person="{key}">
  <header class="masthead">
    <a class="brand" href="/" aria-label="ItisTracker, inizio">
      <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" stroke-width="1.8"/><path d="M4 12h16M12 4v16" stroke-width="1.8"/><circle cx="12" cy="12" r="2" fill="var(--ink)" stroke="var(--bg)" stroke-width="1.2"/></svg></span>
      <span class="brand-name">ItisTracker</span>
    </a>
    <nav class="nav" aria-label="Navigazione principale">
      {links}
    </nav>
    <div class="header-tools">
      {SOCIAL}
      <button class="icon-button" id="theme-toggle" type="button" aria-label="Attiva tema scuro" title="Tema">
        <svg class="theme-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"></svg>
      </button>
    </div>
  </header>
  <main id="main">
    <section class="page-head">
      <h1 id="person-name">{title}</h1>
      <p id="person-label">{description}</p>
    </section>
    {body}
  </main>
  <footer>
    <span>Realizzato da <a href="https://github.com/simossz" target="_blank" rel="noopener noreferrer">Simone Zani</a> · <a href="/studenti/">Torna alla ricerca</a></span>
    <span>Contatti: <a href="mailto:supporto@itistracker.it">supporto@itistracker.it</a></span>
  </footer>
  <script src="/js/app.js" defer></script>
</body>
</html>
'''


def build():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "studenti").mkdir(parents=True)
    (OUTPUT / "docenti").mkdir(parents=True)

    student_index = PROJECT_ROOT / "private-data" / "student-index.json"
    teacher_index = PROJECT_ROOT / "private-data" / "staff-timetables.json"

    links = {"students": {}, "teachers": {}}

    if student_index.is_file():
        data = json.loads(student_index.read_text(encoding="utf-8"))
        for index, student in enumerate(data.get("students", [])):
            slug = slugify(student.get("name"), index)
            path = f"/studenti/{slug}/"
            target = OUTPUT / "studenti" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            name = student.get("name", "Studente")
            cls = student.get("schedule_class") or str(student.get("class") or "").split(" - ")[0].strip()
            label = f"Classe {cls}" if cls else "Studente"
            target.write_text(
                shell(name, label, "student", str(index),
                      '<div id="person-detail"><div class="empty">Caricamento orario…</div></div>'),
                encoding="utf-8",
            )
            links["students"][str(index)] = path

    if teacher_index.is_file():
        data = json.loads(teacher_index.read_text(encoding="utf-8"))
        for teacher in data.get("teachers", []):
            code = teacher.get("resource_code", "")
            slug = slugify(teacher.get("name"), code)
            path = f"/docenti/{slug}/"
            target = OUTPUT / "docenti" / slug / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            name = teacher.get("name", "Docente")
            lessons = teacher.get("lessons", [])
            target.write_text(
                shell(name, "Docente · anno completo", "teacher", code,
                      '<div id="person-detail"><h2>Orario del docente</h2>' + timetable_html(lessons) + '</div>'),
                encoding="utf-8",
            )
            links["teachers"][code] = path

    (OUTPUT / "links.json").write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")

    teacher_index = PROJECT_ROOT / "private-data" / "staff-timetables.json"
    if teacher_index.is_file():
        teachers = json.loads(teacher_index.read_text(encoding="utf-8")).get("teachers", [])
        light = [
            {"name": t.get("name", ""), "resource_code": t.get("resource_code", ""), "status": t.get("status", "")}
            for t in teachers
        ]
        (PROJECT_ROOT / "private-data" / "staff-index.json").write_text(
            json.dumps({"teachers": light}, ensure_ascii=False), encoding="utf-8"
        )
    print(f"pagine studenti: {len(links['students'])}, docenti: {len(links['teachers'])}")


if __name__ == "__main__":
    build()
