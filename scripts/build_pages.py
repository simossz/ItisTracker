import json
import pathlib

repo = pathlib.Path(r"C:\Users\simon\AppData\Local\Temp\opencode\ItisTracker-github")


def slugify(value):
    import re
    import unicodedata
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "classe"


_classes = json.loads((repo / "data" / "class-calendars.json").read_text(encoding="utf-8")).get("classes", {})
CLASS_SELECT = (
    '<div class="field"><label for="class-select">Classe</label>'
    '<select id="class-select" disabled>'
    + "".join(f'<option value="{name}">{name}</option>' for name in _classes)
    + '</select></div>'
)

BRAND_SVG = '''<svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <rect x="4" y="4" width="16" height="16" rx="2" stroke-width="1.8"/>
          <path d="M4 12h16M12 4v16" stroke-width="1.8"/>
          <circle cx="12" cy="12" r="2" fill="var(--ink)" stroke="var(--bg)" stroke-width="1.2"/>
        </svg>'''

GITHUB_SVG = '''<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .7a11.3 11.3 0 0 0-3.57 22c.57.1.78-.24.78-.54v-2.1c-3.18.69-3.85-1.35-3.85-1.35-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.75 2.67 1.24 3.32.95.1-.74.4-1.24.72-1.53-2.54-.29-5.21-1.27-5.21-5.65 0-1.25.44-2.27 1.17-3.07-.12-.29-.51-1.45.11-3.02 0 0 .96-.31 3.12 1.17A10.9 10.9 0 0 1 12 6.78c.97 0 1.94.13 2.85.38 2.16-1.48 3.12-1.17 3.12-1.17.62 1.57.23 2.73.11 3.02.73.8 1.17 1.82 1.17 3.07 0 4.39-2.68 5.36-5.23 5.64.41.36.78 1.06.78 2.14v3.17c0 .3.21.65.79.54A11.3 11.3 0 0 0 12 .7Z"/></svg>'''

INSTA_SVG = '''<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7.8 2h8.4A5.8 5.8 0 0 1 22 7.8v8.4a5.8 5.8 0 0 1-5.8 5.8H7.8A5.8 5.8 0 0 1 2 16.2V7.8A5.8 5.8 0 0 1 7.8 2Zm-.2 2A3.6 3.6 0 0 0 4 7.6v8.8A3.6 3.6 0 0 0 7.6 20h8.8a3.6 3.6 0 0 0 3.6-3.6V7.6A3.6 3.6 0 0 0 16.4 4H7.6Zm8.9 1.5a1.25 1.25 0 1 1 0 2.5 1.25 1.25 0 0 1 0-2.5ZM12 7a5 5 0 1 1 0 10 5 5 0 0 1 0-10Zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z"/></svg>'''

FAVICON = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='32' fill='%23171715'/%3E%3Crect x='16' y='16' width='32' height='32' rx='4' fill='none' stroke='%23fff' stroke-width='4'/%3E%3Cpath d='M16 32h32M32 16v32' stroke='%23fff' stroke-width='4'/%3E%3Ccircle cx='32' cy='32' r='4' fill='%23171715' stroke='%23fff' stroke-width='3'/%3E%3C/svg%3E"

