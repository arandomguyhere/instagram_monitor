#!/usr/bin/env python3
"""
Enhanced Instagram Monitor - Now with Friends List functionality
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
import smtplib
import ssl
from datetime import datetime, timezone
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

import requests
from requests.adapters import HTTPAdapter, Retry

try:
    from instaloader import Instaloader, Profile
    from instaloader.exceptions import LoginRequiredException, ProfileNotExistsException
except ImportError:
    print("Error: instaloader not found. Install with: pip install instaloader")
    sys.exit(1)

# ---------- Enhanced Configuration ----------
ENABLE_EMAIL_NOTIFICATIONS = False
SMTP_HOST = ""
SMTP_PORT = 587
SMTP_USER = ""
SMTP_PASSWORD = ""
SMTP_SSL = True
SENDER_EMAIL = ""
RECEIVER_EMAIL = ""

DETECT_PROFILE_CHANGES = True
SAVE_PROFILE_PICTURES = True
TRACK_FOLLOWERS = True  # Now enabled by default for friends list
TRACK_FOLLOWINGS = True  # Now enabled by default for friends list
TRACK_POSTS = True
SHOW_FRIENDS_LIST = True  # New option for friends list

# Enhanced logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Enhanced Helper Functions ----------

def get_random_user_agent() -> str:
    """Generate random user agent to avoid detection"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    return random.choice(user_agents)

