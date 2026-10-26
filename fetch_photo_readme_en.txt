DOWNLOADING PHOTOS FROM THE CAMERA'S SD CARD
=============================================

The camera (Prusa ESP32-cam, XIAO ESP32-S3 Sense) has three routes for
listing, downloading and deleting photos on the SD card. The photos are
stored in the /timelapse folder on the card and are named like
photo_2026-10-26_12-00-00.jpg.

In the examples below, replace:
  <ip>    with the camera's IP address, e.g. 192.168.1.50
          (or prusa-esp32-s3-cam.local if mDNS works on your computer)
  <name>  with a file name from the list

If Basic Auth is enabled on the camera, add  -u user:password  to every
curl command.

In Windows PowerShell the command must be  curl.exe  (not curl, which is
an alias for a different command). In cmd,  curl  works as is.


1. LIST FILES   (GET /sd_files)
-------------------------------
Returns the file names as plain text, one name per line.

  curl "http://<ip>/sd_files"

Example response:

  photo_2026-10-26_12-00-00.jpg
  photo_2026-10-26_12-10-00.jpg
  photo_2026-10-26_12-20-00.jpg

Save the list to a file:

  curl -o files.txt "http://<ip>/sd_files"

Status codes:
  200  OK (empty response = no photos)
  503  SD card is busy, try again in a moment


2. DOWNLOAD A FILE   (GET /sd_download?file=<name>)
---------------------------------------------------
Fetches one image. Save it with -o (choose a name) or -O (keep the
remote name).

  curl -o image.jpg "http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg"
  curl -O "http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg"

A web browser works too. Paste the address into the address bar:

  http://<ip>/sd_download?file=photo_2026-10-26_12-00-00.jpg

Status codes:
  200  OK, the file is sent
  400  file name missing or invalid
  404  the file does not exist on the card

Only .jpg files in /timelapse can be downloaded. Names containing /, \ or
.. are rejected.


3. DELETE A FILE   (DELETE /sd_delete?file=<name>)
--------------------------------------------------
Deletes a file from the SD card permanently. There is no undo. The request
must be an HTTP DELETE; an ordinary link in a web browser (GET) does not
work.

  curl -X DELETE "http://<ip>/sd_delete?file=photo_2026-10-26_12-00-00.jpg"

Response:
  deleted      the file was deleted (HTTP 200)
  not found    the file did not exist (HTTP 404)
  bad file name / missing file   invalid request (HTTP 400)
  busy         SD card is busy (HTTP 503)


COMBINED EXAMPLE (Linux/macOS)
------------------------------
Download all images that do not already exist locally:

  mkdir -p photos
  curl -sf "http://<ip>/sd_files" | while read -r f; do
    [ -f "photos/$f" ] || curl -sf -o "photos/$f.part" \
      "http://<ip>/sd_download?file=$f" && mv "photos/$f.part" "photos/$f"
  done


AUTOMATIC DOWNLOAD (Windows, Linux, macOS)  -  fetch_photos.py
--------------------------------------------------------------
A Python script that is identical on all three systems. It only needs
Python 3.8 or newer, no extra packages.

Run:

  Windows:      python fetch_photos.py 192.168.1.50
  Linux/macOS:  python3 fetch_photos.py 192.168.1.50

Images are saved in the "photos" folder inside the folder you run the
script from. The script prints the full path when it starts.

Options:

  --dest FOLDER      save to another folder, e.g. --dest D:\CameraPhotos
  --delete           delete each file from the card after a verified
                     download (requires /sd_delete in the firmware)
  --interval SEC     run again every SEC seconds, e.g. --interval 600
                     0 = run once and exit (default)
  --user USER        Basic Auth, if enabled on the camera
  --password PASS

Examples:

  python fetch_photos.py 192.168.1.50
  python fetch_photos.py prusa-esp32-s3-cam.local --dest D:\CameraPhotos
  python fetch_photos.py 192.168.1.50 --interval 600
  python fetch_photos.py 192.168.1.50 --user admin --password secret
  python fetch_photos.py 192.168.1.50 --delete

How it works:
  - Files that already exist locally are skipped, so the script can be
    re-run any number of times.
  - Each file is downloaded to name.jpg.part and renamed only when the
    whole file has arrived. The size is compared with the Content-Length
    sent by the camera, and an incomplete or empty file is not kept.
  - Each file is tried up to 3 times.
  - With --delete, only files that were just downloaded and verified are
    deleted.
  - File names containing path characters (/, \, ..) in the list are
    ignored.

Installing Python if it is missing:
  Windows:  winget install Python.Python.3.12   (or python.org)
            If "python" is not found, try "py".
  macOS:    python3 comes with the Xcode Command Line Tools (macOS offers
            to install them the first time you need them).
  Linux:    python3 is included in almost every distribution.

Scheduled runs:
  Use --interval in an open window, or run the script once per run from
  cron (Linux/macOS), launchd (macOS) or Task Scheduler (Windows) with
  --interval 0. Windows example, every 10 minutes:

  schtasks /create /tn "FetchPhotos" /sc minute /mo 10 /tr "python C:\path\fetch_photos.py 192.168.1.50 --dest C:\path\photos"

Use absolute paths for scheduled runs, otherwise the images end up in
whatever folder the scheduler starts the script from.


ALTERNATIVE WITHOUT PYTHON: fetch_photos.bat (Windows only)
-----------------------------------------------------------
Uses only curl.exe, which ships with Windows 10 (1803) and 11.
Images are saved in the "photos" folder next to the script (the line
set "DIR=%~dp0photos"). Settings at the top of the script:
  CAM       the camera's address
  DELETE    1 = delete from the card after a successful download, 0 = keep
  INTERVAL  seconds between runs, 0 = run once
  AUTH      e.g.  set "AUTH=-u user:password"  if Basic Auth is enabled
The batch script only checks that the file is not empty, not that the size
matches, so the Python script is more thorough.


DO'S AND DON'TS
---------------
- Start without deleting (no --delete, or DELETE=0 in the .bat). Open a
  few of the downloaded images and only enable deletion once you have
  seen that the download works.
- File names are based on the camera's clock. As long as the time shows
  0000-00-00_00-00-00 (NTP has not synced), all photos get the same name
  and overwrite each other. Make sure WiFi and the time work first.
- Downloads happen one file at a time. The camera cannot handle several
  parallel downloads.
- An image the camera is writing at the moment you fetch it can be
  incomplete. Do not delete automatically right after a download without
  checking.
- The connection is unencrypted HTTP. Use it only on your own network.
