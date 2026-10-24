"""Publish the next approved reel from queue/ to Instagram.

Uses "Instagram API with Instagram Login" (graph.instagram.com) — no Facebook Page needed.
Flow: create REELS container (video_url) -> poll status -> media_publish -> move to posted/.

Env:
  IG_ACCESS_TOKEN   long-lived Instagram user token (GitHub secret)
  IG_USER_ID        your Instagram professional account id (GitHub secret)
  PAGES_BASE        public base URL where this repo is served, e.g. https://<user>.github.io/<repo>
  GRAPH_VERSION     optional, default v26.0
  DRY_RUN=1         optional: do everything except publish
"""
import json, os, pathlib, shutil, sys, time
from datetime import datetime, timezone
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE, POSTED = ROOT / "queue", ROOT / "posted"
LOG = ROOT / "posted.json"
VER = os.environ.get("GRAPH_VERSION", "v26.0")
API = f"https://graph.instagram.com/{VER}"
TOKEN = os.environ["IG_ACCESS_TOKEN"]
IG_ID = os.environ["IG_USER_ID"]
BASE = os.environ["PAGES_BASE"].rstrip("/")
DRY = os.environ.get("DRY_RUN") == "1"


def die(msg):
    print(f"::error::{msg}")
    sys.exit(1)


def call(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code >= 400 or "error" in body:
        die(f"{method} {path} failed ({r.status_code}): {json.dumps(body.get('error', body))}")
    return body


def next_item():
    items = sorted(p for p in QUEUE.iterdir() if p.is_dir() and (p / "reel.mp4").exists()) if QUEUE.exists() else []
    return items[0] if items else None


def wait_public(url, minutes=10):
    """GitHub Pages can take a minute or two to serve a freshly pushed file."""
    for _ in range(minutes * 4):
        r = requests.head(url, timeout=30, allow_redirects=True)
        if r.status_code == 200:
            return
        time.sleep(15)
    die(f"Video not publicly reachable: {url} (is GitHub Pages enabled?)")


def main():
    item = next_item()
    if not item:
        print("Queue empty — nothing to post today.")
        return
    caption = (item / "caption.txt").read_text(encoding="utf-8").strip() if (item / "caption.txt").exists() else ""
    if len(caption) > 2200:
        die("Caption longer than Instagram's 2200 char limit")
    if caption.count("#") > 30:
        die("More than 30 hashtags — Instagram will reject it")
    url = f"{BASE}/queue/{item.name}/reel.mp4"
    print(f"Next reel: {item.name}\nURL: {url}")
    wait_public(url)

    limit = call("GET", f"{IG_ID}/content_publishing_limit", fields="quota_usage,config")
    print("Publishing quota:", json.dumps(limit.get("data", limit)))

    container = call("POST", f"{IG_ID}/media", media_type="REELS", video_url=url,
                     caption=caption, share_to_feed="true")["id"]
    print("Container:", container)

    # Instagram downloads + processes the video; poll until FINISHED
    for i in range(20):  # up to ~10 minutes
        time.sleep(30)
        status = call("GET", container, fields="status_code,status").get("status_code")
        print(f"  status[{i}]: {status}")
        if status == "FINISHED":
            break
        if status in ("ERROR", "EXPIRED"):
            die(f"Processing failed: {call('GET', container, fields='status')}")
    else:
        die("Timed out waiting for Instagram to process the video")

    if DRY:
        print("DRY_RUN=1 — container is ready but NOT published.")
        return

    media_id = call("POST", f"{IG_ID}/media_publish", creation_id=container)["id"]
    link = call("GET", media_id, fields="permalink").get("permalink", "")
    print(f"Published! {link}")

    POSTED.mkdir(exist_ok=True)
    shutil.move(str(item), str(POSTED / item.name))
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    log.append({"item": item.name, "media_id": media_id, "permalink": link,
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    LOG.write_text(json.dumps(log, indent=2) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"posted={item.name}\npermalink={link}\n")


if __name__ == "__main__":
    main()
