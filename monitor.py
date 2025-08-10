#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Instagram Monitor
- monitor mode: track basic profile changes over time
- friends mode: extract followers, following, and mutuals (requires login)
- shortcode mode: fetch a public post/reel JSON via GraphQL (cookie-less) with embed fallback

CLI:
  monitor.py --mode monitor --target-user USER --output-dir monitoring_data/USER
  monitor.py --mode friends --target-user USER --out data/USER_friends_analysis.json
  monitor.py --shortcode SHORTCODE --post-out data/post.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---- External libs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from instaloader import Instaloader, Profile, exceptions as igx
except Exception as e:
    print("ERROR: instaloader not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    raise

# =========================
# Logging
# =========================

def setup_logger(verbosity: int = 1) -> logging.Logger:
    logger = logging.getLogger("instagram_monitor")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(levelname)s] %(message)s")

    # If handler already exists, just update it (prevents duplicates)
    if logger.handlers:
        ch = logger.handlers[0]
        ch.setLevel(logging.DEBUG if verbosity > 1 else logging.INFO)
        ch.setFormatter(fmt)
    else:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG if verbosity > 1 else logging.INFO)
        ch.setFormatter(fmt)
        logger.addHandler(ch)

    return logger

logger = setup_logger()

# =========================
# Utilities
# =========================

USER_AGENTS = [
    # Desktop (2025-era)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    # Mobile
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36",
]

def get_random_user_agent() -> str:
    # Simple deterministic rotation to avoid importing random
    idx = int(time.time()) % len(USER_AGENTS)
    return USER_AGENTS[idx]

