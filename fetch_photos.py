#!/usr/bin/env python3
"""
Download photos from the Prusa ESP32-cam SD card.
Works on Windows, Linux and macOS. Needs only Python 3.8+ (no extra packages).

Examples:
  python fetch_photos.py 192.168.1.50
  python fetch_photos.py prusa-esp32-s3-cam.local --dest D:\\Kamerabilder
  python fetch_photos.py 192.168.1.50 --interval 600
  python fetch_photos.py 192.168.1.50 --user admin --password secret
  python fetch_photos.py 192.168.1.50 --delete      (delete from card after verified download)
"""
import argparse
import base64
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 30     # seconds per request
RETRIES = 3      # attempts per file


def open_url(url, auth, method="GET"):
    req = urllib.request.Request(url, method=method)
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    return urllib.request.urlopen(req, timeout=TIMEOUT)


def list_files(base, auth):
    with open_url(base + "/sd_files", auth) as r:
        text = r.read().decode("utf-8", errors="replace")
    return [line.strip() for line in text.splitlines() if line.strip()]


def download(base, auth, name, dest):
    """Download one file to <name>.part and rename it when complete. Returns size in bytes."""
    path = os.path.join(dest, name)
    tmp = path + ".part"
    url = base + "/sd_download?file=" + urllib.parse.quote(name)
    written = 0
    with open_url(url, auth) as r:
        expected = r.headers.get("Content-Length")
        with open(tmp, "wb") as f:
            while True:
                chunk = r.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                written += len(chunk)
    if written == 0 or (expected is not None and int(expected) != written):
        os.remove(tmp)
        raise IOError("incomplete download (%d of %s bytes)" % (written, expected))
    os.replace(tmp, path)
    return written


def delete_remote(base, auth, name):
    url = base + "/sd_delete?file=" + urllib.parse.quote(name)
    with open_url(url, auth, method="DELETE"):
        pass


def run_once(base, auth, dest, delete):
    try:
        names = list_files(base, auth)
    except (urllib.error.URLError, OSError) as e:
        print("Could not get file list:", e, file=sys.stderr)
        return
    print("%d files on card" % len(names))

    new = skipped = failed = 0
    for name in names:
        # never trust names from the network as paths
        if os.path.basename(name) != name or name in (".", ".."):
            print("Skipping suspicious name:", name, file=sys.stderr)
            failed += 1
            continue
        if os.path.exists(os.path.join(dest, name)):
            skipped += 1
            continue

        size = None
        for attempt in range(1, RETRIES + 1):
            try:
                size = download(base, auth, name, dest)
                break
            except (urllib.error.URLError, OSError) as e:
                print("  retry %d/%d %s: %s" % (attempt, RETRIES, name, e), file=sys.stderr)
                time.sleep(2)
        if size is None:
            failed += 1
            continue

        new += 1
        print("Downloaded: %s (%d bytes)" % (name, size))
        if delete:
            try:
                delete_remote(base, auth, name)
            except (urllib.error.URLError, OSError) as e:
                print("  could not delete %s on card: %s" % (name, e), file=sys.stderr)
        time.sleep(0.05)   # be gentle with the ESP32

    print("Done: %d new, %d already local, %d failed" % (new, skipped, failed))


def main():
    p = argparse.ArgumentParser(description="Download photos from the ESP32-cam SD card")
    p.add_argument("host", help="camera IP address or name, e.g. 192.168.1.50 or prusa-esp32-s3-cam.local")
    p.add_argument("--dest", default="photos", help="destination folder (default: ./photos)")
    p.add_argument("--user", help="Basic Auth user name")
    p.add_argument("--password", default="", help="Basic Auth password")
    p.add_argument("--delete", action="store_true", help="delete each file from the card after a verified download")
    p.add_argument("--interval", type=int, default=0, help="seconds between runs, 0 = run once")
    a = p.parse_args()

    base = a.host if a.host.startswith("http") else "http://" + a.host
    base = base.rstrip("/")
    auth = (a.user + ":" + a.password) if a.user else None
    os.makedirs(a.dest, exist_ok=True)
    print("Saving to:", os.path.abspath(a.dest))

    try:
        while True:
            run_once(base, auth, a.dest, a.delete)
            if a.interval <= 0:
                break
            time.sleep(a.interval)
    except KeyboardInterrupt:
        print("\nStopped")


if __name__ == "__main__":
    main()
