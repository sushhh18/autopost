# autopost

System design reels → Instagram, automatically, on a daily schedule.

**How it works**

1. Claude makes a reel. You review it.
2. Once you approve, it goes into `queue/NNN-topic/` (`reel.mp4` + `caption.txt`).
3. Every day at 7:23 PM IST, GitHub Actions posts the next reel from the queue via Instagram's official API, then moves it to `posted/`.
4. If the queue is empty, nothing gets posted. **Only approved reels ever enter the queue.**

---

## One-time setup (~30–45 min)

### Step 1 — Make your Instagram account Professional
Instagram app → Profile → ☰ → **Settings and activity** → **Account type and tools** → **Switch to professional account** → choose **Creator** → category: *Education* or *Digital creator*.

### Step 2 — Meta developer account
1. Go to **developers.facebook.com** → log in (you need a Facebook account; personal is fine) → **Get started** / register as a developer.

### Step 3 — Create an app
1. **My Apps → Create app**.
2. Use case: the Instagram one (named something like *"Manage messaging & content on Instagram"*).
3. App type: **Business** → give it a name (e.g. `autopost`).
4. **Development mode is fine.** You are only posting to your own account, so App Review isn't needed.

### Step 4 — Generate the access token
1. In the app dashboard: **Instagram → API setup with Instagram business login**.
2. Under **Generate access tokens**, click **Add account**. Log in to your Instagram and allow the permissions:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
3. If it asks to add you as a tester: **App roles → Roles → Instagram testers** → add your username. Then accept the invite in the Instagram app (**Settings → Website permissions → Apps and websites → Tester invites**).
4. Click **Generate token** and copy it.
5. ⚠️ **Do not paste this token in any chat** (including Claude). It goes into GitHub secrets only.

### Step 5 — GitHub repo + Pages
1. Create a **public** repo named `autopost` and upload all files from this folder.
   - Public is required for free GitHub Pages hosting.
   - Instagram needs a public URL to download the video from, and the reels are public on Instagram anyway.
2. Repo **Settings → Pages** → Source: **Deploy from a branch** → `main` / `(root)` → Save.
3. Note the URL it shows, e.g. `https://<your-github-username>.github.io/autopost`.

### Step 6 — Secrets & variables
Go to repo **Settings → Secrets and variables → Actions**.

| Where | Name | Value |
|---|---|---|
| Secrets | `IG_ACCESS_TOKEN` | token from Step 4 |
| Variables | `PAGES_BASE` | URL from Step 5 (no trailing `/`) |
| Secrets | `IG_USER_ID` | from Step 7 below |
| Secrets (optional) | `GH_PAT` | for auto token refresh, see below |

### Step 7 — Check setup
1. **Actions → Check setup → Run workflow**. The log prints your `username`, `account_type` and **`IG_USER_ID`**.
2. Add `IG_USER_ID` as a secret.
3. The log must also say **Pages OK**.

### Step 8 — Dry run, then first real post
1. **Actions → Post next reel → Run workflow** with **dry_run ✅**.
   - Instagram downloads and processes the video but does NOT publish it. You should see `status: FINISHED`.
2. Run again with **dry_run ☐** → the reel goes live, and the link appears in the run summary.

From then on, the daily schedule handles it.

---

## Token refresh (do this, or posting stops after ~60 days)
Instagram tokens expire after 60 days.

**Auto (recommended):**
1. Create a fine-grained GitHub token at GitHub → Settings → Developer settings → Fine-grained tokens.
   - Repository access: only `autopost`
   - Permission: **Secrets: Read and write**
2. Save it as secret `GH_PAT`.
3. `refresh-token.yml` then renews the Instagram token on the 1st and 15th of every month.

**Manual:** regenerate in the Meta dashboard (Step 4) every ~50 days and update the secret.

## Changing the posting time
Edit the `cron` line in `.github/workflows/post.yml`. Times are in **UTC**: IST = UTC + 5:30. For example, 9:00 PM IST is `30 15 * * *`.

## Adding a reel manually
```
queue/002-url-shortener/
  reel.mp4      # 9:16, H.264 + AAC, < 90s works best
  caption.txt   # caption + hashtags (max 2200 chars, max 30 hashtags)
```
Folders are posted in name order: `001`, `002`, …

## Limits to know
- Instagram allows ~50–100 API posts per 24h, so one a day is nowhere near the limit.
- Captions: 2200 characters max, 30 hashtags max. The script refuses to post if either is exceeded.
- If something fails, the reel stays in `queue/` and the Action run turns red with the reason. Nothing is half-posted.
