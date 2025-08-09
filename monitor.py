#!/usr/bin/env python3
"""
Instagram Monitor - GitHub Actions Edition (Authentication Aware)
Handles Instagram's authentication requirements with multiple fallback methods
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
    from instaloader import Instaloader, Profile, ConnectionException
    from instaloader.exceptions import LoginRequiredException, ProfileNotExistsException
except ImportError:
    print("Error: instaloader not found. Install with: pip install instaloader")
    sys.exit(1)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------- Helpers ----------
def get_random_user_agent() -> str:
    """Get a random user agent to avoid detection"""
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
    """Load previous monitoring data if it exists"""
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load historical data: {e}")
    return {}


def detect_changes(current: dict, historical: dict) -> dict:
    """Detect changes between current and historical data"""
    changes = {
        "has_changes": False,
        "changes_detected": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not historical:
        changes["changes_detected"].append("First time monitoring this user")
        changes["has_changes"] = True
        return changes

    # Followers
    old_val = int(historical.get("followers", 0) or 0)
    new_val = int(current.get("followers", 0) or 0)
    if new_val != old_val:
        diff = new_val - old_val
        changes["changes_detected"].append(f"Followers: {old_val:,} → {new_val:,} ({diff:+,})")
        changes["has_changes"] = True

    # Following
    old_val = int(historical.get("following", 0) or 0)
    new_val = int(current.get("following", 0) or 0)
    if new_val != old_val:
        diff = new_val - old_val
        changes["changes_detected"].append(f"Following: {old_val:,} → {new_val:,} ({diff:+,})")
        changes["has_changes"] = True

    # Posts
    old_val = int(historical.get("posts", 0) or 0)
    new_val = int(current.get("posts", 0) or 0)
    if new_val != old_val:
        diff = new_val - old_val
        changes["changes_detected"].append(f"Posts: {old_val:,} → {new_val:,} ({diff:+,})")
        changes["has_changes"] = True

    # Bio
    if current.get("bio", "") != historical.get("bio", ""):
        changes["changes_detected"].append("Bio updated")
        changes["has_changes"] = True

    # Display name
    if current.get("full_name", "") != historical.get("full_name", ""):
        changes["changes_detected"].append("Display name changed")
        changes["has_changes"] = True

    # Privacy
    if bool(current.get("is_private", False)) != bool(historical.get("is_private", False)):
        status = "private" if current.get("is_private", False) else "public"
        changes["changes_detected"].append(f"Account is now {status}")
        changes["has_changes"] = True

    return changes


# ---------- Data collection methods ----------
def try_web_scraping_method(username: str) -> dict | None:
    """Fallback method using web scraping when API fails"""
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

        time.sleep(random.uniform(1, 3))  # jitter
        url = f"https://www.instagram.com/{username}/"
        response = session.get(url, timeout=15)

        if response.status_code == 404:
            raise ProfileNotExistsException(f"Profile {username} does not exist")

        response.raise_for_status()
        html_content = response.text

        # Attempt to parse embedded JSON first (more stable than scattered regex)
        full_name = username
        followers = following = posts = 0
        bio = ""
        is_private = False
        is_verified = False
        profile_pic_url = ""

        # <script type="application/ld+json">...</script> (sometimes present)
        m_ld = re.search(r'<script type="application/ld\+json">([^<]+)</script>', html_content)
        if m_ld:
            try:
                ld = json.loads(m_ld.group(1))
                full_name = ld.get("name", full_name) or full_name
            except json.JSONDecodeError:
                pass

        # Legacy blobs that used to contain counts
        m_blob = re.search(r'>\s*window\.__additionalDataLoaded__\s*\(\s*[^,]+,\s*({.*?})\s*\)\s*;<', html_content)
        if m_blob:
            try:
                data = json.loads(m_blob.group(1))
                # Best-effort extraction (schema may vary)
                # Keep defaults if keys are missing
            except json.JSONDecodeError:
                pass

        # Regex fallbacks for counts and other fields
        followers_match = re.search(r'"edge_followed_by":{"count":(\d+)}', html_content)
        following_match = re.search(r'"edge_follow":{"count":(\d+)}', html_content)
        posts_match = re.search(r'"edge_owner_to_timeline_media":{"count":(\d+)}', html_content)
        name_match = re.search(r'"full_name":"([^"]*)"', html_content)
        bio_match = re.search(r'"biography":"([^"]*)"', html_content)
        private_match = re.search(r'"is_private":(true|false)', html_content)
        verified_match = re.search(r'"is_verified":(true|false)', html_content)
        pic_match = re.search(r'"profile_pic_url":"([^"]*)"', html_content)

        full_name = _unescape(name_match.group(1)) if name_match else full_name
        followers = int(followers_match.group(1)) if followers_match else followers
        following = int(following_match.group(1)) if following_match else following
        posts = int(posts_match.group(1)) if posts_match else posts
        bio = _unescape(bio_match.group(1)).replace("\\n", "\n") if bio_match else bio
        is_private = private_match.group(1) == "true" if private_match else is_private
        is_verified = verified_match.group(1) == "true" if verified_match else is_verified
        profile_pic_url = _unescape(pic_match.group(1)) if pic_match else profile_pic_url

        profile_data = {
            "username": username,
            "full_name": full_name or username,
            "followers": followers,
            "following": following,
            "posts": posts,
            "bio": bio,
            "is_private": is_private,
            "is_verified": is_verified,
            "profile_pic_url": profile_pic_url,
            "method": "web_scraping",
        }

        logger.info("✅ Web scraping method successful")
        return profile_data

    except Exception as e:
        logger.warning(f"Web scraping method failed: {e}")
        return None


def _make_instaloader() -> Instaloader:
    L = Instaloader(
        quiet=True,
        download_videos=False,
        download_comments=False,
        save_metadata=False,
    )
    # IMPORTANT: set UA on context; constructor arg is ignored
    L.context.user_agent = get_random_user_agent()
    return L


def try_instaloader_with_session(username: str) -> dict | None:
    """Try to use Instaloader with session credentials if available"""
    try:
        session_user = os.getenv("INSTAGRAM_SESSION_USERNAME")
        session_pass = os.getenv("INSTAGRAM_SESSION_PASSWORD")

        if not session_user or not session_pass:
            logger.info("No session credentials found, skipping authenticated method")
            return None

        logger.info("Attempting authenticated Instagram access...")
        L = _make_instaloader()

        # Try to load existing session or login
        try:
            L.load_session_from_file(session_user)
            logger.info("Loaded existing session")
        except FileNotFoundError:
            logger.info("Logging in with credentials...")
            L.login(session_user, session_pass)
            # Avoid committing session artifacts in CI
            if os.getenv("CI") != "true":
                L.save_session_to_file()
                logger.info("New session created and saved locally")
            else:
                logger.info("Running in CI - session not persisted")

        profile = Profile.from_username(L.context, username)

        profile_data = {
            "username": profile.username,
            "full_name": profile.full_name or profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "bio": profile.biography or "",
            "is_private": profile.is_private,
            "is_verified": bool(getattr(profile, "is_verified", False)),
            "profile_pic_url": str(profile.profile_pic_url) if getattr(profile, "profile_pic_url", None) else "",
            "method": "authenticated_api",
        }

        # Optional enrich (best-effort, safe in try/except)
        try:
            profile_data["external_url"] = getattr(profile, "external_url", None)
            if profile.mediacount:
                # This may do an extra request; keep it quick
                post = next(profile.get_posts(), None)
                if post:
                    profile_data["last_post_date"] = post.date_utc.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

        logger.info("✅ Authenticated method successful")
        return profile_data

    except Exception as e:
        logger.warning(f"Authenticated method failed: {e}")
        return None


def try_instaloader_anonymous(username: str) -> dict | None:
    """Try basic Instaloader without authentication"""
    try:
        logger.info("Attempting anonymous Instagram access...")
        L = _make_instaloader()

        profile = Profile.from_username(L.context, username)

        profile_data = {
            "username": profile.username,
            "full_name": profile.full_name or profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "posts": profile.mediacount,
            "bio": profile.biography or "",
            "is_private": profile.is_private,
            "is_verified": bool(getattr(profile, "is_verified", False)),
            "profile_pic_url": str(profile.profile_pic_url) if getattr(profile, "profile_pic_url", None) else "",
            "method": "anonymous_api",
        }

        # Optional enrich
        try:
            profile_data["external_url"] = getattr(profile, "external_url", None)
            if profile.mediacount:
                post = next(profile.get_posts(), None)
                if post:
                    profile_data["last_post_date"] = post.date_utc.replace(tzinfo=timezone.utc).isoformat()
        except Exception:
            pass

        logger.info("✅ Anonymous method successful")
        return profile_data

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
    """Create basic profile data when all methods fail"""
    logger.info("Creating fallback data structure...")

    return {
        "username": username,
        "full_name": username,
        "followers": 0,
        "following": 0,
        "posts": 0,
        "bio": "",
        "is_private": True,  # Assume private if we can't access
        "is_verified": False,
        "profile_pic_url": "",
        "method": "fallback",
        "error": "Unable to access profile data - may be private or restricted",
    }


# ---------- Orchestration ----------
def fetch_profile_data(target_user: str, output_dir: str = "./", history_keep: int = 100) -> bool:
    """Fetch Instagram profile data using multiple methods with fallbacks"""

    # Create output directory (do NOT append username here — pass per-user dir from CI)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "monitoring_summary.json"

    # Load historical data for change detection
    historical_data = load_historical_data(summary_file)

    logger.info(f"Fetching data for: {target_user}")

    # Try multiple methods in order of preference
    profile_data = (
        try_instaloader_with_session(target_user)
        or try_instaloader_anonymous(target_user)
        or try_web_scraping_method(target_user)
        or create_fallback_data(target_user)
    )

    # Add metadata to the profile data
    current_data = {
        **profile_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile_url": f"https://instagram.com/{target_user}",
        "external_url": profile_data.get("external_url", None),
        "has_stories": False,
        "story_count": 0,
        "monitoring_session": profile_data.get("method") == "authenticated_api",
        "last_post_date": profile_data.get("last_post_date", None),
        "engagement_rate": 0.0,
        "data_collection_method": profile_data.get("method", "unknown"),
    }

    # Detect changes
    changes = detect_changes(current_data, historical_data)
    current_data["changes"] = changes

    # Save main monitoring summary
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(current_data, f, indent=2, ensure_ascii=False)

    # Save historical tracking
    history_file = output_path / "monitoring_history.json"
    history_data = load_historical_data(history_file)
    if "entries" not in history_data:
        history_data["entries"] = []
        history_data["username"] = target_user

    history_entry = {
        "timestamp": current_data["timestamp"],
        "followers": int(current_data.get("followers", 0) or 0),
        "following": int(current_data.get("following", 0) or 0),
        "posts": int(current_data.get("posts", 0) or 0),
        "is_private": bool(current_data.get("is_private", False)),
        "method": current_data.get("data_collection_method"),
    }
    history_data["entries"].append(history_entry)
    history_data["entries"] = history_data["entries"][-int(history_keep):]
    history_data["last_updated"] = current_data["timestamp"]

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)

    # Create quick stats
    stats_file = output_path / "quick_stats.json"
    quick_stats = {
        "username": current_data["username"],
        "followers": int(current_data.get("followers", 0) or 0),
        "following": int(current_data.get("following", 0) or 0),
        "posts": int(current_data.get("posts", 0) or 0),
        "last_updated": current_data["timestamp"],
        "is_private": bool(current_data.get("is_private", False)),
        "is_verified": bool(current_data.get("is_verified", False)),
        "method": current_data.get("data_collection_method"),
    }

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(quick_stats, f, indent=2, ensure_ascii=False)

    # Log results
    logger.info("✅ Data collection completed successfully")
    logger.info(f"   Method used: {current_data['data_collection_method']}")
    logger.info(f"   Output directory: {output_path.absolute()}")
    logger.info(f"   Profile: @{current_data['username']} ({current_data['full_name']})")
    logger.info(f"   Followers: {current_data['followers']:,}")
    logger.info(f"   Following: {current_data['following']:,}")
    logger.info(f"   Posts: {current_data['posts']:,}")
    logger.info(f"   Private: {current_data['is_private']}")
    logger.info(f"   Verified: {current_data['is_verified']}")

    if "error" in current_data:
        logger.warning(f"   Note: {current_data['error']}")

    if changes["has_changes"]:
        logger.info(f"   Changes detected: {len(changes['changes_detected'])}")
        for change in changes["changes_detected"]:
            logger.info(f"     • {change}")
    else:
        logger.info("   No changes detected since last run")

    # List generated files
    logger.info("   Generated files:")
    for file in sorted(output_path.glob("*.json")):
        logger.info(f"     • {file.name}")

    # If we only had fallback, you can choose to fail CI by returning False
    return True


# ---------- CLI ----------
def main():
    parser = argparse.ArgumentParser(
        description="Monitor Instagram profile stats with multiple fallback methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py --target-user dominance.information
  python monitor.py --target-user cristiano --output-dir ./docs/data/cristiano

Environment Variables:
  INSTAGRAM_SESSION_USERNAME - Instagram username for authenticated access
  INSTAGRAM_SESSION_PASSWORD - Instagram password for authenticated access
        """,
    )

    parser.add_argument("--target-user", required=True, help="Instagram username to monitor")
    parser.add_argument(
        "--output-dir",
        default="./",
        help="Output directory for data files (default: current directory). "
             "Pass a per-user path from CI, e.g. ./docs/data/<user>",
    )
    parser.add_argument(
        "--history-keep",
        type=int,
        default=100,
        help="Number of history entries to retain (default: 100)",
    )

    args = parser.parse_args()

    # Clean username (remove @ if present)
    clean_username = args.target_user.replace("@", "").strip()
    if not clean_username:
        logger.error("Invalid username provided")
        sys.exit(1)

    logger.info(f"Starting Instagram monitoring for: {clean_username}")
    logger.info(f"Output directory: {Path(args.output_dir).absolute()}")

    # Check for authentication credentials
    if os.getenv("INSTAGRAM_SESSION_USERNAME"):
        logger.info("Authentication credentials found - will attempt authenticated access")
    else:
        logger.info("No authentication credentials - will use anonymous/fallback methods")

    try:
        success = fetch_profile_data(clean_username, args.output_dir, args.history_keep)
        if success:
            logger.info("🎉 Instagram monitoring completed successfully!")
        else:
            logger.error("❌ Instagram monitoring failed")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("❌ Monitoring cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