def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON atomically to avoid partial files"""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(path)

def send_email_notification(subject: str, body: str, html_body: str = "") -> bool:
    """Send email notification if configured"""
    if not ENABLE_EMAIL_NOTIFICATIONS or not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, SENDER_EMAIL, RECEIVER_EMAIL]):
        return False
    
    try:
        if SMTP_SSL:
            ssl_context = ssl.create_default_context()
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
            server.starttls(context=ssl_context)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        
        server.login(SMTP_USER, SMTP_PASSWORD)
        
        msg = MIMEMultipart('alternative')
        msg["From"] = SENDER_EMAIL
        msg["To"] = RECEIVER_EMAIL
        msg["Subject"] = str(Header(subject, 'utf-8'))
        
        # Add text version
        text_part = MIMEText(body.encode('utf-8'), 'plain', _charset='utf-8')
        msg.attach(text_part)
        
        # Add HTML version if provided
        if html_body:
            html_part = MIMEText(html_body.encode('utf-8'), 'html', _charset='utf-8')
            msg.attach(html_part)
        
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        logger.info(f"Email notification sent: {subject}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def save_profile_picture(url: str, filepath: str) -> bool:
    """Download and save profile picture"""
    try:
        response = requests.get(url, headers={'User-Agent': get_random_user_agent()}, timeout=15, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        logger.warning(f"Failed to save profile picture: {e}")
        return False

def compare_profile_pictures(file1: str, file2: str) -> bool:
    """Compare two profile pictures to detect changes"""
    if not (os.path.isfile(file1) and os.path.isfile(file2)):
        return False
    
    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            return f1.read() == f2.read()
    except Exception:
        return False

def detect_changes(current_data: dict, historical_data: dict) -> dict:
    """Detect changes between current and historical data"""
    changes = {
        "has_changes": False,
        "changes_detected": [],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    if not historical_data:
        changes["changes_detected"].append("First time monitoring this user")
        changes["has_changes"] = True
        return changes
    
    # Check for numerical changes
    for field, label in [("followers", "Followers"), ("following", "Following"), ("posts", "Posts")]:
        old_val = historical_data.get(field, 0)
        new_val = current_data.get(field, 0)
        if new_val != old_val:
            diff = new_val - old_val
            changes["changes_detected"].append(f"{label}: {old_val:,} → {new_val:,} ({diff:+,})")
            changes["has_changes"] = True
    
    # Check for text changes
    for field, label in [("bio", "Bio"), ("full_name", "Display name")]:
        old_val = historical_data.get(field, "")
        new_val = current_data.get(field, "")
        if new_val != old_val:
            changes["changes_detected"].append(f"{label} changed")
            changes["has_changes"] = True
    
    # Check privacy status
    old_private = bool(historical_data.get("is_private", False))
    new_private = bool(current_data.get("is_private", False))
    if old_private != new_private:
        status = "private" if new_private else "public"
        changes["changes_detected"].append(f"Account is now {status}")
        changes["has_changes"] = True
    
    return changes

# ---------- Friends List Functions ----------

def get_followers_list(profile) -> list:
    """Get list of followers"""
    try:
        return [follower.username for follower in profile.get_followers()]
    except Exception as e:
        logger.error(f"Failed to get followers: {e}")
        return []

def get_followings_list(profile) -> list:
    """Get list of followings"""
    try:
        return [followee.username for followee in profile.get_followees()]
    except Exception as e:
        logger.error(f"Failed to get followings: {e}")
        return []

def find_mutual_friends(followers: list, followings: list) -> list:
    """Find mutual friends (people who follow and are followed by the user)"""
    return list(set(followers) & set(followings))

def analyze_friend_changes(current_followers: list, previous_followers: list, 
                          current_followings: list, previous_followings: list) -> dict:
    """Analyze changes in friends lists"""
    changes = {
        "new_followers": list(set(current_followers) - set(previous_followers)),
        "lost_followers": list(set(previous_followers) - set(current_followers)),
        "new_followings": list(set(current_followings) - set(previous_followings)),
        "unfollowed": list(set(previous_followings) - set(current_followings)),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    return changes

def save_friends_data(username: str, followers: list, followings: list, output_dir: Path) -> None:
    """Save friends data to files"""
    followers_file = output_dir / f"{username}_followers.json"
    followings_file = output_dir / f"{username}_followings.json"
    friends_file = output_dir / f"{username}_friends_analysis.json"
    
    # Save followers and followings
    followers_data = {
        "count": len(followers),
        "list": followers,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    followings_data = {
        "count": len(followings),
        "list": followings,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    write_json_atomic(followers_file, followers_data)
    write_json_atomic(followings_file, followings_data)
    
    # Create friends analysis
    mutual_friends = find_mutual_friends(followers, followings)
    friends_analysis = {
        "username": username,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": {
            "followers_count": len(followers),
            "followings_count": len(followings),
            "mutual_friends_count": len(mutual_friends),
            "follower_following_ratio": round(len(followers) / len(followings), 2) if followings else 0
        },
        "mutual_friends": mutual_friends,
        "followers_only": list(set(followers) - set(followings)),
        "followings_only": list(set(followings) - set(followers))
    }
    
    write_json_atomic(friends_file, friends_analysis)
    logger.info(f"Friends data saved for {username}")

def load_previous_friends_data(username: str, output_dir: Path) -> tuple:
    """Load previous friends data"""
    followers_file = output_dir / f"{username}_followers.json"
    followings_file = output_dir / f"{username}_followings.json"
    
    previous_followers = []
    previous_followings = []
    
    try:
        if followers_file.exists():
            with open(followers_file, 'r', encoding="utf-8") as f:
                data = json.load(f)
                previous_followers = data.get("list", [])
    except Exception as e:
        logger.warning(f"Failed to load previous followers: {e}")
    
    try:
        if followings_file.exists():
            with open(followings_file, 'r', encoding="utf-8") as f:
                data = json.load(f)
                previous_followings = data.get("list", [])
    except Exception as e:
        logger.warning(f"Failed to load previous followings: {e}")
    
    return previous_followers, previous_followings

def display_friends_analysis(username: str, output_dir: Path) -> None:
    """Display friends analysis"""
    friends_file = output_dir / f"{username}_friends_analysis.json"
    
    if not friends_file.exists():
        logger.warning("No friends analysis data found")
        return
    
    try:
        with open(friends_file, 'r', encoding="utf-8") as f:
            data = json.load(f)
        
        print("\n" + "="*60)
        print(f"FRIENDS LIST ANALYSIS FOR @{username}")
        print("="*60)
        
        stats = data.get("stats", {})
        print(f"📊 STATISTICS:")
        print(f"   Followers: {stats.get('followers_count', 0):,}")
        print(f"   Following: {stats.get('followings_count', 0):,}")
        print(f"   Mutual Friends: {stats.get('mutual_friends_count', 0):,}")
        print(f"   Follower/Following Ratio: {stats.get('follower_following_ratio', 0)}")
        
        mutual_friends = data.get("mutual_friends", [])
        if mutual_friends:
            print(f"\n🤝 MUTUAL FRIENDS ({len(mutual_friends)}):")
            for i, friend in enumerate(mutual_friends[:20], 1):  # Show first 20
                print(f"   {i:2d}. @{friend}")
            if len(mutual_friends) > 20:
                print(f"   ... and {len(mutual_friends) - 20} more")
        
        followers_only = data.get("followers_only", [])
        if followers_only:
            print(f"\n👥 FOLLOWERS ONLY ({len(followers_only)}) [showing first 10]:")
            for i, follower in enumerate(followers_only[:10], 1):
                print(f"   {i:2d}. @{follower}")
        
        followings_only = data.get("followings_only", [])
        if followings_only:
            print(f"\n👤 FOLLOWING ONLY ({len(followings_only)}) [showing first 10]:")
            for i, following in enumerate(followings_only[:10], 1):
                print(f"   {i:2d}. @{following}")
        
        print("="*60)
        
    except Exception as e:
        logger.error(f"Failed to display friends analysis: {e}")

# ---------- Enhanced Profile Picture Detection ----------

def detect_profile_picture_changes(username: str, current_pic_url: str, output_dir: Path) -> dict:
    """Detect and handle profile picture changes"""
    if not SAVE_PROFILE_PICTURES or not current_pic_url:
        return {"changed": False}
    
    pic_dir = output_dir / "profile_pics"
    pic_dir.mkdir(exist_ok=True)
    
    current_pic_file = pic_dir / f"{username}_current.jpg"
    new_pic_file = pic_dir / f"{username}_new.jpg"
    
    # Download new picture
    if not save_profile_picture(current_pic_url, str(new_pic_file)):
        return {"changed": False, "error": "Failed to download"}
    
    # If no existing picture, this is the first time
    if not current_pic_file.exists():
        new_pic_file.rename(current_pic_file)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = pic_dir / f"{username}_{timestamp}.jpg"
        save_profile_picture(current_pic_url, str(archive_file))
        
        return {
            "changed": True,
            "type": "initial",
            "message": f"Initial profile picture saved for {username}"
        }
    
    # Compare with existing picture
    if compare_profile_pictures(str(current_pic_file), str(new_pic_file)):
        # No change
        new_pic_file.unlink()
        return {"changed": False}
    else:
        # Picture changed
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        old_archive = pic_dir / f"{username}_old_{timestamp}.jpg"
        current_pic_file.rename(old_archive)
        new_pic_file.rename(current_pic_file)
        
        # Save new version with timestamp
        new_archive = pic_dir / f"{username}_{timestamp}.jpg"
        save_profile_picture(current_pic_url, str(new_archive))
        
        return {
            "changed": True,
            "type": "update",
            "message": f"Profile picture changed for {username}",
            "old_file": str(old_archive),
            "new_file": str(new_archive)
        }

# ---------- Enhanced Data Collection ----------

def get_enhanced_profile_pic_urls(profile):
    """Extract multiple profile picture URL options with better error handling"""
    urls = {}
    
    try:
        # Standard profile pic URL
        if hasattr(profile, 'profile_pic_url') and profile.profile_pic_url:
            url = str(profile.profile_pic_url)
            if url and not url.startswith('http'):
                url = 'https:' + url if url.startswith('//') else 'https://' + url
            urls['profile_pic_url'] = url
            
        # HD version
        if hasattr(profile, 'profile_pic_url_hd') and profile.profile_pic_url_hd:
            url_hd = str(profile.profile_pic_url_hd)
            if url_hd and not url_hd.startswith('http'):
                url_hd = 'https:' + url_hd if url_hd.startswith('//') else 'https://' + url_hd
            urls['profile_pic_url_hd'] = url_hd
        
        # Try node data
        if hasattr(profile, '_node') and profile._node:
            node = profile._node
            for key in ['profile_pic_url', 'profile_pic_url_hd']:
                if key in node and node[key]:
                    url = str(node[key])
                    if url and not url.startswith('http'):
                        url = 'https:' + url if url.startswith('//') else 'https://' + url
                    urls[key] = url
                    
        logger.debug(f"Extracted profile pic URLs: {urls}")
                
    except Exception as e:
        logger.debug(f"Error extracting profile pic URLs: {e}")
    
    # Ensure fallback values
    if not urls.get('profile_pic_url'):
        urls['profile_pic_url'] = ''
    if not urls.get('profile_pic_url_hd'):
        urls['profile_pic_url_hd'] = urls.get('profile_pic_url', '')
    
    return urls

def try_authenticated_method(username: str) -> dict | None:
    """Try authenticated Instagram access"""
    try:
        session_user = os.getenv("INSTAGRAM_SESSION_USERNAME")
        session_pass = os.getenv("INSTAGRAM_SESSION_PASSWORD")
        if not session_user or not session_pass:
            logger.info("No session credentials found, skipping authenticated method")
            return None

        logger.info("Attempting authenticated Instagram access...")
        L = Instaloader(quiet=True, download_videos=False, download_comments=False, save_metadata=False)
        L.context.user_agent = get_random_user_agent()
        
        try:
            L.load_session_from_file(session_user)
            logger.info("Loaded existing session")
        except FileNotFoundError:
            logger.info("Logging in with credentials...")
            L.login(session_user, session_pass)
            if os.getenv("CI") != "true":
                L.save_session_to_file()
                logger.info("New session created and saved locally")

        profile = Profile.from_username(L.context, username)
        pic_urls = get_enhanced_profile_pic_urls(profile)

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
            "profile_object": profile  # Pass the profile object for friends list access
        }

        # Optional enrichment
        try:
            data["external_url"] = getattr(profile, "external_url", None)
        except Exception:
            pass

        return data
    except Exception as e:
        logger.warning(f"Authenticated method failed: {e}")
        return None

def try_anonymous_method(username: str) -> dict | None:
    """Try anonymous Instagram access"""
    try:
        logger.info("Attempting anonymous Instagram access...")
        L = Instaloader(quiet=True, download_videos=False, download_comments=False, save_metadata=False)
        L.context.user_agent = get_random_user_agent()
        
        profile = Profile.from_username(L.context, username)
        pic_urls = get_enhanced_profile_pic_urls(profile)
        
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
            "profile_object": profile  # Pass the profile object
        }
        
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

def try_web_scraping_method(username: str) -> dict | None:
    """Enhanced web scraping method with better error handling"""
    try:
        logger.info("Trying enhanced web scraping method...")
        session = requests.Session()
        session.headers.update({
            "User-Agent": get_random_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        })
        
        retries = Retry(total=5, backoff_factor=2.0, status_forcelist=(429, 500, 502, 503, 504))
        session.mount("https://", HTTPAdapter(max_retries=retries))

        time.sleep(random.uniform(3, 8))
        url = f"https://www.instagram.com/{username}/"
        resp = session.get(url, timeout=20)

        if resp.status_code == 404:
            raise ProfileNotExistsException(f"Profile {username} does not exist")
        resp.raise_for_status()
        html = resp.text

        # Extract data using regex patterns
        patterns = {
            "followers": r'"edge_followed_by":{"count":(\d+)}',
            "following": r'"edge_follow":{"count":(\d+)}',
            "posts": r'"edge_owner_to_timeline_media":{"count":(\d+)}',
            "full_name": r'"full_name":"([^"]*)"',
            "bio": r'"biography":"([^"]*)"',
            "is_private": r'"is_private":(true|false)',
            "is_verified": r'"is_verified":(true|false)',
            "profile_pic_url": r'"profile_pic_url":"([^"]*)"',
            "profile_pic_url_hd": r'"profile_pic_url_hd":"([^"]*)"'
        }
        
        data = {
            "username": username,
            "full_name": username,
            "followers": 0,
            "following": 0,
            "posts": 0,
            "bio": "",
            "is_private": False,
            "is_verified": False,
            "profile_pic_url": "",
            "profile_pic_url_hd": "",
            "method": "web_scraping",
            "profile_object": None  # No profile object available for web scraping
        }
        
        # Extract using patterns
        for field, pattern in patterns.items():
            match = re.search(pattern, html)
            if match:
                value = match.group(1)
                if field in ["followers", "following", "posts"]:
                    data[field] = int(value)
                elif field in ["is_private", "is_verified"]:
                    data[field] = value == "true"
                elif field in ["profile_pic_url", "profile_pic_url_hd"]:
                    value = value.replace('\\/', '/').replace('\\u0026', '&')
                    if value and not value.startswith('http'):
                        value = 'https:' + value if value.startswith('//') else 'https://' + value
                    data[field] = value
                else:
                    data[field] = value.replace('\\n', '\n').replace('\\"', '"')

        return data
        
    except Exception as e:
        logger.warning(f"Enhanced web scraping method failed: {e}")
        return None

# ---------- Main Enhanced Function ----------

def fetch_enhanced_profile_data(target_user: str, output_dir: str = "./", history_keep: int = 100, show_friends: bool = False) -> bool:
    """Enhanced profile data fetching with change detection, notifications and friends list"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    summary_file = output_path / "monitoring_summary.json"
    history_file = output_path / "monitoring_history.json"
    stats_file = output_path / "quick_stats.json"
    changes_file = output_path / "changes_log.json"

    # Load historical data
    historical_summary = {}
    if summary_file.exists():
        try:
            with open(summary_file, "r", encoding="utf-8") as f:
                historical_summary = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load historical data: {e}")

    history_data = {"entries": [], "username": target_user}
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history_data = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load history data: {e}")

    logger.info(f"Fetching enhanced data for: {target_user}")

    # Try different methods to get profile data
    profile_data = (
        try_authenticated_method(target_user)
        or try_anonymous_method(target_user)
        or try_web_scraping_method(target_user)
        or {
            "username": target_user,
            "full_name": target_user,
            "followers": 0,
            "following": 0,
            "posts": 0,
            "bio": "",
            "is_private": True,
            "is_verified": False,
            "profile_pic_url": "",
            "profile_pic_url_hd": "",
            "method": "fallback",
            "error": "Unable to access profile data",
            "profile_object": None
        }
    )

    now_iso = datetime.now(timezone.utc).isoformat()
    current_data = {
        **profile_data,
        "timestamp": now_iso,
        "profile_url": f"https://instagram.com/{target_user}",
        "data_collection_method": profile_data.get("method", "unknown"),
    }

    # Remove profile_object from data before saving (not JSON serializable)
    profile_object = current_data.pop("profile_object", None)

    # Detect changes
    changes = detect_changes(current_data, historical_summary)
    current_data["changes"] = changes

    # Handle profile picture changes
    if DETECT_PROFILE_CHANGES:
        pic_url = current_data.get("profile_pic_url_hd") or current_data.get("profile_pic_url")
        pic_result = detect_profile_picture_changes(target_user, pic_url, output_path)
        if pic_result.get("changed"):
            changes["changes_detected"].append(pic_result["message"])
            changes["has_changes"] = True
            logger.info(pic_result["message"])

    # Handle friends list functionality
    if SHOW_FRIENDS_LIST and profile_object and not current_data.get("is_private", False):
        logger.info("Processing friends list...")
        
        # Load previous friends data
        previous_followers, previous_followings = load_previous_friends_data(target_user, output_path)
        
        # Get current friends data
        current_followers = get_followers_list(profile_object) if TRACK_FOLLOWERS else []
        current_followings = get_followings_list(profile_object) if TRACK_FOLLOWINGS else []
        
        # Save current friends data
        if current_followers or current_followings:
            save_friends_data(target_user, current_followers, current_followings, output_path)
            
            # Analyze changes
            if previous_followers or previous_followings:
                friend_changes = analyze_friend_changes(
                    current_followers, previous_followers,
                    current_followings, previous_followings
                )
                
                # Log significant changes
                if friend_changes["new_followers"]:
                    changes["changes_detected"].append(f"New followers: {len(friend_changes['new_followers'])}")
                    changes["has_changes"] = True
                    
                if friend_changes["lost_followers"]:
                    changes["changes_detected"].append(f"Lost followers: {len(friend_changes['lost_followers'])}")
                    changes["has_changes"] = True
                    
                if friend_changes["new_followings"]:
                    changes["changes_detected"].append(f"New followings: {len(friend_changes['new_followings'])}")
                    changes["has_changes"] = True
                    
                if friend_changes["unfollowed"]:
                    changes["changes_detected"].append(f"Unfollowed: {len(friend_changes['unfollowed'])}")
                    changes["has_changes"] = True
                
                # Save friend changes to changes log
                if changes["has_changes"]:
                    friend_changes_file = output_path / "friend_changes_log.json"
                    friend_changes_data = {"entries": []}
                    
                    if friend_changes_file.exists():
                        try:
                            with open(friend_changes_file, "r", encoding="utf-8") as f:
                                friend_changes_data = json.load(f)
                        except Exception:
                            pass
                    
                    friend_changes_data["entries"].append(friend_changes)
                    friend_changes_data["entries"] = friend_changes_data["entries"][-50:]  # Keep last 50
                    write_json_atomic(friend_changes_file, friend_changes_data)
            
            # Display friends analysis if requested
            if show_friends:
                display_friends_analysis(target_user, output_path)

    # Save all data files
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
        "full_name": current_data.get("full_name", target_user),
        "bio": current_data.get("bio", "")
    }
    
    write_json_atomic(stats_file, quick_stats)
    write_json_atomic(summary_file, current_data)

    # Update history
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

    # Save changes log
    if changes["has_changes"]:
        changes_data = {"entries": []}
        if changes_file.exists():
            try:
                with open(changes_file, "r", encoding="utf-8") as f:
                    changes_data = json.load(f)
            except Exception:
                pass
        
        changes_data["entries"].append(changes)
        changes_data["entries"] = changes_data["entries"][-50:]  # Keep last 50 changes
        write_json_atomic(changes_file, changes_data)

    # Send notifications if configured
    if ENABLE_EMAIL_NOTIFICATIONS and changes["has_changes"]:
        subject = f"Instagram Changes for @{target_user}"
        body = f"Changes detected for @{target_user}:\n\n"
        body += "\n".join(f"• {change}" for change in changes["changes_detected"])
        body += f"\n\nTimestamp: {now_iso}"
        
        html_body = f"<h2>Changes detected for @{target_user}</h2><ul>"
        html_body += "".join(f"<li>{change}</li>" for change in changes["changes_detected"])
        html_body += f"</ul><p>Timestamp: {now_iso}</p>"
        
        send_email_notification(subject, body, html_body)

    # Logging
    logger.info("✅ Enhanced data collection completed successfully")
    logger.info(f"   Method used: {current_data['data_collection_method']}")
    logger.info(f"   Profile: @{current_data['username']} ({current_data['full_name']})")
    logger.info(f"   Followers: {current_data['followers']:,}")
    logger.info(f"   Following: {current_data['following']:,}")
    logger.info(f"   Posts: {current_data['posts']:,}")
    logger.info(f"   Private: {current_data['is_private']}")
    logger.info(f"   Verified: {current_data['is_verified']}")
    
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

