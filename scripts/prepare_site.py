import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE_DIR = PROJECT_ROOT / "_site"

ROOT_FILES = (
    "index.html",
    "CNAME",
    "robots.txt",
    "sitemap.xml",
    "google6baad8fa7abc046f.html",
    "404.html",
)
PAGE_FILES = (
    "orario/index.html",
    "studenti/index.html",
    "docenti/index.html",
    "css/style.css",
    "js/app.js",
)
DATA_FILES = (
    "data/class-schedules.json",
    "data/class-calendars.json",
    "private-data/student-index.json",
    "private-data/staff-timetables.json",
)
DATA_DIRS = (
    "data/class-schedules",
    "private-data/staff-timetable-images",
)
EXTRA_DIRS = (
    ("person-pages/studenti", "studenti"),
    ("person-pages/docenti", "docenti"),
    ("class-pages/orario", "orario"),
)
PERSON_FILES = (
    ("person-pages/links.json", "person-pages/links.json"),
)


def require_file(relative_path):
    path = PROJECT_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"File richiesto per il sito non trovato: {relative_path}")
    return path


def prepare_site():
    for relative_path in (*ROOT_FILES, *PAGE_FILES, *DATA_FILES):
        require_file(relative_path)
    for relative_path in DATA_DIRS:
        if not (PROJECT_ROOT / relative_path).is_dir():
            raise FileNotFoundError(f"Cartella richiesta per il sito non trovata: {relative_path}")
    for relative_path, _ in (*EXTRA_DIRS, *PERSON_FILES):
        if not (PROJECT_ROOT / relative_path).exists():
            raise FileNotFoundError(f"File personale richiesto non trovato: {relative_path}")

    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    for relative_path in (*ROOT_FILES, *PAGE_FILES, *DATA_FILES):
        destination = SITE_DIR / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / relative_path, destination)
    for relative_path in DATA_DIRS:
        destination = SITE_DIR / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PROJECT_ROOT / relative_path, destination)
    for relative_path, destination_path in EXTRA_DIRS:
        destination = SITE_DIR / destination_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(PROJECT_ROOT / relative_path, destination, dirs_exist_ok=True)
    for relative_path, destination_path in PERSON_FILES:
        destination = SITE_DIR / destination_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT_ROOT / relative_path, destination)

    copied_files = sum(1 for path in SITE_DIR.rglob("*") if path.is_file())
    print(f"Sito pronto in _site/ ({copied_files} file).")


if __name__ == "__main__":
    prepare_site()