def retry_session(total=3, backoff=0.5) -> requests.Session:
    s = requests.Session()
    r = Retry(
        total=total,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"]),
        raise_on_status=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.mount("http://", HTTPAdapter(max_retries=r))
    return s

def json_load(path: Path, default):
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read JSON {path}: {e}")
    return default

def json_dump_atomic(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def normalize_username(u: str) -> str:
    return (u or "").strip().lstrip("@").lower()


# =========================
# Unauth Web-Scrape Helpers
# =========================

PROFILE_PAGE_JSON_PATTERNS = [
    # Legacy hydration blobs IG has used at different times
    r'window\.__additionalDataLoaded__\(.+?,\s*(\{.*?\})\);',
    r'window\._sharedData\s*=\s*(\{.*?\});',
    r'"props":\{"pageProps":(\{.*?\})\}',
]

def _build_headers() -> Dict[str, str]:
    return {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.instagram.com/",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
    }

def _extract_first_json_blob(html: str) -> Optional[dict]:
    import re, json as _json
    for pat in PROFILE_PAGE_JSON_PATTERNS:
        m = re.search(pat, html, flags=re.DOTALL)
        if m:
            blob = m.group(1)
            try:
                return _json.loads(blob)
            except Exception:
                try:
                    cleaned = blob.replace("\\n", "\n")
                    return _json.loads(cleaned)
                except Exception:
                    continue
    return None

def _pick_hd_pfp_url(user_obj: dict) -> Optional[str]:
    try:
        if "hd_profile_pic_url_info" in user_obj:
            return user_obj["hd_profile_pic_url_info"].get("url")
        if "hd_profile_pic_versions" in user_obj:
            versions = user_obj["hd_profile_pic_versions"]
            versions = sorted(versions, key=lambda v: v.get("width", 0), reverse=True)
            if versions:
                return versions[0].get("url")
        return user_obj.get("profile_pic_url_hd") or user_obj.get("profile_pic_url")
    except Exception:
        return None

@dataclass
class ProfileSnapshot:
    username: str
    full_name: str
    biography: str
    is_private: bool
    is_verified: bool
    followers: int
    following: int
    posts: int
    profile_pic_url: Optional[str]
    last_updated: str

def _shape_snapshot_from_user(user_obj: dict, username_hint: str) -> Optional["ProfileSnapshot"]:
    if not user_obj:
        return None
    full_name   = user_obj.get("full_name") or ""
    biography   = user_obj.get("biography") or ""
    is_private  = bool(user_obj.get("is_private"))
    is_verified = bool(user_obj.get("is_verified"))
    followers   = user_obj.get("edge_followed_by", {}).get("count") or user_obj.get("follower_count") or user_obj.get("followers") or 0
    following   = user_obj.get("edge_follow", {}).get("count") or user_obj.get("following_count") or user_obj.get("followees") or 0
    posts       = (user_obj.get("edge_owner_to_timeline_media", {}) or {}).get("count") or user_obj.get("media_count") or user_obj.get("posts") or 0
    pfp_url     = _pick_hd_pfp_url(user_obj)

    # We avoid safe_int here to keep this block self-contained
    def _to_int(v):
        try:
            return int(v)
        except Exception:
            return 0

    return ProfileSnapshot(
        username=(user_obj.get("username") or username_hint or "").lower(),
        full_name=full_name,
        biography=biography,
        is_private=is_private,
        is_verified=is_verified,
        followers=_to_int(followers),
        following=_to_int(following),
        posts=_to_int(posts),
        profile_pic_url=pfp_url,
        last_updated=now_iso(),
    )

def fetch_profile_unauth_via_page(username: str) -> Optional["ProfileSnapshot"]:
    """
    Method A: Unauth page fetch https://www.instagram.com/<user>/ and parse page-embedded JSON.
    Works when the site serves hydration JSON without requiring cookies.
    """
    try:
        sess = retry_session()
        r = sess.get(f"https://www.instagram.com/{username}/", headers=_build_headers(), timeout=20)
        if r.status_code >= 400:
            logger.debug(f"Profile page HTTP {r.status_code} for {username}")
            return None
        data = _extract_first_json_blob(r.text)
        if not data:
            logger.debug("No hydration JSON found in profile page.")
            return None

        # Try common paths to reach a 'user' object
        candidates = []
        # Classic sharedData/graphql/user style
        try:
            user2 = (data.get("entry_data", {})
                       .get("ProfilePage", [{}])[0]
                       .get("graphql", {})
                       .get("user"))
            if user2:
                candidates.append(user2)
        except Exception:
            pass

        # Direct pageProps.user-ish
        user3 = (data.get("user") or data.get("profile_user"))
        if user3:
            candidates.append(user3)

        # Pick the richest candidate
        import json as _json
        richest = max(
            candidates,
            key=lambda u: len(_json.dumps(u)) if isinstance(u, dict) else 0,
            default=None
        )
        return _shape_snapshot_from_user(richest or (user2 if 'user2' in locals() else None) or user3, username)
    except Exception as e:
        logger.debug(f"fetch_profile_unauth_via_page error: {e}")
        return None

def fetch_post_public_graphql(shortcode: str) -> Optional[dict]:
    """
    Method B: Unauth pull of public post/reel JSON via the same GraphQL the web app uses.
    Note: actual queries can require doc_id/query_hash; this minimal variant works as a placeholder.
    """
    try:
        params = {
            "variables": json.dumps({"shortcode": shortcode, "child_comment_count": 0, "fetch_comment_count": 0}),
        }
        sess = retry_session()
        r = sess.get("https://www.instagram.com/api/graphql", params=params, headers=_build_headers(), timeout=20)
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json"):
            return r.json()
        return None
    except Exception as e:
        logger.debug(f"fetch_post_public_graphql error: {e}")
        return None

def fetch_profile_unauth_via_mobile(username: str) -> Optional["ProfileSnapshot"]:
    """
    Method G: Mobile web JSON endpoint occasionally returns rich profile info
    without full login. It’s rate-limited and sometimes needs cookies, but is
    worth trying before/after page JSON depending on --prefer-mobile.
    """
    try:
        sess = retry_session()
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            "Accept": "application/json",
            "X-IG-App-ID": "936619743392459",  # common public app id used by web
            "Referer": f"https://www.instagram.com/{username}/",
        }
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        r = sess.get(url, headers=headers, timeout=20)
        if r.status_code != 200 or "application/json" not in r.headers.get("content-type",""):
            logger.debug(f"mobile web_profile_info HTTP {r.status_code}")
            return None
        js = r.json()
        user = (js.get("data", {}).get("user") or js.get("user"))
        return _shape_snapshot_from_user(user, username)
    except Exception as e:
        logger.debug(f"fetch_profile_unauth_via_mobile error: {e}")
        return None

def fetch_post_via_embed(shortcode: str) -> Optional[dict]:
    """
    Method E: Parse OG/meta from the public embed page as a last-resort fallback.
    """
    try:
        sess = retry_session()
        url = f"https://www.instagram.com/p/{shortcode}/embed/"
        r = sess.get(url, headers=_build_headers(), timeout=20)
        if r.status_code >= 400:
            return None
        # Minimal OG scrape
        from html import unescape
        import re
        meta = {}
        for m in re.finditer(r'<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"', r.text, flags=re.I):
            k, v = m.group(1).strip(), unescape(m.group(2))
            meta[k] = v
        # Normalize a tiny structure
        return {
            "source": "embed",
            "shortcode": shortcode,
            "og": {
                "title": meta.get("og:title"),
                "description": meta.get("og:description"),
                "image": meta.get("og:image"),
                "url": meta.get("og:url"),
                "site_name": meta.get("og:site_name"),
                "type": meta.get("og:type"),
            }
        }
    except Exception as e:
        logger.debug(f"fetch_post_via_embed error: {e}")
        return None

def fetch_post_graphql_or_embed(shortcode: str) -> Optional[dict]:
    """
    Try GraphQL first; if it fails, fall back to embed OG scraper.
    """
    js = fetch_post_public_graphql(shortcode)
    if js:
        return {"source": "graphql", "shortcode": shortcode, "data": js}
    return fetch_post_via_embed(shortcode)


# =========================
# Instaloader Login / Context
# =========================

def login_loader(verbosity: int = 1) -> Instaloader:
    """Create Instaloader instance; try login if creds present."""
    L = Instaloader(
        download_pictures=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        quiet=(verbosity < 2),
        max_connection_attempts=3,
    )
    user = os.getenv("INSTAGRAM_SESSION_USERNAME") or os.getenv("IG_USERNAME")
    pwd  = os.getenv("INSTAGRAM_SESSION_PASSWORD") or os.getenv("IG_PASSWORD")

    if user and pwd:
        try:
            L.login(user, pwd)
            logger.info(f"Auth mode: logged in as {user}")
            return L
        except Exception as e:
            logger.error(f"Login failed: {e}. Continuing in anonymous mode.")

    logger.info("Auth mode: anonymous (limited data; friends not available)")
    return L

def require_login_or_die(L: Instaloader, feature: str) -> None:
    if not getattr(L.context, "username", None):
        logger.error(f"{feature} requires login. Set INSTAGRAM_SESSION_USERNAME / INSTAGRAM_SESSION_PASSWORD.")
        sys.exit(2)


# =========================
# Profile Data
# =========================

def safe_int(x) -> int:
    try:
        return int(x)
    except Exception:
        return 0

def fetch_profile_snapshot(L: Instaloader, username: str) -> ProfileSnapshot:
    """
    Fetch basic profile fields with layered fallbacks:
      (1) Instaloader (login or anonymous)
      (2) Optional: Mobile web JSON (Method G) if --prefer-mobile set
      (3) Page-embedded JSON (Method A)
      (4) If FORCE_UNAUTH_ONLY: skip (1) and go straight to (2)/(3)
    """
    # Unauth-only shortcut
    if FORCE_UNAUTH_ONLY:
        if args_prefer_mobile():
            snap = fetch_profile_unauth_via_mobile(username) or fetch_profile_unauth_via_page(username)
        else:
            snap = fetch_profile_unauth_via_page(username) or fetch_profile_unauth_via_mobile(username)
        if snap:
            return snap
        logger.error("Unauth-only mode failed to fetch profile.")
        sys.exit(1)

    # 1) Instaloader first (robust for core fields)
    snap = None
    try:
        profile = Profile.from_username(L.context, username)
        snap = ProfileSnapshot(
            username=profile.username.lower(),
            full_name=profile.full_name or "",
            biography=profile.biography or "",
            is_private=bool(profile.is_private),
            is_verified=bool(profile.is_verified),
            followers=safe_int(profile.followers),
            following=safe_int(profile.followees),
            posts=safe_int(profile.mediacount),
            profile_pic_url=str(profile.profile_pic_url) if getattr(profile, "profile_pic_url", None) else None,
            last_updated=now_iso(),
        )
    except igx.ProfileNotExistsException:
        logger.error(f"Profile '{username}' does not exist.")
        sys.exit(1)
    except Exception as e:
        logger.warning(f"Instaloader failed for '{username}' ({e}); will try unauth fallbacks.")

    # 2/3) Unauth fallbacks (order controlled by --prefer-mobile)
    try:
        def _fallback_chain():
            if args_prefer_mobile():
                yield fetch_profile_unauth_via_mobile(username)
                yield fetch_profile_unauth_via_page(username)
            else:
                yield fetch_profile_unauth_via_page(username)
                yield fetch_profile_unauth_via_mobile(username)

        if snap is None or not snap.profile_pic_url:
            for alt in _fallback_chain():
                if not alt:
                    continue
                if snap is None:
                    snap = alt
                    break
                # merge better PFP or missing text fields
                if not snap.profile_pic_url and alt.profile_pic_url:
                    snap = ProfileSnapshot(
                        username=snap.username or alt.username,
                        full_name=snap.full_name or alt.full_name,
                        biography=snap.biography or alt.biography,
                        is_private=snap.is_private,
                        is_verified=snap.is_verified,
                        followers=snap.followers or alt.followers,
                        following=snap.following or alt.following,
                        posts=snap.posts or alt.posts,
                        profile_pic_url=alt.profile_pic_url,
                        last_updated=now_iso(),
                    )
                    break
    except Exception as e:
        logger.debug(f"Unauth fallback chain error: {e}")

    if snap is None:
        logger.error(f"Could not fetch profile for '{username}' via any method.")
        sys.exit(1)
    return snap

def save_profile_picture(url: str, filepath: Path) -> bool:
    """Best-effort profile picture download with retries."""
    try:
        sess = retry_session()
        headers = {"User-Agent": get_random_user_agent()}
        with sess.get(url, headers=headers, timeout=20, stream=True) as resp:
            resp.raise_for_status()
            with filepath.open("wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Failed to save profile picture: {e}")
        return False

def detect_changes(prev: Dict, curr: ProfileSnapshot) -> Dict:
    """Compare basic fields and return changes for bookkeeping."""
    changes = {}
    if not prev:
        return changes

    mapping = {
        "full_name": curr.full_name,
        "biography": curr.biography,
        "is_private": curr.is_private,
        "is_verified": curr.is_verified,
        "followers": curr.followers,
        "following": curr.following,
        "posts": curr.posts,
        "profile_pic_url": curr.profile_pic_url,
    }
    for k, v in mapping.items():
        if prev.get(k) != v:
            changes[k] = {"old": prev.get(k), "new": v}
    return changes


# =========================
# Friends (requires login)
# =========================

def list_followers(profile: Profile) -> List[str]:
    return [u.username.lower() for u in profile.get_followers()]

def list_following(profile: Profile) -> List[str]:
    return [u.username.lower() for u in profile.get_followees()]

def extract_friends(L: Instaloader, username: str) -> Dict:
    """Return followers, following, and mutuals."""
    require_login_or_die(L, "Friends extraction")
    try:
        profile = Profile.from_username(L.context, username)
    except Exception as e:
        logger.error(f"Cannot load profile '{username}' for friends: {e}")
        sys.exit(1)

    followers = list_followers(profile)
    following = list_following(profile)
    set_f = set(followers)
    set_g = set(following)
    mutuals = sorted(set_f & set_g)

    return {
        "target": profile.username.lower(),
        "followers": sorted(followers),
        "following": sorted(following),
        "mutuals": mutuals,
        "counts": {
            "followers": len(followers),
            "following": len(following),
            "mutuals": len(mutuals),
            "ratio_ff": round(len(followers) / len(following), 2) if len(following) else 0.0
        },
        "updated_at": now_iso(),
        "schema": "v1",
    }


# =========================
# File I/O Contract (monitor mode)
# =========================

def write_monitor_outputs(base_dir: Path, snap: ProfileSnapshot, changes: Dict) -> Tuple[Path, Path]:
    """Writes latest.json and history.json into base_dir."""
    latest_path = base_dir / "latest.json"
    history_path = base_dir / "history.json"

    latest = {
        "username": snap.username,
        "full_name": snap.full_name,
        "biography": snap.biography,
        "is_private": snap.is_private,
        "is_verified": snap.is_verified,
        "followers": snap.followers,
        "following": snap.following,
        "posts": snap.posts,
        "profile_pic_url": snap.profile_pic_url,
        "last_updated": snap.last_updated,
        "schema": "v1",
    }

    # Append to history
    history = json_load(history_path, [])
    history.append({
        "timestamp": snap.last_updated,
        "snapshot": latest,
        "changes": changes,
    })

    json_dump_atomic(latest_path, latest)
    json_dump_atomic(history_path, history)

    return latest_path, history_path


# =========================
# CLI
# =========================

FORCE_UNAUTH_ONLY = False  # set by --unauth-only
_PREFER_MOBILE = False     # set by --prefer-mobile

def args_prefer_mobile() -> bool:
    return _PREFER_MOBILE

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Instagram monitoring and friends extraction")
    p.add_argument("--mode", choices=["monitor", "friends"], help="Operation mode")
    p.add_argument("--target-user", help="Target username (no @)")
    p.add_argument("--output-dir", help="Directory for monitor mode outputs (e.g., monitoring_data/<user>)")
    p.add_argument("--out", help="Output file for friends analysis (e.g., data/<user>_friends_analysis.json)")
    p.add_argument("--download-pfp", action="store_true", help="Download profile picture (monitor mode)")
    p.add_argument("--verbosity", type=int, default=1, help="0=quiet, 1=info, 2=debug")
    p.add_argument("--unauth-only", action="store_true", help="Skip Instaloader; use unauth scraping only")
    p.add_argument("--prefer-mobile", action="store_true",
                   help="When fetching a profile, try mobile web JSON before page HTML JSON")
    # Post/reel mode:
    p.add_argument("--shortcode", help="Post/Reel shortcode for post detail pull (unauth)")
    p.add_argument("--post-out", help="Output file for post JSON (used with --shortcode)")
    return p

def main():
    args = build_parser().parse_args()
    # Update logger verbosity
    global logger, FORCE_UNAUTH_ONLY, _PREFER_MOBILE
    logger = setup_logger(args.verbosity)
    FORCE_UNAUTH_ONLY = bool(args.unauth_only)
    _PREFER_MOBILE = bool(getattr(args, "prefer_mobile", False))

    # Standalone post/reel JSON path
    if args.shortcode:
        data = fetch_post_graphql_or_embed(args.shortcode)
        if not data:
            logger.error("Failed to fetch post via GraphQL or embed fallbacks.")
            sys.exit(1)
        if args.post_out:
            outp = Path(args.post_out)
            json_dump_atomic(outp, data)
            logger.info(f"Wrote post JSON: {outp}")
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        sys.exit(0)

    # Below paths require a target user and mode
    if not args.mode or not args.target_user:
        logger.error("For profile operations you must supply --mode and --target-user")
        sys.exit(1)

    username = normalize_username(args.target_user)
    if not username:
        logger.error("Invalid --target-user")
        sys.exit(1)

    L = login_loader(verbosity=args.verbosity)

    if args.mode == "friends":
        if not args.out:
            logger.error("--out is required for --mode friends")
            sys.exit(1)
        data = extract_friends(L, username)
        out_path = Path(args.out)
        json_dump_atomic(out_path, data)
        logger.info(f"Wrote friends analysis: {out_path}")
        sys.exit(0)

    # monitor mode
    if args.mode == "monitor":
        if not args.output_dir:
            logger.error("--output-dir is required for --mode monitor")
            sys.exit(1)
        base_dir = Path(args.output_dir)
        base_dir.mkdir(parents=True, exist_ok=True)

        snap = fetch_profile_snapshot(L, username)

        # If requested, download profile picture best-effort
        if args.download_pfp and snap.profile_pic_url:
            pfp_path = base_dir / "profile_pic.jpg"
            ok = save_profile_picture(snap.profile_pic_url, pfp_path)
            if ok:
                logger.info(f"Saved profile picture → {pfp_path}")

        latest_path = base_dir / "latest.json"
        prev_latest = json_load(latest_path, {})

        changes = detect_changes(prev_latest, snap)
        write_monitor_outputs(base_dir, snap, changes)

        if changes:
            logger.info(f"Detected changes: {', '.join(changes.keys())}")
        else:
            logger.info("No changes detected.")

        logger.info(f"Wrote: {latest_path} and {base_dir / 'history.json'}")
        sys.exit(0)

    # Should not reach here
    sys.exit(1)


if __name__ == "__main__":
    main()
