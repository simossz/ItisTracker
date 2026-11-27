import json
import re
import shutil
import unicodedata
from datetime import date
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = PROJECT_ROOT / "class-pages"
BASE = "https://itistracker.it"
TODAY = date.today().isoformat()

_ALL_CLASSES = json.loads((PROJECT_ROOT / "data" / "class-calendars.json").read_text(encoding="utf-8")).get("classes", {})
CLASS_SELECT = (
    '<div class="field"><label for="class-select">Classe</label>'
    '<select id="class-select" disabled>'
    + "".join(f'<option value="{name}">{name}</option>' for name in _ALL_CLASSES)
    + '</select></div>'
)

DAYS = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato"]
HOURS = ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00"]

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='32' fill='%23171715'/%3E%3Crect x='16' y='16' width='32' height='32' rx='4' fill='none' stroke='%23fff' stroke-width='4'/%3E%3Cpath d='M16 32h32M32 16v32' stroke='%23fff' stroke-width='4'/%3E%3Ccircle cx='32' cy='32' r='4' fill='%23171715' stroke='%23fff' stroke-width='3'/%3E%3C/svg%3E"


def slugify(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "classe"


def escape(value):
    return str(value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def nav():
    items = [("Orario", "/orario/"), ("Studenti", "/studenti/"), ("Docenti", "/docenti/")]
    return "\n      ".join(f'<a href="{href}">{label}</a>' for label, href in items)


def timetable_html(lessons):
    html = '<div class="calendar-scroll"><div class="calendar-grid"><div class="calendar-head"></div>'
    for day in DAYS:
        html += f'<div class="calendar-head">{day[:3]}</div>'
    for hour in HOURS:
        start = int(hour.split(":")[0])
        html += f'<div class="time-label">{hour}</div>'
        for day in DAYS:
            lesson = None
            for item in lessons:
                if item.get("day") != day:
                    continue
                a, b = int(str(item.get("start", "0:0")).split(":")[0]), int(str(item.get("end", "0:0")).split(":")[0])
                if start >= a and start < b:
                    lesson = item
                    break
            if lesson:
                subject = escape(lesson.get("subject") or lesson.get("text") or "Lezione")
                room = escape(lesson.get("room"))
                detail = f"{subject} · {room} · {lesson.get('start','')}–{lesson.get('end','')}"
                secondary = room
                html += f'<div class="calendar-cell"><div class="lesson" tabindex="0" data-detail="{escape(detail)}"><strong>{subject}</strong><small>{secondary}</small></div></div>'
            else:
                html += '<div class="calendar-cell empty-cell"><span aria-label="Ora vuota">—</span></div>'
    return html + "</div></div>"


def page_html(name, lessons, all_classes):
    slug = slugify(name)
    canonical = f"{BASE}/orario/{slug}/"
    subjects = sorted({(l.get("subject") or l.get("text") or "Lezione") for l in lessons})
    rooms = sorted({l.get("room") for l in lessons if l.get("room") and "VERIFICARE" not in str(l.get("room"))})
    title = f"Orario classe {name} ITIS Parma — ItisTracker"
    description = f"Orario completo della classe {name} dell'ITIS Leonardo da Vinci di Parma: {', '.join(subjects[:8])}. Materie, aule e orariora per ora."
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "ItisTracker", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Orario classi", "item": BASE + "/orario/"},
            {"@type": "ListItem", "position": 3, "name": f"Classe {name}", "item": canonical},
        ],
    }
    faq = {
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"Qual è l'orario della classe {name} all'ITIS di Parma?",
             "acceptedAnswer": {"@type": "Answer", "text": f"L'orario della classe {name} include {len(lessons)} lezioni settimanali nelle materie: {', '.join(subjects[:12])}."}},
            {"@type": "Question", "name": f"Quali aule usa la classe {name}?",
             "acceptedAnswer": {"@type": "Answer", "text": "Aule: " + ", ".join(rooms) + "." if rooms else "Le aule non sono ancora verificate."}},
        ],
    }
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f4ef">
  <title>ItisTracker</title>
  <meta name="description" content="{escape(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="ItisTracker">
  <meta property="og:locale" content="it_IT">
  <meta property="og:title" content="{escape(title)}">
  <meta property="og:description" content="{escape(description)}">
  <meta property="og:url" content="{canonical}">
  <link rel="icon" href="{FAVICON}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">
  <script type="application/ld+json">{json.dumps(breadcrumb, ensure_ascii=False)}</script>
  <script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>
