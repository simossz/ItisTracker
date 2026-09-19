# ItisTracker

**Orari scolastici dell’ITIS Parma, in un’unica pagina.**

[Apri il sito](https://itis.simocode.xyz/) · [Segnala un problema](https://github.com/simossz/ItisTracker/issues)

ItisTracker è un sito statico per consultare gli orari settimanali delle classi e cercare gli orari di studenti e docenti. È pensato per essere rapido, utilizzabile da tastiera e leggibile anche da telefono.

## Cosa puoi fare

- consultare l’orario di una classe;
- cercare uno studente e aprire l’orario della sua classe;
- cercare un docente e vedere materia, classe, aula e fascia oraria;
- usare il tema chiaro o scuro;
- esplorare i risultati con tastiera: **↓ / ↑**, **Home / End**, **Invio** ed **Esc**.

## Dati e privacy

I roster e i manifest generati con i nominativi degli studenti **non fanno parte della cronologia Git**. Per mantenere attiva la ricerca sul sito, GitHub Actions genera i dati durante il deploy usando il secret `STUDENT_ROSTER_GZIP_BASE64`; i file temporanei vengono esclusi dal pacchetto sorgente.

Il secret contiene un CSV `Nome;Cognome;Classe` compresso in gzip e codificato Base64. Per ricrearlo localmente:

```powershell
python -c "import base64,gzip,pathlib; p=pathlib.Path('private-data/student-roster.csv'); print(base64.b64encode(gzip.compress(p.read_bytes(),mtime=0)).decode())"
```

L’output contiene dati personali: copialo solo nelle impostazioni dei secret GitHub Actions e non inserirlo in commit o log.

Il sito è statico: per offrire la ricerca, l’indice studenti viene comunque scaricato dal browser e può essere recuperato dai visitatori. Pubblicalo e mantienilo attivo solo con l’autorizzazione necessaria. Non inserire mai nel repository roster CSV, credenziali o dati personali non autorizzati.

## Avvio locale

Per visualizzare i file già generati, avvia un server statico dalla radice del progetto:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Apri <http://127.0.0.1:8000/>. Per eseguire localmente tutte le ricerche servono i manifest generati, Tesseract con il pacchetto italiano e un roster autorizzato.

## Aggiornamento degli orari

Gli script di download e generazione si trovano in `scripts/`. Per aggiornare le immagini ufficiali delle classi, esegui `python scripts/download_class_schedules.py`; poi, con Tesseract e un roster autorizzato disponibili localmente, rigenera i calendari:

```powershell
python scripts/build_student_calendars.py --refresh
python scripts/build_staff_calendars.py --refresh
python scripts/split_student_calendars.py --cleanup
python scripts/prepare_site.py
```

GitHub Actions pubblica il sito quando cambia `main` o su richiesta manuale. I calendari delle classi, privi di nominativi, sono versionati in `data/class-calendars.json`; il deploy ricrea l’indice studenti dal secret `STUDENT_ROSTER_GZIP_BASE64` senza ripetere l’OCR. CSV e manifest intermedi restano esclusi da Git e dall’artefatto Pages.

L’indice necessario alla ricerca viene incluso nel sito statico e quindi può essere scaricato dai visitatori: questa scelta mantiene il funzionamento attuale. Gli aggiornamenti delle immagini ufficiali si fanno localmente, ricostruendo e verificando i calendari prima del commit.

## Licenza

La repo non dichiara ancora una licenza di riutilizzo. La visibilità pubblica del codice non equivale a un’autorizzazione a riutilizzarlo.
