"""Upload one posted reel folder to YouTube as a Short.
usage: python scripts/yt_upload.py posted/<item>
Env (GitHub secrets): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
Reads <item>/youtube.txt: line 1 = title (<=100 chars), rest = description. Falls back to caption.txt.
Never fails the Instagram job: prints a warning and exits 0 on any error."""
import json, os, pathlib, re, sys
from datetime import datetime, timezone
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "yt_posted.json"

def warn(msg):
    print(f"::warning::YouTube: {msg}")
    sys.exit(0)

def main():
    if len(sys.argv) < 2: warn("no folder given")
    item = pathlib.Path(sys.argv[1])
    if not item.is_absolute(): item = ROOT / item
    if not (item / "reel.mp4").exists(): warn(f"{item}/reel.mp4 not found")
    cid, sec, rt = (os.environ.get(k, "") for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"))
    if not (cid and sec and rt): warn("secrets not set yet, skipping YouTube upload")
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    if any(x["item"] == item.name for x in log): warn(f"{item.name} already on YouTube, skipping")

    src = item / "youtube.txt"
    if src.exists():
        lines = src.read_text(encoding="utf-8").strip().splitlines()
        title, desc = lines[0].strip(), "\n".join(lines[1:]).strip()
    else:
        cap = (item / "caption.txt").read_text(encoding="utf-8").strip() if (item / "caption.txt").exists() else item.name
        title, desc = cap.splitlines()[0], cap
    if "#shorts" not in (title + desc).lower(): desc += "\n\n#shorts"
    title = title[:100]
    desc = (desc + "\n\nInstagram: @scaleit__up")[:4900]
    tags = list(dict.fromkeys(t[1:] for t in re.findall(r"#\w+", title + " " + desc)))[:15]

    tok = requests.post("https://oauth2.googleapis.com/token", data=dict(client_id=cid, client_secret=sec, refresh_token=rt,
                        grant_type="refresh_token"), timeout=60).json()
    if "access_token" not in tok: warn(f"token refresh failed: {tok.get('error')} {tok.get('error_description', '')}")
    H = {"Authorization": f"Bearer {tok['access_token']}"}
    video = (item / "reel.mp4").read_bytes()
    meta = {"snippet": {"title": title, "description": desc, "tags": tags, "categoryId": "28", "defaultLanguage": "hi"},
            "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False}}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers={**H, "Content-Type": "application/json; charset=UTF-8", "X-Upload-Content-Type": "video/mp4",
                               "X-Upload-Content-Length": str(len(video))}, data=json.dumps(meta), timeout=60)
    if r.status_code != 200 or "Location" not in r.headers: warn(f"upload init failed ({r.status_code}): {r.text[:400]}")
    up = requests.put(r.headers["Location"], headers={**H, "Content-Type": "video/mp4"}, data=video, timeout=900)
    if up.status_code not in (200, 201): warn(f"upload failed ({up.status_code}): {up.text[:400]}")
    vid = up.json()["id"]; link = f"https://youtube.com/shorts/{vid}"
    print(f"YouTube uploaded: {link}")
    log.append({"item": item.name, "video_id": vid, "url": link, "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    LOG.write_text(json.dumps(log, indent=2) + "\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f: f.write(f"### YouTube ✅ {link}\n")

if __name__ == "__main__":
    try: main()
    except SystemExit: raise
    except Exception as e: warn(f"unexpected error: {e}")