</head>
<body data-page="classe" data-class="{escape(name)}">
  <header class="masthead">
    <a class="brand" href="/" aria-label="ItisTracker, inizio">
      <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="2" stroke-width="1.8"/><path d="M4 12h16M12 4v16" stroke-width="1.8"/><circle cx="12" cy="12" r="2" fill="var(--ink)" stroke="var(--bg)" stroke-width="1.2"/></svg></span>
      <span class="brand-name">ItisTracker</span>
    </a>
    <nav class="nav" aria-label="Navigazione principale">
      {nav()}
    </nav>
    <div class="header-tools">
      <button class="icon-button" id="theme-toggle" type="button" aria-label="Attiva tema scuro" title="Tema">
        <svg class="theme-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"></svg>
      </button>
    </div>
  </header>
  <main id="main">
    <section class="page-head">
      <nav class="breadcrumb" aria-label="Percorso"><a href="/orario/">Orario classi</a> › <span>Classe {escape(name)}</span></nav>
      <h1>Orario classe {escape(name)}</h1>
    </section>
    <div class="workspace">
      <aside class="side">
        <h2>Classe</h2>
        {CLASS_SELECT}
      </aside>
      <div class="class-content">
        {timetable_html(lessons)}
      </div>
    </div>
  </main>
  <footer>
    <span>Orari dell'<a href="https://itis.pr.it/" target="_blank" rel="noopener noreferrer">ITIS Leonardo da Vinci di Parma</a> · <a href="https://github.com/simossz" target="_blank" rel="noopener noreferrer">Simone Zani</a></span>
  </footer>
  <script src="/js/app.js"></script>
</body>
</html>
'''


def build():
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    (OUTPUT / "orario").mkdir(parents=True)

    data = json.loads((PROJECT_ROOT / "data" / "class-calendars.json").read_text(encoding="utf-8"))
    classes = data.get("classes", {})
    urls = []
    for name, entry in classes.items():
        lessons = entry.get("lessons", [])
        if not lessons:
            continue
        slug = slugify(name)
        target = OUTPUT / "orario" / slug / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(page_html(name, lessons, list(classes.keys())), encoding="utf-8")
        urls.append(f"{BASE}/orario/{slug}/")

    links = {name: f"/orario/{slugify(name)}/" for name in classes}
    (PROJECT_ROOT / "data" / "class-links.json").write_text(
        json.dumps(links, ensure_ascii=False), encoding="utf-8"
    )

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    priorities = [
        (BASE + "/", "1.0", "daily"),
        (BASE + "/orario/", "0.9", "daily"),
        (BASE + "/studenti/", "0.8", "daily"),
        (BASE + "/docenti/", "0.8", "daily"),
    ]
    for loc, priority, freq in priorities:
        sitemap.append(f"<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>{freq}</changefreq><priority>{priority}</priority></url>")
    for loc in urls:
        sitemap.append(f"<url><loc>{loc}</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq><priority>0.7</priority></url>")
    teacher_index = PROJECT_ROOT / "private-data" / "staff-timetables.json"
    if teacher_index.is_file():
        teachers = json.loads(teacher_index.read_text(encoding="utf-8")).get("teachers", [])
        import re as _re
        import unicodedata as _un
        for teacher in teachers:
            name = teacher.get("name", "")
            code = teacher.get("resource_code", "")
            text = _un.normalize("NFKD", name)
            text = "".join(ch for ch in text if not _un.combining(ch)).lower()
            slug = _re.sub(r"[^a-z0-9]+", "-", text).strip("-") + "-" + str(code).lower()
            sitemap.append(f"<url><loc>{BASE}/docenti/{slug}/</loc><lastmod>{TODAY}</lastmod><changefreq>weekly</changefreq><priority>0.6</priority></url>")
    sitemap.append("</urlset>")
    (PROJECT_ROOT / "sitemap.xml").write_text("\n".join(sitemap) + "\n", encoding="utf-8")

    not_found = f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pagina non trovata — ItisTracker</title>
  <meta name="robots" content="noindex">
  <link rel="icon" href="{FAVICON}">
  <link rel="stylesheet" href="/css/style.css">
</head>
<body data-page="404">
  <header class="masthead">
    <a class="brand" href="/"><span class="brand-mark" aria-hidden="true">✳</span><span class="brand-name">ItisTracker</span></a>
    <nav class="nav" aria-label="Navigazione principale">{nav()}</nav>
  </header>
  <main id="main">
    <section class="page-head">
      <h1>Pagina non trovata</h1>
      <p>La pagina che cerchi non esiste. Torna all'<a href="/orario/">orario delle classi</a> o cerca uno <a href="/studenti/">studente</a>.</p>
    </section>
  </main>
</body>
</html>
'''
    (PROJECT_ROOT / "404.html").write_text(not_found, encoding="utf-8")
    print("pagine classe:", len(urls))


if __name__ == "__main__":
    build()
