"""Upload ONE old Instagram reel (from posted/) to YouTube per run.
Picks the newest version of each topic (011/015 UPI -> 015), newest topics first, skips anything already in yt_posted.json.
Optional env YT_SKIP="001-rate-limiter,002-black-october" to never upload some items."""
import json, os, pathlib, re, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
LOG = ROOT / "yt_posted.json"
done = {x["item"] for x in (json.loads(LOG.read_text()) if LOG.exists() else [])}
slug = lambda n: re.sub(r"^\d+-", "", n)
done_slugs = {slug(n) for n in done}
skip = {s.strip() for s in os.environ.get("YT_SKIP", "").split(",") if s.strip()}
best = {}
for p in sorted((ROOT / "posted").iterdir()):
    if p.is_dir() and (p / "reel.mp4").exists():
        best[slug(p.name)] = p              # sorted, so the highest number (newest remake) wins
todo = [p for s, p in best.items() if s not in done_slugs and p.name not in skip]
todo.sort(key=lambda p: p.name, reverse=True)  # newest first
print(f"{len(todo)} old reels left for YouTube:", [p.name for p in todo])
if not todo:
    print("Backfill complete."); sys.exit(0)
sys.exit(subprocess.call([sys.executable, str(ROOT / "scripts" / "yt_upload.py"), str(todo[0])]))
