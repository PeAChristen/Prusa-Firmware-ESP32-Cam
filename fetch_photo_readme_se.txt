HAMTA BILDER FRAN KAMERANS SD-KORT
===================================

Kameran (Prusa ESP32-cam, XIAO ESP32-S3 Sense) har tre routes for att lista,
ladda ner och radera foton pa SD-kortet. Fotona ligger i mappen /timelapse
pa kortet och heter t.ex. photo_2026-10-26_12-00-00.jpg.

I exemplen nedan ersatts:
  <ip>   med kamerans IP-adress, t.ex. 192.168.1.50
         (eller prusa-esp32-s3-cam.local om mDNS fungerar pa din dator)
  <namn> med ett filnamn fran listan

Anvander du Basic Auth pa kameran, lagg till  -u anvandare:losenord  pa
alla curl-kommandon.

I Windows PowerShell ska kommandot heta  curl.exe  (inte curl, som ar ett
alias for ett annat kommando). I cmd fungerar  curl  direkt.


1. LISTA FILER   (GET /sd_files)
--------------------------------
Returnerar filnamnen som ren text, ett namn per rad.

  curl "http://<ip>/sd_files"

Exempel pa svar:

  photo_2026-10-26_12-00-00.jpg
  photo_2026-10-26_12-10-00.jpg
  photo_2026-10-26_12-20-00.jpg

Spara listan till en fil:

  curl -o filer.txt "http://<ip>/sd_files"

Svarskoder:
  200  OK (tomt svar = inga foton)
  503  SD-kortet ar upptaget, forsok igen om en stund


2. LADDA NER EN FIL   (GET /sd_download?file=<namn>)
----------------------------------------------------
Hamtar en bild och sparar den med -o (eller -O for samma filnamn).

  curl -o bild.jpg "http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg"
  curl -O "http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg"

Webblasaren fungerar ocksa. Klistra in adressen i fonstret:

  http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg

Svarskoder:
  200  OK, filen skickas
  400  filnamnet saknas eller ar ogiltigt
  404  filen finns inte pa kortet

Endast .jpg-filer i /timelapse kan hamtas. Namn med /, \ eller ..
nekas.


3. RADERA EN FIL   (DELETE /sd_delete?file=<namn>)
--------------------------------------------------
Raderar en fil permanent fran SD-kortet. Det finns ingen angra-funktion.
Anropet maste vara HTTP DELETE, en vanlig lank i webblasaren (GET)
fungerar inte.

  curl -X DELETE "http://<ip>/sd_delete?file=photo_2026-10-26_12-00-00.jpg"

Svar:
  deleted      filen raderades (HTTP 200)
  not found    filen fanns inte (HTTP 404)
  bad file name / missing file   felaktigt anrop (HTTP 400)
  busy         SD-kortet upptaget (HTTP 503)


SAMMANSTALLT EXEMPEL (Linux/macOS)
----------------------------------
Hamta alla bilder som inte redan finns lokalt:

  mkdir -p photos
  curl -sf "http://<ip>/sd_files" | while read -r f; do
    [ -f "photos/$f" ] || curl -sf -o "photos/$f.part" \
      "http://<ip>/sd_download?file=$f" && mv "photos/$f.part" "photos/$f"
  done


AUTOMATISK HAMTNING (Windows, Linux, macOS)  -  fetch_photos.py
----------------------------------------------------------------
Ett Python-script som ar identiskt pa alla tre systemen. Det behover
bara Python 3.8 eller nyare, inga extra paket.

Kor:

  Windows:      python fetch_photos.py 192.168.1.50
  Linux/macOS:  python3 fetch_photos.py 192.168.1.50

Bilderna sparas i mappen "photos" i den mapp du star i nar du kor
scriptet. Scriptet skriver ut sokvagen nar det startar.

Flaggor:

  --dest MAPP        spara i en annan mapp, t.ex. --dest D:\Kamerabilder
  --delete           radera varje fil fran kortet efter verifierad
                     nedladdning (kraver /sd_delete i firmware)
  --interval SEK     kor om var SEK:e sekund, t.ex. --interval 600
                     0 = kor en gang och avsluta (standard)
  --user ANVANDARE   Basic Auth, om det ar paslaget pa kameran
  --password LOSEN

Exempel:

  python fetch_photos.py 192.168.1.50
  python fetch_photos.py prusa-esp32-s3-cam.local --dest D:\Kamerabilder
  python fetch_photos.py 192.168.1.50 --interval 600
  python fetch_photos.py 192.168.1.50 --user admin --password hemligt
  python fetch_photos.py 192.168.1.50 --delete

Sa fungerar det:
  - Filer som redan finns lokalt hoppas over, sa scriptet kan koras om
    hur manga ganger som helst.
  - Varje fil hamtas till namn.jpg.part och dops om forst nar hela filen
    kommit. Storleken jamfors mot Content-Length fran kameran, och en
    ofullstandig eller tom fil sparas inte.
  - Varje fil provas upp till 3 ganger.
  - Med --delete raderas bara filer som just laddats ner och verifierats.
  - Filnamn med sokvagstecken (/, \, ..) i listan ignoreras.

Installera Python om det saknas:
  Windows:  winget install Python.Python.3.12   (eller python.org)
            Hittas inte "python", prova "py".
  macOS:    python3 foljer med Xcode Command Line Tools (macOS erbjuder
            att installera dem forsta gangen).
  Linux:    python3 finns i nastan alla distributioner.

Schemalagd korning:
  Anvand --interval i ett oppet fonster, eller kor scriptet en gang per
  korning fran cron (Linux/macOS), launchd (macOS) eller Schemalaggaren
  (Windows) med --interval 0. Windows-exempel, var 10:e minut:

  schtasks /create /tn "FetchPhotos" /sc minute /mo 10 /tr "python C:\sokvag\fetch_photos.py 192.168.1.50 --dest C:\sokvag\photos"

Anvand absoluta sokvagar vid schemalagd korning, annars hamnar bilderna
i den mapp som Schemalaggaren startar scriptet fran.


ALTERNATIV UTAN PYTHON: fetch_photos.bat (endast Windows)
---------------------------------------------------------
Anvander bara curl.exe, som foljer med Windows 10 (1803) och 11.
Bilderna sparas i mappen "photos" bredvid skriptet (raden
set "DIR=%~dp0photos"). Installningar overst i skriptet:
  CAM       kamerans adress
  DELETE    1 = radera fran kortet efter lyckad nedladdning, 0 = behall
  INTERVAL  sekunder mellan korningar, 0 = kor en gang
  AUTH      t.ex.  set "AUTH=-u anvandare:losenord"  om Basic Auth ar pa
Batch-skriptet kontrollerar bara att filen inte ar tom, inte att storleken
stammer. Python-scriptet ar saledes noggrannare.


GOR SA HAR / UNDVIK
-------------------
- Borja utan radering (inget --delete, eller DELETE=0 i .bat). Oppna
  nagra av de nedladdade bilderna och sla bara pa radering nar du sett
  att nedladdningen fungerar.
- Filnamnen bygger pa kamerans klocka. Sa lange tiden star pa
  0000-00-00_00-00-00 (NTP har inte synkat) far alla foton samma namn och
  skriver over varandra. Kontrollera att WiFi och tid fungerar forst.
- Hamtningen sker en fil i taget. Kameran klarar inte flera parallella
  nedladdningar.
- En bild som kameran skriver just nar du hamtar den kan bli ofullstandig.
  Radera inte automatiskt direkt efter en nedladdning utan kontroll.
- Anslutningen ar okrypterad HTTP. Anvand den bara pa ditt eget natverk.