PAGES = [
    {
        "dir": None,
        "page": "orario",
        "title": "ItisTracker — Orari classi ITIS Parma",
        "description": "ItisTracker: orari online dell'ITIS Leonardo da Vinci di Parma. Consulta l'orario settimanale di qualsiasi classe, con materia, aula e orario.",
        "canonical": "https://itistracker.it/",
        "h1": "Orario delle classi",
        "lead": "Seleziona una classe per vedere le lezioni della settimana, con materia, aula e orario.",
        "body": '''<section class="view active" id="class-view">
      <div class="workspace">
        <aside class="side">
          <h2>Classe</h2>
          <div class="field"><label for="class-select">Seleziona</label><select id="class-select" disabled><option>Caricamento…</option></select></div>
        </aside>
        <div class="content" id="schedule-wrap"><div class="empty">Caricamento orario…</div></div>
      </div>
    </section>''',
    },
    {
        "dir": "orario",
        "page": "orario",
        "title": "Orari classi ITIS Parma — ItisTracker",
        "description": "Consulta l'orario settimanale delle classi dell'ITIS Leonardo da Vinci di Parma: lezioni, materie, docenti e aule ora per ora.",
        "canonical": "https://itistracker.it/orario/",
        "h1": "Orario delle classi",
        "lead": "Seleziona una classe per vedere le lezioni della settimana, con materia, aula e orario.",
        "body": '''<section class="view active" id="class-view">
      <div class="workspace">
        <aside class="side">
          <h2>Classe</h2>
          <div class="field"><label for="class-select">Seleziona</label><select id="class-select" disabled><option>Caricamento…</option></select></div>
        </aside>
        <div class="content" id="schedule-wrap"><div class="empty">Caricamento orario…</div></div>
      </div>
    </section>''',
    },
    {
        "dir": "studenti",
        "page": "studenti",
        "title": "Cerca studente ITIS Parma — ItisTracker",
        "description": "Cerca uno studente dell'ITIS Leonardo da Vinci di Parma per nome o cognome e visualizza il suo orario e l'elenco della classe.",
        "canonical": "https://itistracker.it/studenti/",
        "h1": "Cerca studente",
        "lead": "Scrivi almeno due lettere del nome o del cognome per trovare lo studente e vedere il suo orario.",
        "body": '''<section class="view active" id="student-view">
      <div class="workspace">
        <aside class="side">
          <h2>Studente</h2>
          <div class="field"><label for="student-search">Nome o cognome</label><input id="student-search" type="search" autocomplete="off" placeholder="Scrivi…" aria-controls="student-results" aria-describedby="student-search-help" disabled></div>
          <span class="sr-only" id="student-search-help">Scrivi almeno due lettere. Usa le frecce per esplorare i risultati e Invio per selezionarne uno.</span>
        </aside>
        <div class="content">
          <div class="results" id="student-results" aria-label="Risultati studenti"><div class="empty">Caricamento studenti…</div></div>
          <p class="sr-only" id="student-search-status" role="status" aria-live="polite" aria-atomic="true"></p>
          <div class="detail" id="student-detail"></div>
        </div>
      </div>
    </section>''',
    },
    {
        "dir": "docenti",
        "page": "docenti",
        "title": "Cerca docente ITIS Parma — ItisTracker",
        "description": "Cerca un docente dell'ITIS Leonardo da Vinci di Parma per nome o cognome e consulta il suo orario annuale.",
        "canonical": "https://itistracker.it/docenti/",
        "h1": "Cerca docente",
        "lead": "Scrivi almeno due lettere del nome o del cognome per trovare il docente e vedere il suo orario.",
        "body": '''<section class="view active" id="teacher-view">
      <div class="workspace">
        <aside class="side">
          <h2>Docente</h2>
          <div class="field"><label for="teacher-search">Nome o cognome</label><input id="teacher-search" type="search" autocomplete="off" placeholder="Scrivi…" aria-controls="teacher-results" aria-describedby="teacher-search-help" disabled></div>
          <span class="sr-only" id="teacher-search-help">Scrivi almeno due lettere. Usa le frecce per esplorare i risultati e Invio per selezionarne uno.</span>
          ''' + CLASS_SELECT + '''</aside>
        <div class="content">
          <div class="results" id="teacher-results" aria-label="Risultati docenti"><div class="empty">Caricamento docenti…</div></div>
          <p class="sr-only" id="teacher-search-status" role="status" aria-live="polite" aria-atomic="true"></p>
          <div class="detail" id="teacher-detail"></div>
        </div>
      </div>
    </section>''',
    },
    {
        "dir": "aule-libere",
        "page": "aule-libere",
        "title": "Aule libere adesso all'ITIS Parma — ItisTracker",
        "description": "Scopri in tempo reale quali aule sono libere all'ITIS Leonardo da Vinci di Parma, calcolate dagli orari delle classi.",
        "canonical": "https://itistracker.it/aule-libere/",
        "h1": "Aule libere adesso",
        "lead": "Le aule non occupate in questo momento, calcolate dagli orari delle classi. Si aggiornano da sole ogni cinque minuti.",
        "body": '''<section class="view active" id="free-view">
      <div class="workspace">
        <aside class="side">
          <h2>In tempo reale</h2>
          <p class="hint">Aggiornamento automatico ogni 5 minuti.</p>
          <button class="room-button" type="button" id="free-rooms-refresh">Aggiorna ora</button>
          <p class="sr-only" id="free-rooms-status" role="status" aria-live="polite" aria-atomic="true"></p>
        </aside>
        <div class="content" id="free-rooms"><div class="empty">Caricamento aule…</div></div>
      </div>
    </section>''',
    },
]

NAV = [
    ("Orario", "/orario/", "orario"),
    ("Studenti", "/studenti/", "studenti"),
    ("Docenti", "/docenti/", "docenti"),
]


