import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin

import requests


PAGE_URL = (
    "https://dati.itis.pr.it/orariodiurno/index-original.html"
    "?nocache=1791385312311"
)
BASE_URL = "https://dati.itis.pr.it/orariodiurno/"
RESOURCE_JS = urljoin(BASE_URL, "js_to_replace/_ressource.js")
PERIOD_JS = urljoin(BASE_URL, "js_to_replace/_periode.js")
GRID_JS = urljoin(BASE_URL, "js_to_replace/_grille.js")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "class-schedules"
MANIFEST_PATH = PROJECT_ROOT / "data" / "class-schedules.json"

RESOURCE_PATTERN = re.compile(
    r'new\s+Ressource\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
PERIOD_PATTERN = re.compile(
    r'new\s+Periode\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
GRID_PATTERN = re.compile(
    r'new\s+Grille\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"'
)


def fetch_text(url):
    response = requests.get(
        url,
        headers={"User-Agent": "ItisTracker schedule updater"},
        timeout=(10, 45),
    )
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def fetch_file(url, path):
    try:
        with requests.get(
            url,
            headers={"User-Agent": "ItisTracker schedule updater"},
            stream=True,
            timeout=(10, 60),
        ) as response:
            response.raise_for_status()
            with path.open("wb") as image:
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        image.write(chunk)
    except requests.RequestException:
        path.unlink(missing_ok=True)
        raise

    if not path.is_file() or path.stat().st_size == 0:
        path.unlink(missing_ok=True)
        raise RuntimeError("download completato ma il file è vuoto")
    with path.open("rb") as image:
        if image.read(8) != b"\x89PNG\r\n\x1a\n":
            path.unlink(missing_ok=True)
            raise RuntimeError("la risposta ricevuta non è un'immagine PNG")


def collect_schedule_map():
    resources_text = fetch_text(RESOURCE_JS)
    periods_text = fetch_text(PERIOD_JS)
    grids_text = fetch_text(GRID_JS)

    classes = [
        {"name": name.strip(), "resource_code": code}
        for genre, name, code in RESOURCE_PATTERN.findall(resources_text)
        if genre == "grClasse" and code != "vide" and name.strip()
    ]
    periods_by_resource = {}
    for resource_code, label, grid_key in PERIOD_PATTERN.findall(periods_text):
        periods_by_resource.setdefault(resource_code, []).append(
            {"label": label.strip(), "grid_key": grid_key}
        )
    grids_by_key = {
        grid_key: filename
        for grid_key, genre, filename in GRID_PATTERN.findall(grids_text)
        if genre == "grClasse"
    }

    if not classes:
        raise RuntimeError("non trovo le classi nel file dati del sito.")

    schedules = []
    for class_info in classes:
        matching_periods = periods_by_resource.get(class_info["resource_code"], [])
        matched = [
            {
                "period": period["label"],
                "image_path": grids_by_key[period["grid_key"]],
            }
            for period in matching_periods
            if period["grid_key"] in grids_by_key
        ]
        if len(matched) == 1:
            schedules.append(
                {
                    **class_info,
                    "period": matched[0]["period"],
                    "source_url": urljoin(BASE_URL, "img/" + matched[0]["image_path"]),
                    "status": "pending",
                }
            )
        else:
            reason = "nessuna immagine associata" if not matched else "più immagini associate"
            schedules.append(
                {
                    **class_info,
                    "period": None,
                    "source_url": None,
                    "status": "failed",
                    "error": reason,
                }
            )
    return schedules


def safe_filename(class_name):
    return quote(class_name, safe="") + ".png"


def save_manifest(schedules, path):
    source_updated = datetime.now(timezone.utc).isoformat(timespec="seconds")
    path.write_text(
        json.dumps(
            {
                "source_page": PAGE_URL,
                "source_updated": source_updated,
                "note": (
                    "Gli orari sono immagini pubblicate dal sito; non sono stati "
                    "trascritti in campi strutturati."
                ),
                "classes": schedules,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def download_schedules(output_dir, manifest_path):
    schedules = collect_schedule_map()
    output_dir.mkdir(parents=True, exist_ok=True)

    for schedule in schedules:
        class_name = schedule["name"]
        if schedule["status"] == "failed":
            print(f"{class_name} + non fatto ({schedule['error']})")
            continue
        image_path = output_dir / safe_filename(class_name)
        try:
            schedule["local_file"] = image_path.resolve().relative_to(
                PROJECT_ROOT
            ).as_posix()
        except ValueError:
            schedule["local_file"] = str(image_path.resolve())
        try:
            fetch_file(schedule["source_url"], image_path)
            schedule["status"] = "done"
            schedule["bytes"] = image_path.stat().st_size
            print(f"{class_name} + fatto")
        except (OSError, RuntimeError, requests.RequestException) as error:
            schedule["status"] = "failed"
            schedule["error"] = str(error)
            schedule.pop("local_file", None)
            print(f"{class_name} + non fatto ({error})", file=sys.stderr)

    save_manifest(schedules, manifest_path)
    return schedules


def main():
    parser = argparse.ArgumentParser(
        description="Scarica localmente la tabella immagine dell'orario per ogni classe."
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    try:
        schedules = download_schedules(args.output_dir, args.manifest)
    except (OSError, RuntimeError, requests.RequestException) as error:
        parser.error(str(error))

    succeeded = sum(item["status"] == "done" for item in schedules)
    failed = len(schedules) - succeeded
    print(
        f"Completato: {succeeded}/{len(schedules)} classi salvate; "
        f"{failed} non riuscite. Manifest: {args.manifest}"
    )
    return 0 if succeeded == len(schedules) else 1


if __name__ == "__main__":
    raise SystemExit(main())
