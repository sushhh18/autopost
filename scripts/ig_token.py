"""Token helpers.
  python scripts/ig_token.py check     -> prints your IG user id, username, account type
  python scripts/ig_token.py refresh   -> prints a refreshed 60-day token (for the refresh workflow)
Env: IG_ACCESS_TOKEN
"""
import os, sys, requests

TOKEN = os.environ["IG_ACCESS_TOKEN"]

def check():
    r = requests.get("https://graph.instagram.com/me",
                     params={"fields": "user_id,username,account_type", "access_token": TOKEN}, timeout=30).json()
    if "error" in r:
        sys.exit(f"Token problem: {r['error'].get('message')}")
    print(f"username     : {r.get('username')}\naccount_type : {r.get('account_type')}\nIG_USER_ID   : {r.get('user_id')}")
    if r.get("account_type") not in ("BUSINESS", "MEDIA_CREATOR"):
        print("WARNING: account must be Professional (Creator or Business) to publish.")

def refresh():
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": TOKEN}, timeout=30).json()
    if "access_token" not in r:
        sys.exit(f"Refresh failed: {r}")
    days = int(r.get("expires_in", 0)) // 86400
    print(f"::add-mask::{r['access_token']}", file=sys.stderr)
    print(r["access_token"])
    print(f"refreshed, valid ~{days} days", file=sys.stderr)

if __name__ == "__main__":
    {"check": check, "refresh": refresh}[sys.argv[1] if len(sys.argv) > 1 else "check"]()