def head(page):
    ld = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "ItisTracker",
        "url": "https://itistracker.it/",
        "description": "Orari online dell'ITIS Leonardo da Vinci di Parma: classi, studenti e docenti.",
        "inLanguage": "it",
        "publisher": {
            "@type": "EducationalOrganization",
            "name": "ITIS Leonardo da Vinci",
            "address": {"@type": "PostalAddress", "addressLocality": "Parma", "addressCountry": "IT"},
        },
        "potentialAction": {
            "@type": "SearchAction",
            "target": "https://itistracker.it/studenti/?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    ld_extra = ""
    if page["page"] == "orario":
        faq = {
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": "Come vedo l'orario di una classe dell'ITIS di Parma?",
                 "acceptedAnswer": {"@type": "Answer", "text": "Apri ItisTracker, scegli la classe dal menu e visualizza l'orario settimanale con materie, aule e orari."}},
                {"@type": "Question", "name": "Posso cercare uno studente o un docente dell'ITIS Parma?",
                 "acceptedAnswer": {"@type": "Answer", "text": "Sì: usa la pagina Studenti o Docenti, scrivi almeno due lettere e seleziona il nome per vedere l'orario."}},
                {"@type": "Question", "name": "Dove si trova l'ITIS Leonardo da Vinci di Parma?",
                 "acceptedAnswer": {"@type": "Answer", "text": "L'ITIS Leonardo da Vinci si trova a Parma. Il sito ufficiale è itis.pr.it."}},
            ],
        }
        ld_extra = f'  <script type="application/ld+json">{json.dumps(faq, ensure_ascii=False)}</script>\n'
    return f'''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#f5f4ef">
  <title>ItisTracker</title>
  <meta name="description" content="{page["description"]}">
  <meta name="robots" content="index, follow">
  <meta name="keywords" content="ItisTracker, ITIS Parma, ITIS Leonardo da Vinci Parma, orari scolastici Parma, orario classi, studenti, docenti">
  <link rel="canonical" href="{page["canonical"]}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="ItisTracker">
  <meta property="og:locale" content="it_IT">
  <meta property="og:title" content="{page["title"]}">
  <meta property="og:description" content="{page["description"]}">
  <meta property="og:url" content="{page["canonical"]}">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{page["title"]}">
  <meta name="twitter:description" content="{page["description"]}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Newsreader:opsz,wght@6..72,500&display=swap" rel="stylesheet">
  <link rel="icon" href="{FAVICON}">
  <link rel="stylesheet" href="/css/style.css">
  <script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
{ld_extra}</head>
<body data-page="{page["page"]}">'''


def shell(page):
    links = "\n      ".join(
        f'<a href="{href}"{" aria-current=\"page\"" if key == page["page"] else ""}>{label}</a>'
        for label, href, key in NAV
    )
    social = f'''<a class="icon-button" href="https://github.com/simossz" target="_blank" rel="noopener noreferrer" aria-label="GitHub simossz" title="GitHub">{GITHUB_SVG}</a>
    <a class="icon-button" href="https://instagram.com/21.simooo" target="_blank" rel="noopener noreferrer" aria-label="Instagram 21.simooo" title="Instagram">{INSTA_SVG}</a>'''
    return f'''  <header class="masthead">
    <a class="brand" href="/" aria-label="ItisTracker, inizio">
      <span class="brand-mark" aria-hidden="true">{BRAND_SVG}</span>
      <span class="brand-name">ItisTracker</span>
    </a>
    <nav class="nav" aria-label="Navigazione principale">
      {links}
    </nav>
    <div class="header-tools">
      {social}
      <button class="icon-button" id="theme-toggle" type="button" aria-label="Attiva tema scuro" title="Tema">
        <svg class="theme-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true"></svg>
      </button>
    </div>
  </header>
  <div class="mobile-social" aria-label="Social">
    {social}
  </div>

  <main id="main">
    <section class="page-head">
      <h1>{page["h1"]}</h1>
      <p>{page["lead"]}</p>
    </section>
    {page["body"]}
  </main>

  <footer>
    <span>Orari dell'<a href="https://itis.pr.it/" target="_blank" rel="noopener noreferrer">ITIS Leonardo da Vinci di Parma</a> · realizzato da <a href="https://github.com/simossz" target="_blank" rel="noopener noreferrer">Simone Zani</a> · <a href="mailto:support@itistracker.it">Segnala un problema</a></span>
  </footer>
  <script src="/js/app.js"></script>
</body>
</html>
'''


for page in PAGES:
    if page["dir"]:
        target_dir = repo / page["dir"]
        target_dir.mkdir(exist_ok=True)
        target = target_dir / "index.html"
    else:
        target = repo / "index.html"
    if page["dir"] is None:
        redirect = '''<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ItisTracker</title>
  <meta http-equiv="refresh" content="0; url=/orario/">
  <link rel="canonical" href="https://itistracker.it/orario/">
  <meta name="robots" content="noindex">
  <link rel="stylesheet" href="/css/style.css">
  <script>location.replace('/orario/');</script>
</head>
<body data-page="orario">
  <main id="main"><section class="page-head"><h1>ItisTracker</h1><p><a href="/orario/">Vai all'orario delle classi</a></p></section></main>
</body>
</html>
'''
        target.write_text(redirect, encoding="utf-8")
    else:
        target.write_text(head(page) + shell(page), encoding="utf-8")
    print("scritto", target.relative_to(repo))

sitemap = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://itistracker.it/</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>
  <url><loc>https://itistracker.it/orario/</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://itistracker.it/studenti/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>
  <url><loc>https://itistracker.it/docenti/</loc><changefreq>daily</changefreq><priority>0.8</priority></url>
</urlset>
'''
(repo / "sitemap.xml").write_text(sitemap, encoding="utf-8")
print("sitemap aggiornato")
