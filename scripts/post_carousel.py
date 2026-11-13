"""Publish the next carousel from queue_carousel/ to Instagram (no music; the API can't attach music to carousels).
Folder layout: queue_carousel/<name>/01.jpg ... NN.jpg (2-10 JPEGs, same aspect ratio, 1080x1350 recommended) + caption.txt
Flow: one child container per slide (is_carousel_item) -> CAROUSEL container -> media_publish -> move to posted/.
Env: IG_ACCESS_TOKEN, IG_USER_ID, PAGES_BASE, GRAPH_VERSION (opt), DRY_RUN=1 (opt)."""
import json, os, pathlib, re, shutil, sys, time
from datetime import datetime, timezone
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
QDIR = os.environ.get("QUEUE_DIR", "queue_carousel")
QUEUE, POSTED, LOG = ROOT / QDIR, ROOT / "posted", ROOT / "posted.json"
API = f"https://graph.instagram.com/{os.environ.get('GRAPH_VERSION', 'v26.0')}"
TOKEN, IG_ID = os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]
BASE = os.environ["PAGES_BASE"].rstrip("/")
DRY = os.environ.get("DRY_RUN") == "1"

def die(msg): print(f"::error::{msg}"); sys.exit(1)

def call(method, path, **params):
    params["access_token"] = TOKEN
    r = requests.request(method, f"{API}/{path}", data=params if method == "POST" else None,
                         params=params if method == "GET" else None, timeout=60)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {"raw": r.text}
    if r.status_code >= 400 or "error" in body:
        die(f"{method} {path} failed ({r.status_code}): {json.dumps(body.get('error', body))}")
    return body

def slides(p): return sorted(x for x in p.iterdir() if re.fullmatch(r"\d+\.jpe?g", x.name.lower()))

MIN_HOURS = float(os.environ.get("CAROUSEL_MIN_HOURS", "12"))

def reel_ready(name):
    """Carousel 'c027-xyz' waits for reel '027-...' to be posted at least MIN_HOURS ago.
    Carousels not named c<digits>-... have no pair and are always ready."""
    m = re.match(r"c(\d+)-", name)
    if not m: return True, "no paired reel"
    num = m.group(1)
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    hits = [x for x in log if x.get("item", "").split("-")[0] == num and x.get("type") != "carousel"]
    if not hits: return False, f"reel {num} not posted yet"
    t = datetime.fromisoformat(hits[-1]["posted_at"])
    age = (datetime.now(timezone.utc) - t).total_seconds() / 3600
    return (age >= MIN_HOURS), f"reel {num} posted {age:.1f}h ago (need {MIN_HOURS:.0f}h)"

def next_item():
    if not QUEUE.exists(): return None
    for p in sorted(p for p in QUEUE.iterdir() if p.is_dir() and len(slides(p)) >= 2):
        ok, why = reel_ready(p.name)
        print(f"{p.name}: {'READY' if ok else 'waiting'} ({why})")
        if ok: return p
    return None

def wait_public(url, minutes=10):
    for _ in range(minutes * 4):
        if requests.head(url, timeout=30, allow_redirects=True).status_code == 200: return
        time.sleep(15)
    die(f"Not publicly reachable: {url} (is GitHub Pages enabled?)")

def wait_ready(cid, what):
    for i in range(20):
        st = call("GET", cid, fields="status_code").get("status_code")
        if st == "FINISHED": return
        if st in ("ERROR", "EXPIRED"): die(f"{what} failed: {call('GET', cid, fields='status')}")
        time.sleep(10 if i < 6 else 30)
    die(f"Timed out waiting for {what}")

def main():
    item = next_item()
    if not item:
        print("No carousel ready today (empty, or waiting for its reel)."); return
    imgs = slides(item)
    if len(imgs) > 10: die(f"{len(imgs)} slides — Instagram API allows max 10 per carousel")
    caption = (item / "caption.txt").read_text(encoding="utf-8").strip() if (item / "caption.txt").exists() else ""
    if len(caption) > 2200: die("Caption longer than 2200 chars")
    if len(re.findall(r"#\w+", caption)) > 5: die("More than 5 hashtags — trim caption.txt")
    print(f"Next carousel: {item.name} ({len(imgs)} slides)")
    children = []
    for img in imgs:
        url = f"{BASE}/{QDIR}/{item.name}/{img.name}"
        wait_public(url)
        cid = call("POST", f"{IG_ID}/media", image_url=url, is_carousel_item="true")["id"]
        wait_ready(cid, img.name); children.append(cid); print(f"  slide {img.name}: {cid}")
    parent = call("POST", f"{IG_ID}/media", media_type="CAROUSEL", children=",".join(children), caption=caption)["id"]
    wait_ready(parent, "carousel"); print("Carousel container:", parent)
    if DRY:
        print("DRY_RUN=1 — carousel is ready but NOT published."); return
    media_id = call("POST", f"{IG_ID}/media_publish", creation_id=parent)["id"]
    link = call("GET", media_id, fields="permalink").get("permalink", "")
    print(f"Published! {link}")
    POSTED.mkdir(exist_ok=True); shutil.move(str(item), str(POSTED / item.name))
    log = json.loads(LOG.read_text()) if LOG.exists() else []
    log.append({"item": item.name, "type": "carousel", "media_id": media_id, "permalink": link,
                "posted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    LOG.write_text(json.dumps(log, indent=2) + "\n")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f: f.write(f"posted={item.name}\npermalink={link}\n")

if __name__ == "__main__":
    main()
