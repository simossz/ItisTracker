import argparse
import csv
import getpass
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select


LOGIN_URL = "https://riservata.itis.pr.it/riservata/email/"
MAILING_LIST_URL = "https://riservata.itis.pr.it/riservata/email/mailingList.php"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = PROJECT_ROOT / "private-data" / "student-roster.csv"
WAIT_SECONDS = 30

CLASSES = [
    *(f"1{letter} - 1{letter} BIENNIO TECNOLOGICO DELLA RIFORMA" for letter in "ABCDEFGHI"),
    *(f"1{letter} - 1{letter} BIENNIO TECNOLOGICO DELLA RIFORMA" for letter in "LMNOPQR"),
    *(f"2{letter} - 2{letter} BIENNIO TECNOLOGICO DELLA RIFORMA" for letter in "ABCDEF"),
    "2G - 2G TRASPORTI E LOGISTICA",
    *(f"2{letter} - 2{letter} BIENNIO TECNOLOGICO DELLA RIFORMA" for letter in "HILMN"),
    "2Q - 2Q INFORMATICA  E TELECOMUNICAZIONI",
    "3A - 3A ELETTRONICA ED ELETTROTECNICA",
    "3A1 - 3A1 MECCANICA MECCATRONICA ED ENERGIA",
    "3A2 - 3A2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "3A5 - 3A5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "3A6 - 3A6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "3B - 3B ELETTRONICA ED ELETTROTECNICA art. AUTOMAZIONE",
    "3B1 - 3B1 MECCANICA MECCATRONICA ED ENERGIA",
    "3B2 - 3B2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "3B5 - 3B5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "3B6 - 3B6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "3C - 3C ELETTRONICA ELETTROTECNICA",
    "3C1 - 3C1 MECCANICA MECCATRONICA ED ENERGIA",
    "3C5 - 3C5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "3S1 - 3S1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "3S4 - 3S4 SERALE ELETTRONICA E ELETTROTECNICA",
    "4A - 4A ELETTRONICA ED ELETTROTECNICA",
    "4A1 - 4A1 MECCANICA MECCATRONICA ED ENERGIA",
    "4A2 - 4A2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "4A5 - 4A5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "4A6 - 4A6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "4B - 4B ELETTRONICA ED ELETTROTECNICA art. AUTOMAZIONE",
    "4B1 - 4B1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "4B2 - 4B2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "4B5 - 4B5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "4B6 - 4B6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "4C - 4C ELETTRONICA ED ELETTROTECNICA art. AUTOMAZIONE",
    "4C1 - 4C1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "4C2 - 4C2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "4C5 - 4C5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "4S1 - 4S1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "4S4 - 4S4 ELETTRONICA ELETTROTECNICA",
    "5A - 5A ELETTRONICA ED ELETTROTECNICA",
    "5A1 - 5A1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "5A2 - 5A2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "5A5 - 5A5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "5A6 - 5A6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "5B - 5B ELETTRONICA ED ELETTROTECNICA art. AUTOMAZIONE",
    "5B1 - 5B1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "5B2 - 5B2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "5B5 - 5B5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "5B6 - 5B6 CHIMICA MATERIALI E BIOTECNOLOGIE SANITARIE",
    "5C - 5C ELETTRONICA ED ELETTROTECNICA art. AUTOMAZIONE",
    "5C1 - 5C1 MECCANICA MECCATRONICA ED ENERGIA",
    "5C2 - 5C2 INFORMATICA E TELECOMUNICAZIONI  art. INFORMATICA",
    "5C5 - 5C5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "5D5 - 5D5 TRASPORTI E LOGISTICA  art. LOGISTICA",
    "5S1 - 5S1 MECCANICA MECCATRONICA ED ENERGIA art. MECCATRONICA",
    "5S4 - 5S4 ELETTRONICA ELETTROTECNICA",
]


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None
        self.cell_tag = None
        self.skip_tag = None

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            return
        if tag in ("script", "style"):
            self.skip_tag = tag
        elif tag == "table":
            self.table = []
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
            self.cell_tag = tag

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_tag = None
            return
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append((" ".join("".join(self.cell).split()), self.cell_tag == "th"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row:
                if self.table is not None:
                    self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            if self.table:
                self.tables.append(self.table)
            self.table = None

    def handle_data(self, data):
        if not self.skip_tag and self.cell is not None:
            self.cell.append(data)


def find_visible(driver, selectors):
    for by, selector in selectors:
        for element in driver.find_elements(by, selector):
            if element.is_displayed() and element.is_enabled():
                return element
    return None


def extract_student_rows(html):
    parser = TableParser()
    parser.feed(html)
    for table in parser.tables:
        for index, row in enumerate(table):
            headers = [value.strip().casefold() for value, _ in row]
            if {"utente", "cognome", "nome", "email"}.issubset(headers):
                column_names = [value for value, _ in row]
                data = [
                    [value for value, _ in data_row]
                    for data_row in table[index + 1:]
                    if any(value for value, _ in data_row)
                ]
                return column_names, data
    raise RuntimeError("La pagina non contiene la tabella studenti attesa.")


def find_class_dropdown(driver):
    for dropdown in driver.find_elements(By.TAG_NAME, "select"):
        if dropdown.is_displayed() and dropdown.is_enabled():
            return dropdown
    raise TimeoutException("Non trovo il menu a tendina delle classi.")


def normalize_class_name(name):
    return " ".join(name.split())


def find_students_button(driver):
    return find_visible(
        driver,
        [
            (
                By.XPATH,
                "//*[self::button or self::a or self::input]"
                "[translate(normalize-space(string(.)),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='vedi studenti'"
                " or translate(normalize-space(@value),"
                "'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='vedi studenti']",
            )
        ],
    )


def append_class_rows(output_path, class_name, headers, rows, write_header):
    with open(output_path, "a", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.writer(output_file, delimiter=";")
        if write_header:
            writer.writerow(["Classe", *headers])
        for row in rows:
            writer.writerow([class_name, *row])


def has_student_table(html):
    try:
        extract_student_rows(html)
    except RuntimeError:
        return False
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Accede al portale con Selenium e salva la mailing list in CSV."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=OUTPUT_CSV,
        help=f"CSV da creare (default: {OUTPUT_CSV})",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    username_value = input("Utente del portale: ").strip()
    password_value = getpass.getpass("Password del portale: ")
    if not username_value or not password_value:
        parser.error("utente e password sono obbligatori")

    option_html = "".join(f"<option>{name}</option>" for name in CLASSES)
    target_url = (
        f"{MAILING_LIST_URL}?classiStudenti={quote(option_html, safe='/')}"
    )

    options = webdriver.ChromeOptions()
    try:
        driver = webdriver.Chrome(options=options)
    except WebDriverException as error:
        print(f"Impossibile avviare Chrome con Selenium: {error}", file=sys.stderr)
        return 1

    wait = WebDriverWait(driver, WAIT_SECONDS)
    try:
        driver.get(LOGIN_URL)

        username = wait.until(
            lambda current_driver: find_visible(
                current_driver,
                [
                    (By.ID, "user_login"),
                    (By.NAME, "log"),
                    (By.NAME, "user"),
                    (By.NAME, "username"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                ],
            )
        )
        password = find_visible(
            driver,
            [
                (By.ID, "user_pass"),
                (By.NAME, "pwd"),
                (By.NAME, "password"),
                (By.CSS_SELECTOR, "input[type='password']"),
            ],
        )
        if password is None:
            raise RuntimeError("Non trovo il campo password nella pagina di accesso.")

        username.clear()
        username.send_keys(username_value)
        password.clear()
        password.send_keys(password_value)

        submit = find_visible(
            driver,
            [
                (By.ID, "wp-submit"),
                (By.CSS_SELECTOR, "button[type='submit']"),
                (By.CSS_SELECTOR, "input[type='submit']"),
            ],
        )
        if submit is None:
            raise RuntimeError("Non trovo il pulsante di accesso.")
        submit.click()

        try:
            wait.until(
                lambda current_driver: (
                    current_driver.current_url.rstrip("/") != LOGIN_URL.rstrip("/")
                    or not current_driver.find_elements(
                        By.CSS_SELECTOR,
                        "input[type='password']",
                    )
                )
            )
        except TimeoutException as error:
            raise RuntimeError(
                "Il login non sembra riuscito: verifica le credenziali nella finestra Chrome."
            ) from error

        driver.get(target_url)
        dropdown = wait.until(find_class_dropdown)
        classes_by_normalized_name = {
            normalize_class_name(name): name for name in CLASSES
        }
        class_choices = []
        for option in Select(dropdown).options:
            displayed_name = option.text.strip()
            canonical_name = classes_by_normalized_name.get(
                normalize_class_name(displayed_name)
            )
            if canonical_name:
                class_choices.append((displayed_name, canonical_name))
        if not class_choices:
            raise RuntimeError("Il menu a tendina non contiene le classi previste.")

        with open(args.output, "w", newline="", encoding="utf-8-sig"):
            pass

        successful_classes = 0
        headers = None
        for displayed_name, class_name in class_choices:
            code = class_name.split()[0]
            try:
                driver.get(target_url)
                dropdown = wait.until(find_class_dropdown)
                Select(dropdown).select_by_visible_text(displayed_name)
                selected_class_name = class_name

                button = wait.until(
                    lambda current_driver: find_students_button(current_driver)
                )
                if button is None:
                    raise TimeoutException("pulsante 'Vedi studenti' non trovato")
                button.click()

                wait.until(
                    lambda current_driver: has_student_table(
                        current_driver.page_source
                    )
                )
                current_headers, rows = extract_student_rows(driver.page_source)
                if headers is None:
                    headers = current_headers
                elif headers != current_headers:
                    raise RuntimeError(
                        "intestazioni tabella diverse da quelle delle classi precedenti"
                    )

                append_class_rows(
                    args.output,
                    selected_class_name,
                    headers,
                    rows,
                    write_header=successful_classes == 0,
                )
                successful_classes += 1
                print(f"{code} Riuscita")
            except (TimeoutException, RuntimeError, WebDriverException, OSError) as error:
                print(f"{code} non riuscita: {error}", file=sys.stderr)

        if successful_classes == 0:
            print("Nessuna classe è stata esportata.", file=sys.stderr)
            return 1

        print(
            f"CSV salvato in {args.output}; classi riuscite: "
            f"{successful_classes}/{len(class_choices)}."
        )
        return 0
    except TimeoutException:
        print(
            "Timeout: non trovo il form, il pulsante 'Vedi studenti' o i risultati. "
            "Controlla la pagina aperta nel browser.",
            file=sys.stderr,
        )
        return 1
    except (OSError, RuntimeError, WebDriverException) as error:
        print(f"Errore: {error}", file=sys.stderr)
        return 1
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
