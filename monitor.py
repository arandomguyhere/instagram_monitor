#!/usr/bin/env python3
"""
Instagram Monitor - GitHub Actions Edition (Authentication Aware)
Always writes BOTH monitoring_summary.json and quick_stats.json.
FIXED: Enhanced profile picture URL extraction and handling.
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter, Retry

try:
    from instaloader import Instaloader, Profile
    from instaloader.exceptions import LoginRequiredException, ProfileNotExistsException
except ImportError:
    print("Error: instaloader not found. Install with: pip install instaloader")
    sys.exit(1)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def get_random_user_agent() -> str:
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    return random.choice(user_agents)


def _unescape(s: str) -> str:
    try:
        return bytes(s, "utf-8").decode("unicode_escape")
    except Exception:
        return s


def load_historical_data(filepath: Path) -> dict:
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load historical data: {e}")
    return {}


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically to avoid partial files in CI."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)


def detect_changes(current: dict, historical: dict) -> dict:
    changes = {"has_changes": False, "changes_detected": [], "timestamp": datetime.now(timezone.utc).isoformat()}

    if not historical:
        changes["changes_detected"].append("First time monitoring this user")
        changes["has_changes"] = True
        return changes

    def _cmp(field, label=None):
        old = historical.get(field, 0 if field in ("followers", "following", "posts") else "")
        new = current.get(field, old)
        if new != old:
            label = label or field.title()
            if isinstance(new, (int, float)) and isinstance(old, (int, float)):
                diff = new - old
                changes["changes_detected"].append(f"{label}: {old:,} → {new:,} ({diff:+,})")
            else:
                changes["changes_detected"].append(f"{label} changed")
            changes["has_changes"] = True

    _cmp("followers", "Followers")
    _cmp("following", "Following")
    _cmp("posts", "Posts")
    _cmp("bio", "Bio")
    _cmp("full_name", "Display name")
    if bool(current.get("is_private", False)) != bool(historical.get("is_private", False)):
        status = "private" if current.get("is_private", False) else "public"
        changes["changes_detected"].append(f"Account is now {status}")
        changes["has_changes"] = True

    return changes


# FIXED: Enhanced profile picture URL extraction
def get_profile_pic_urls(profile):
    """Extract multiple profile picture URL options for better fallbacks."""
    urls = {}
    
    try:
        # Try to get the standard profile pic URL
        if hasattr(profile, 'profile_pic_url') and profile.profile_pic_url:
            url = str(profile.profile_pic_url)
            # Clean up common URL issues
            if url and not url.startswith('http'):
                url = 'https:' + url if url.startswith('//') else 'https://' + url
            urls['profile_pic_url'] = url
            
        # Try to get HD version
        if hasattr(profile, 'profile_pic_url_hd') and profile.profile_pic_url_hd:
            url_hd = str(profile.profile_pic_url_hd)
            if url_hd and not url_hd.startswith('http'):
                url_hd = 'https:' + url_hd if url_hd.startswith('//') else 'https://' + url_hd
            urls['profile_pic_url_hd'] = url_hd
        
        # Sometimes there's a different resolution available in the node
        if hasattr(profile, '_node') and profile._node:
            node = profile._node
            if 'profile_pic_url' in node and node['profile_pic_url']:
                url = str(node['profile_pic_url'])
                if url and not url.startswith('http'):
                    url = 'https:' + url if url.startswith('//') else 'https://' + url
                urls['profile_pic_url'] = url
                
            if 'profile_pic_url_hd' in node and node['profile_pic_url_hd']:
                url_hd = str(node['profile_pic_url_hd'])
                if url_hd and not url_hd.startswith('http'):
                    url_hd = 'https:' + url_hd if url_hd.startswith('//') else 'https://' + url_hd
                urls['profile_pic_url_hd'] = url_hd
                
        # Log what we found
        logger.debug(f"Extracted profile pic URLs: {urls}")
                
    except Exception as e:
        logger.debug(f"Error extracting profile pic URLs: {e}")
    
    # Ensure we always have fallback values
    if not urls.get('profile_pic_url'):
        urls['profile_pic_url'] = ''
    if not urls.get('profile_pic_url_hd'):
        urls['profile_pic_url_hd'] = urls.get('profile_pic_url', '')
    
    return urls


# ---------- Data collection methods ----------
def try_web_scraping_method(username: str) -> dict | None:
    try:
        logger.info("Trying web scraping fallback method...")
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
        )
        retries = Retry(total=3, backoff_factor=0.8, status_forcelist=(429, 500, 502, 503, 504))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        time.sleep(random.uniform(1, 3))
        url = f"https://www.instagram.com/{username}/"
        resp = session.get(url, timeout=15)

        if resp.status_code == 404:
            raise ProfileNotExistsException(f"Profile {username} does not exist")
        resp.raise_for_status()
        html = resp.text

        full_name = username
        followers = following = posts = 0
        bio = ""
        is_private = False
        is_verified = False
        profile_pic_url = ""
        profile_pic_url_hd = ""

        # JSON-LD sometimes present
        m_ld = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html)
        if m_ld:
            try:
                ld = json.loads(m_ld.group(1))
                full_name = ld.get("name", full_name) or full_name
            except json.JSONDecodeError:
                pass

        followers_match = re.search(r'"edge_followed_by":{"count":(\d+)}', html)
        following_match = re.search(r'"edge_follow":{"count":(\d+)}', html)
        posts_match = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html)
        name_match = re.search(r'"full_name":"([^"]*)"', html)
        bio_match = re.search(r'"biography":"([^"]*)"', html)
        private_match = re.search(r'"is_private":(true|false)', html)
        verified_match = re.search(r'"is_verified":(true|false)', html)
        
        # FIXED: Better profile pic extraction from web scraping
        pic_match = re.search(r'"profile_pic_url":"([^"]*)"', html)
        pic_hd_match = re.search(r'"profile_pic_url_hd":"([^"]*)"', html)

        full_name = _unescape(name_match.group(1)) if name_match else full_name
        followers = int(followers_match.group(1)) if followers_match else followers
        following = int(following_match.group(1)) if following_match else following
        posts = int(posts_match.group(1)) if posts_match else posts
        bio = _unescape(bio_match.group(1)).replace("\\n", "\n") if bio_match else bio
        is_private = private_match.group(1) == "true" if private_match else is_private
        is_verified = verified_match.group(1) == "true" if verified_match else is_verified
        
        # FIXED: Clean up profile pic URLs
        if pic_match:
            profile_pic_url = _unescape(pic_match.group(1))
            if profile_pic_url and not profile_pic_url.startswith('http'):
                profile_pic_url = 'https:' + profile_pic_url if profile_pic_url.startswith('//') else 'https://' + profile_pic_url
        
        if pic_hd_match:
            profile_pic_url_hd = _unescape(pic_hd_match.group(1))
            if profile_pic_url_hd and not profile_pic_url_hd.startswith('http'):
                profile_pic_url_hd = 'https:' + profile_pic_url_hd if profile_pic_url_hd.startswith('//') else 'https://' + profile_pic_url_hd
        else:
            profile_pic_url_hd = profile_pic_url  # Fallback to normal if HD not found

        return {
            "username": username,
            "full_name": full_name or username,
            "followers": followers,
            "following": following,
            "posts": posts,
            "bio": bio,
            "is_private": is_private,
            "is_verified": is_verified,
            "profile_pic_url": profile_pic_url,
            "profile_pic_url_hd": profile_pic_url_hd,
            "method": "web_scraping",
        }
    except Exception as e:
        logger.warning(f"Web scraping method failed: {e}")
        return None


def _make_instaloader() -> Instaloader:
    L = Instaloader(quiet=True, download_videos=False, download_comments=False, save_metadata=False)
    # Set UA on context; constructor UA is ignored by Instaloader
    L.context.user_agent = get_random_user_agent()
    return L


def try_instaloader_with_session(username: str) -> dict | None:
    try:
        session_user = os.getenv("INSTAGRAM_SESSION_USERNAME")
        session_pass = os.getenv("INSTAGRAM_SESSION_PASSWORD")
        if not session_user or not session_pass:
            logger.info("No session credentials found, skipping authenticated method")
            return None

        logger.info("Attempting authenticated Instagram access...")
        L = _make_instaloader()
        try:
            L.load_session_from_file(session_user)
            logger.info("Loaded existing session")
        except FileNotFoundError:
            logger.info("Logging in with credentials...")
            L.login(session_user, session_pass)
            if os.getenv("CI") != "true":
                L.save_session_to_file()
                logger.info("New session created and saved locally")
            else:
                logger.info("Running in CI - session not persisted")

        profile = Profile.from_username(L.context, username)

        # FIXED: Use enhanced profile pic extraction
        pic_urls = get_profile_pic_urls(profile)

        data = {
            "username": profile.username,
            "full_name": profile.full_name or profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "bio": profile.biography or "",
            "is_private": profile.is_private,
            "is_verified": bool(getattr(profile, "is_verified", False)),
            "profile_pic_url": pic_urls.get('profile_pic_url', ''),
            "profile_pic_url_hd": pic_urls.get('profile_pic_url_hd', ''),
            "method": "authenticated_api",
        }

        # Optional enrich
        try:
            data["external_url"] = getattr(profile, "external_url", None)
            if profile.mediacount:
                post = next(profile.get_posts(), None)
                if post:
                    data["last_post_date"] = post.date_utc.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

        return data
    except Exception as e:
        logger.warning(f"Authenticated method failed: {e}")
        return None


def try_instaloader_anonymous(username: str) -> dict | None:
    try:
        logger.info("Attempting anonymous Instagram access...")
        L = _make_instaloader()
        profile = Profile.from_username(L.context, username)
        
        # FIXED: Use enhanced profile pic extraction
        pic_urls = get_profile_pic_urls(profile)
        
        data = {
            "username": profile.username,
            "full_name": profile.full_name or profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "bio": profile.biography or "",
            "is_private": profile.is_private,
            "is_verified": bool(getattr(profile, "is_verified", False)),
            "profile_pic_url": pic_urls.get('profile_pic_url', ''),
            "profile_pic_url_hd": pic_urls.get('profile_pic_url_hd', ''),
            "method": "anonymous_api",
        }
        try:
            data["external_url"] = getattr(profile, "external_url", None)
            if profile.mediacount:
                post = next(profile.get_posts(), None)
                if post:
                    data["last_post_date"] = post.date_utc.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
        return data
    except LoginRequiredException:
        logger.warning("Anonymous method failed: Login required")
        return None
    except ProfileNotExistsException:
        logger.error(f"Profile {username} does not exist")
        return None
    except Exception as e:
        logger.warning(f"Anonymous method failed: {e}")
        return None


def create_fallback_data(username: str) -> dict:
    logger.info("Creating fallback data structure...")
    return {
        "username": username,
        "full_name": username,
        "followers": 0,
        "following": 0,
        "posts": 0,
        "bio": "",
        "is_private": True,
        "is_verified": False,
        "profile_pic_url": "",
        "profile_pic_url_hd": "",
        "method": "fallback",
        "error": "Unable to access profile data - may be private or restricted",
    }


# ---------- Orchestration ----------
def fetch_profile_data(target_user: str, output_dir: str = "./", history_keep: int = 100) -> bool:
    """Fetch data; ALWAYS write monitoring_summary.json and quick_stats.json."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "monitoring_summary.json"
    history_file = output_path / "monitoring_history.json"
    stats_file = output_path / "quick_stats.json"

    historical_summary = load_historical_data(summary_file)
    history_data = load_historical_data(history_file) or {"entries": [], "username": target_user}

    logger.info(f"Fetching data for: {target_user}")

    profile_data = (
        try_instaloader_with_session(target_user)
        or try_instaloader_anonymous(target_user)
        or try_web_scraping_method(target_user)
        or create_fallback_data(target_user)
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    current_data = {
        **profile_data,
        "timestamp": now_iso,
        "profile_url": f"https://instagram.com/{target_user}",
        "external_url": profile_data.get("external_url", None),
        "has_stories": False,
        "story_count": 0,
        "monitoring_session": profile_data.get("method") == "authenticated_api",
        "last_post_date": profile_data.get("last_post_date", None),
        "engagement_rate": 0.0,
        "data_collection_method": profile_data.get("method", "unknown"),
    }

    # Detect & attach changes (based on last summary if present)
    changes = detect_changes(current_data, historical_summary)
    current_data["changes"] = changes

    # ------- QUICK STATS (always) -------
    quick_stats = {
        "username": current_data["username"],
        "followers": int(current_data.get("followers", 0) or 0),
        "following": int(current_data.get("following", 0) or 0),
        "posts": int(current_data.get("posts", 0) or 0),
        "last_updated": now_iso,
        "is_private": bool(current_data.get("is_private", False)),
        "is_verified": bool(current_data.get("is_verified", False)),
        "method": current_data.get("data_collection_method"),
        "profile_pic_url": current_data.get("profile_pic_url", ""),
        "profile_pic_url_hd": current_data.get("profile_pic_url_hd", ""),
    }
    write_json_atomic(stats_file, quick_stats)

    # ------- SUMMARY (always) -------
    write_json_atomic(summary_file, current_data)

    # ------- HISTORY (always) -------
    history_entry = {
        "timestamp": now_iso,
        "followers": quick_stats["followers"],
        "following": quick_stats["following"],
        "posts": quick_stats["posts"],
        "is_private": quick_stats["is_private"],
        "method": quick_stats["method"],
    }
    history_data.setdefault("entries", []).append(history_entry)
    history_data["entries"] = history_data["entries"][-int(history_keep):]
    history_data["last_updated"] = now_iso
    history_data["username"] = target_user
    write_json_atomic(history_file, history_data)

    # Logs
    logger.info("✅ Data collection completed successfully")
    logger.info(f"   Method used: {current_data['data_collection_method']}")
    logger.info(f"   Output directory: {output_path.absolute()}")
    logger.info(f"   Profile: @{current_data['username']} ({current_data['full_name']})")
    logger.info(f"   Followers: {current_data['followers']:,}")
    logger.info(f"   Following: {current_data['following']:,}")
    logger.info(f"   Posts: {current_data['posts']:,}")
    logger.info(f"   Private: {current_data['is_private']}")
    logger.info(f"   Verified: {current_data['is_verified']}")
    logger.info(f"   Profile pic URL: {current_data.get('profile_pic_url', 'None')[:100]}...")
    logger.info(f"   Profile pic HD URL: {current_data.get('profile_pic_url_hd', 'None')[:100]}...")
    if "error" in current_data:
        logger.warning(f"   Note: {current_data['error']}")

    if changes["has_changes"]:
        logger.info(f"   Changes detected: {len(changes['changes_detected'])}")
        for change in changes["changes_detected"]:
            logger.info(f"     • {change}")
    else:
        logger.info("   No changes detected since last run")

    logger.info("   Generated files:")
    for file in sorted(output_path.glob("*.json")):
        logger.info(f"     • {file.name}")
    return True


# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(
        description="Monitor Instagram profile stats with multiple fallback methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py --target-user dominance.information
  python monitor.py --target-user cristiano --output-dir ./data/cristiano

Environment Variables:
  INSTAGRAM_SESSION_USERNAME - Instagram username for authenticated access
  INSTAGRAM_SESSION_PASSWORD - Instagram password for authenticated access
        """,
    )
    parser.add_argument("--target-user", required=True, help="Instagram username to monitor")
    parser.add_argument(
        "--output-dir",
        default="./",
        help="Output directory for data files (default: current directory). Pass per-user path, e.g. ./data/<user>",
    )
    parser.add_argument("--history-keep", type=int, default=100, help="Number of history entries to retain")
    args = parser.parse_args()

    user = args.target_user.replace("@", "").strip()
    if not user:
        logger.error("Invalid username provided")
        sys.exit(1)

    logger.info(f"Starting Instagram monitoring for: {user}")
    logger.info(f"Output directory: {Path(args.output_dir).absolute()}")

    if os.getenv("INSTAGRAM_SESSION_USERNAME"):
        logger.info("Authentication credentials found - will attempt authenticated access")
    else:
        logger.info("No authentication credentials - will use anonymous mode.")

    try:
        ok = fetch_profile_data(user, args.output_dir, args.history_keep)
        if not ok:
            logger.error("❌ Instagram monitoring failed")
            sys.exit(1)
        logger.info("🎉 Instagram monitoring completed successfully!")
    except KeyboardInterrupt:
        logger.info("❌ Monitoring cancelled by user")
        sys.exit(1)
    except Exception as e:
        # As a last resort, still write empty files so the UI doesn't break
        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)
        now_iso = datetime.now(timezone.utc).isoformat()
        fallback_quick = {
            "username": user, "followers": 0, "following": 0, "posts": 0,
            "last_updated": now_iso, "is_private": True, "is_verified": False,
            "method": "fallback", "profile_pic_url": "", "profile_pic_url_hd": ""
        }
        write_json_atomic(out / "quick_stats.json", fallback_quick)
        fallback_summary = {
            **fallback_quick,
            "full_name": user, "bio": "", "timestamp": now_iso,
            "profile_url": f"https://instagram.com/{user}",
            "data_collection_method": "fallback",
            "changes": {"has_changes": False, "changes_detected": [], "timestamp": now_iso}
        }
        write_json_atomic(out / "monitoring_summary.json", fallback_summary)
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
