#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Instagram Monitor
- monitor mode: track basic profile changes over time
- friends mode: extract followers, following, and mutuals (requires login)

CLI:
  monitor.py --mode monitor --target-user USER --output-dir monitoring_data/USER
  monitor.py --mode friends --target-user USER --out data/USER_friends_analysis.json
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
from requests.adapters import HTTPAdapter, Retry

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
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbosity > 1 else logging.INFO)
    fmt = logging.Formatter("[%(levelname)s] %(message)s")
    ch.setFormatter(fmt)
    # Avoid duplicate handlers if reimported
    if not logger.handlers:
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

def safe_int(x) -> int:
    try:
        return int(x)
    except Exception:
        return 0

def fetch_profile_snapshot(L: Instaloader, username: str) -> ProfileSnapshot:
    """Fetch basic profile fields. Works in anonymous mode."""
    try:
        profile = Profile.from_username(L.context, username)
    except igx.ProfileNotExistsException:
        logger.error(f"Profile '{username}' does not exist.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Failed to load profile '{username}': {e}")
        sys.exit(1)

    try:
        full_name = profile.full_name or ""
        bio = profile.biography or ""
        is_private = bool(profile.is_private)
        is_verified = bool(profile.is_verified)
        followers = safe_int(profile.followers)
        followees = safe_int(profile.followees)
        posts = safe_int(profile.mediacount)
        pfp_url = profile.profile_pic_url if hasattr(profile, "profile_pic_url") else None
    except Exception as e:
        logger.error(f"Error reading fields for '{username}': {e}")
        sys.exit(1)

    snap = ProfileSnapshot(
        username=profile.username.lower(),
        full_name=full_name,
        biography=bio,
        is_private=is_private,
        is_verified=is_verified,
        followers=followers,
        following=followees,
        posts=posts,
        profile_pic_url=str(pfp_url) if pfp_url else None,
        last_updated=now_iso(),
    )
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

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Instagram monitoring and friends extraction")
    p.add_argument("--mode", choices=["monitor", "friends"], required=True, help="Operation mode")
    p.add_argument("--target-user", required=True, help="Target username (no @)")
    p.add_argument("--output-dir", help="Directory for monitor mode outputs (e.g., monitoring_data/<user>)")
    p.add_argument("--out", help="Output file for friends analysis (e.g., data/<user>_friends_analysis.json)")
    p.add_argument("--download-pfp", action="store_true", help="Download profile picture (monitor mode)")
    p.add_argument("--verbosity", type=int, default=1, help="0=quiet, 1=info, 2=debug")
    return p

def main():
    args = build_parser().parse_args()
    # Update logger verbosity
    global logger
    logger = setup_logger(args.verbosity)

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