# ---------- Friends List CLI Commands ----------

def show_friends_list_command(target_user: str, output_dir: str = "./") -> bool:
    """Command to show friends list analysis"""
    output_path = Path(output_dir)
    
    # Check if friends data exists
    friends_file = output_path / f"{target_user}_friends_analysis.json"
    if not friends_file.exists():
        logger.error(f"No friends data found for {target_user}. Run monitor first with --friends option.")
        return False
    
    display_friends_analysis(target_user, output_path)
    return True

def export_friends_list(target_user: str, output_dir: str = "./", format_type: str = "json") -> bool:
    """Export friends list in different formats"""
    output_path = Path(output_dir)
    friends_file = output_path / f"{target_user}_friends_analysis.json"
    
    if not friends_file.exists():
        logger.error(f"No friends data found for {target_user}")
        return False
    
    try:
        with open(friends_file, 'r', encoding="utf-8") as f:
            data = json.load(f)
        
        if format_type.lower() == "csv":
            import csv
            csv_file = output_path / f"{target_user}_friends_export.csv"
            
            with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Username', 'Category', 'Profile_URL'])
                
                # Write mutual friends
                for friend in data.get("mutual_friends", []):
                    writer.writerow([friend, 'Mutual Friend', f'https://instagram.com/{friend}'])
                
                # Write followers only
                for follower in data.get("followers_only", []):
                    writer.writerow([follower, 'Follower Only', f'https://instagram.com/{follower}'])
                
                # Write followings only
                for following in data.get("followings_only", []):
                    writer.writerow([following, 'Following Only', f'https://instagram.com/{following}'])
            
            logger.info(f"Friends list exported to CSV: {csv_file}")
            
        elif format_type.lower() == "txt":
            txt_file = output_path / f"{target_user}_friends_export.txt"
            
            with open(txt_file, 'w', encoding='utf-8') as txtfile:
                txtfile.write(f"FRIENDS LIST FOR @{target_user}\n")
                txtfile.write("="*50 + "\n\n")
                
                stats = data.get("stats", {})
                txtfile.write(f"STATISTICS:\n")
                txtfile.write(f"Followers: {stats.get('followers_count', 0):,}\n")
                txtfile.write(f"Following: {stats.get('followings_count', 0):,}\n")
                txtfile.write(f"Mutual Friends: {stats.get('mutual_friends_count', 0):,}\n\n")
                
                txtfile.write(f"MUTUAL FRIENDS ({len(data.get('mutual_friends', []))}):\n")
                for friend in data.get("mutual_friends", []):
                    txtfile.write(f"@{friend}\n")
                
                txtfile.write(f"\nFOLLOWERS ONLY ({len(data.get('followers_only', []))}):\n")
                for follower in data.get("followers_only", []):
                    txtfile.write(f"@{follower}\n")
                
                txtfile.write(f"\nFOLLOWING ONLY ({len(data.get('followings_only', []))}):\n")
                for following in data.get("followings_only", []):
                    txtfile.write(f"@{following}\n")
            
            logger.info(f"Friends list exported to TXT: {txt_file}")
        
        else:  # JSON format
            json_file = output_path / f"{target_user}_friends_export.json"
            write_json_atomic(json_file, data)
            logger.info(f"Friends list exported to JSON: {json_file}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to export friends list: {e}")
        return False

