import argparse
import getpass
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
from requests_ntlm import HttpNtlmAuth


BASE_URL = "https://dati.itis.pr.it/orariodiurnoriservata/"
PORTAL_URL = BASE_URL
RESOURCE_JS = urljoin(BASE_URL, "js_to_replace/_ressource.js")
PERIOD_JS = urljoin(BASE_URL, "js_to_replace/_periode.js")
GRID_JS = urljoin(BASE_URL, "js_to_replace/_grille.js")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "private-data" / "staff-timetable-images"
MANIFEST_PATH = PROJECT_ROOT / "private-data" / "staff-timetables.json"

RESOURCE_PATTERN = re.compile(
    r'new\s+Ressource\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
PERIOD_PATTERN = re.compile(
    r'new\s+Periode\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"\s*\)'
)
GRID_PATTERN = re.compile(
    r'new\s+Grille\s*\(\s*"([^"]+)"\s*,\s*"([^"]+)"\s*,\s*"([^"]+)"'
)


def get_authenticated_text(session, url):
    response = session.get(url, timeout=30)
    if response.status_code == 401:
        challenge = response.headers.get("WWW-Authenticate", "")
        challenge_detail = f" Il server richiede: {challenge}." if challenge else ""
        raise RuntimeError(
            "Accesso negato (HTTP 401). Verifica che l'account sia autorizzato "
            "all'orario docenti diurno e che il nome utente sia corretto. Se "
            "richiesto dall'istituto, inserisci DOMINIO\\utente come username."
            + challenge_detail
        )
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def collect_teacher_schedule_map(session):
    resources_text = get_authenticated_text(session, RESOURCE_JS)
    periods_text = get_authenticated_text(session, PERIOD_JS)
    grids_text = get_authenticated_text(session, GRID_JS)

    teachers = [
        {"name": name.strip(), "resource_code": code}
        for genre, name, code in RESOURCE_PATTERN.findall(resources_text)
        if genre == "grProf" and code != "vide" and name.strip()
    ]
    periods_by_resource = {}
    for resource_code, label, grid_key in PERIOD_PATTERN.findall(periods_text):
        periods_by_resource.setdefault(resource_code, []).append(
            {"label": label.strip(), "grid_key": grid_key}
        )
    grids_by_key = {
        grid_key: filename
        for grid_key, genre, filename in GRID_PATTERN.findall(grids_text)
        if genre == "grProf"
    }

    if not teachers:
        raise RuntimeError("Non trovo docenti nei dati restituiti dal portale.")

    schedules = []
    for teacher in teachers:
        matched_periods = [
            {
                "period": period["label"],
                "image_path": grids_by_key[period["grid_key"]],
            }
            for period in periods_by_resource.get(teacher["resource_code"], [])
            if period["grid_key"] in grids_by_key
        ]
        if len(matched_periods) != 1:
            reason = (
                "nessuna immagine associata"
                if not matched_periods
                else "più immagini associate"
            )
            schedules.append(
                {
                    **teacher,
                    "status": "failed",
                    "error": reason,
                }
            )
            continue

        matched = matched_periods[0]
        schedules.append(
            {
                **teacher,
                "period": matched["period"],
                "source_url": urljoin(BASE_URL, "img/" + matched["image_path"]),
                "status": "pending",
            }
        )
    return schedules


def project_asset_path(path):
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def download_teacher_schedules(username, password, output_dir, manifest_path):
    session = requests.Session()
    session.auth = HttpNtlmAuth(username, password)
    session.headers.update({"User-Agent": "OrariITIS-local/1.0"})

    print("Verifico l'accesso alla pagina Orario Docenti Diurno...")
    get_authenticated_text(session, PORTAL_URL)
    schedules = collect_teacher_schedule_map(session)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(schedules)
    for index, schedule in enumerate(schedules, start=1):
        teacher_name = schedule["name"]
        if schedule["status"] == "failed":
            print(
                f"{teacher_name} + non fatto ({schedule['error']})",
                file=sys.stderr,
            )
            continue

        image_path = output_dir / f"{index:03d}.png"
        try:
            response = session.get(schedule["source_url"], timeout=30)
            if response.status_code == 401:
                raise RuntimeError("accesso negato al PNG (401)")
            response.raise_for_status()
            if not response.content.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError("la risposta ricevuta non è un'immagine PNG")
            image_path.write_bytes(response.content)
            schedule.update(
                {
                    "status": "done",
                    "local_file": project_asset_path(image_path),
                    "bytes": len(response.content),
                }
            )
            print(f"{teacher_name} + fatto ({index}/{total})")
        except (OSError, requests.RequestException, RuntimeError) as error:
            schedule["status"] = "failed"
            schedule["error"] = str(error)
            print(f"{teacher_name} + non fatto ({error})", file=sys.stderr)

    manifest_path.write_text(
        json.dumps(
            {
                "source": PORTAL_URL,
                "note": (
                    "Orari professionali scaricati localmente con autenticazione "
                    "NTLM. Le credenziali non sono salvate."
                ),
                "teachers": schedules,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return schedules


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Accedi alla pagina Orario Docenti Diurno collegata dal sito "
            "itis.pr.it e scarica gli orari localmente. Username e password "
            "sono richiesti nel terminale; la password non viene mostrata "
            "e nessuna credenziale viene salvata."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    args = parser.parse_args()

    print(f"Portale: {PORTAL_URL}")
    username = input("Utente autorizzato del portale (eventuale DOMINIO\\utente): ").strip()
    password = getpass.getpass("Password (input nascosto, non viene salvata): ")
    if not username or not password:
        parser.error("utente e password sono obbligatori")

    try:
        schedules = download_teacher_schedules(
            username,
            password,
            args.output_dir,
            args.manifest,
        )
    except (OSError, requests.RequestException, RuntimeError) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1

    completed = sum(item["status"] == "done" for item in schedules)
    failed = len(schedules) - completed
    print(
        f"Completato: {completed}/{len(schedules)} orari acquisiti; "
        f"{failed} non riusciti. Manifest locale: {args.manifest}"
    )
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
