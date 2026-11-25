import json
import re
import shutil
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "person-pages"


def slugify(value, suffix=None):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    if suffix:
        text = f"{text}-{str(suffix).lower()}"
    return text or "sconosciuto"


def shell(title, description, page, key, body):
    nav = [
        ("Orario", "/orario/", "orario"),
        ("Studenti", "/studenti/", "studenti"),
        ("Docenti", "/docenti/", "docenti"),
    ]
    links = "\n      ".join(f'<a href="{href}">{label}</a>' for label, href, _ in nav)
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f4ef">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="noindex, nofollow">
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
    <span>Orari dell'ITIS Leonardo da Vinci di Parma · <a href="/studenti/">Torna alla ricerca</a></span>
  </footer>
  <script src="/js/app.js"></script>
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
            target.write_text(
                shell(name, f"Classe {student.get('schedule_class', '')}", "student", str(index),
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
            target.write_text(
                shell(name, "Docente · anno completo", "teacher", code,
                      '<div id="person-detail"><div class="empty">Caricamento orario…</div></div>'),
                encoding="utf-8",
            )
            links["teachers"][code] = path

    (OUTPUT / "links.json").write_text(json.dumps(links, ensure_ascii=False), encoding="utf-8")
    print(f"pagine studenti: {len(links['students'])}, docenti: {len(links['teachers'])}")


if __name__ == "__main__":
    build()