def compare_friends_over_time(target_user: str, output_dir: str = "./") -> bool:
    """Compare friends changes over time"""
    output_path = Path(output_dir)
    changes_file = output_path / "friend_changes_log.json"
    
    if not changes_file.exists():
        logger.error(f"No friend changes data found for {target_user}")
        return False
    
    try:
        with open(changes_file, 'r', encoding="utf-8") as f:
            data = json.load(f)
        
        entries = data.get("entries", [])
        if not entries:
            logger.info("No friend changes recorded yet")
            return True
        
        print("\n" + "="*60)
        print(f"FRIENDS CHANGES TIMELINE FOR @{target_user}")
        print("="*60)
        
        for i, entry in enumerate(reversed(entries[-10:]), 1):  # Show last 10 changes
            timestamp = entry.get("timestamp", "Unknown")
            date_str = timestamp.split("T")[0] if "T" in timestamp else timestamp
            
            print(f"\n{i:2d}. {date_str}")
            print("-" * 30)
            
            if entry.get("new_followers"):
                print(f"   📈 New Followers ({len(entry['new_followers'])}): {', '.join(entry['new_followers'][:5])}")
                if len(entry['new_followers']) > 5:
                    print(f"      ... and {len(entry['new_followers']) - 5} more")
            
            if entry.get("lost_followers"):
                print(f"   📉 Lost Followers ({len(entry['lost_followers'])}): {', '.join(entry['lost_followers'][:5])}")
                if len(entry['lost_followers']) > 5:
                    print(f"      ... and {len(entry['lost_followers']) - 5} more")
            
            if entry.get("new_followings"):
                print(f"   ➕ New Followings ({len(entry['new_followings'])}): {', '.join(entry['new_followings'][:5])}")
                if len(entry['new_followings']) > 5:
                    print(f"      ... and {len(entry['new_followings']) - 5} more")
            
            if entry.get("unfollowed"):
                print(f"   ➖ Unfollowed ({len(entry['unfollowed'])}): {', '.join(entry['unfollowed'][:5])}")
                if len(entry['unfollowed']) > 5:
                    print(f"      ... and {len(entry['unfollowed']) - 5} more")
        
        print("="*60)
        return True
        
    except Exception as e:
        logger.error(f"Failed to compare friends over time: {e}")
        return False

# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Instagram Monitor with Friends List functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic monitoring
  python monitor.py --target-user username
  
  # Monitor with friends list
  python monitor.py --target-user username --friends
  
  # Show existing friends analysis
  python monitor.py --target-user username --show-friends
  
  # Export friends list
  python monitor.py --target-user username --export-friends csv
  
  # Compare friends changes over time
  python monitor.py --target-user username --friends-timeline
        """
    )
    
    parser.add_argument("--target-user", required=True, help="Instagram username to monitor")
    parser.add_argument("--output-dir", default="./", help="Output directory for data files")
    parser.add_argument("--history-keep", type=int, default=100, help="Number of history entries to retain")
    
    # Email settings
    parser.add_argument("--enable-email", action="store_true", help="Enable email notifications")
    parser.add_argument("--disable-profile-pics", action="store_true", help="Disable profile picture detection")
    
    # Friends list options
    parser.add_argument("--friends", action="store_true", help="Enable friends list tracking and analysis")
    parser.add_argument("--show-friends", action="store_true", help="Show friends list analysis (no monitoring)")
    parser.add_argument("--export-friends", choices=["json", "csv", "txt"], help="Export friends list in specified format")
    parser.add_argument("--friends-timeline", action="store_true", help="Show friends changes over time")
    parser.add_argument("--disable-followers", action="store_true", help="Disable follower tracking (for friends list)")
    parser.add_argument("--disable-followings", action="store_true", help="Disable following tracking (for friends list)")
    
    args = parser.parse_args()

    global ENABLE_EMAIL_NOTIFICATIONS, SAVE_PROFILE_PICTURES, TRACK_FOLLOWERS, TRACK_FOLLOWINGS, SHOW_FRIENDS_LIST
    
    if args.enable_email:
        ENABLE_EMAIL_NOTIFICATIONS = True
    
    if args.disable_profile_pics:
        SAVE_PROFILE_PICTURES = False
    
    if args.disable_followers:
        TRACK_FOLLOWERS = False
        
    if args.disable_followings:
        TRACK_FOLLOWINGS = False
    
    if args.friends:
        SHOW_FRIENDS_LIST = True

    user = args.target_user.replace("@", "").strip()
    if not user:
        logger.error("Invalid username provided")
        sys.exit(1)

    # Handle specific commands
    if args.show_friends:
        logger.info(f"Showing friends list analysis for: {user}")
        success = show_friends_list_command(user, args.output_dir)
        sys.exit(0 if success else 1)
    
    if args.export_friends:
        logger.info(f"Exporting friends list for: {user} (format: {args.export_friends})")
        success = export_friends_list(user, args.output_dir, args.export_friends)
        sys.exit(0 if success else 1)
    
    if args.friends_timeline:
        logger.info(f"Showing friends timeline for: {user}")
        success = compare_friends_over_time(user, args.output_dir)
        sys.exit(0 if success else 1)

    # Main monitoring
    logger.info(f"Starting enhanced Instagram monitoring for: {user}")
    logger.info(f"Output directory: {Path(args.output_dir).absolute()}")
    logger.info(f"Email notifications: {ENABLE_EMAIL_NOTIFICATIONS}")
    logger.info(f"Profile picture detection: {SAVE_PROFILE_PICTURES}")
    logger.info(f"Friends list tracking: {SHOW_FRIENDS_LIST}")
    logger.info(f"Follower tracking: {TRACK_FOLLOWERS}")
    logger.info(f"Following tracking: {TRACK_FOLLOWINGS}")

    try:
        success = fetch_enhanced_profile_data(
            user, 
            args.output_dir, 
            args.history_keep, 
            show_friends=args.friends
        )
        if not success:
            logger.error("❌ Enhanced Instagram monitoring failed")
            sys.exit(1)
        logger.info("🎉 Enhanced Instagram monitoring completed successfully!")
    except KeyboardInterrupt:
        logger.info("❌ Monitoring cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
