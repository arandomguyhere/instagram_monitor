#!/usr/bin/env python3
"""
Instagram Monitor - GitHub Actions Edition (Authentication Aware)
Handles Instagram's authentication requirements with multiple fallback methods
"""
import json
import os
import sys
import logging
import argparse
import time
import random
import requests
from datetime import datetime, timezone
from pathlib import Path

try:
    from instaloader import Instaloader, Profile, ConnectionException
    from instaloader.exceptions import LoginRequiredException, ProfileNotExistsException
except ImportError:
    print("Error: instaloader not found. Install with: pip install instaloader")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_random_user_agent():
    """Get a random user agent to avoid detection"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def load_historical_data(filepath):
    """Load previous monitoring data if it exists"""
    if Path(filepath).exists():
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load historical data: {e}")
    return {}

def detect_changes(current, historical):
    """Detect changes between current and historical data"""
    changes = {
        'has_changes': False,
        'changes_detected': [],
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    if not historical:
        changes['changes_detected'].append("First time monitoring this user")
        changes['has_changes'] = True
        return changes
    
    # Check for changes
    if current['followers'] != historical.get('followers', 0):
        old_val = historical.get('followers', 0)
        new_val = current['followers']
        diff = new_val - old_val
        changes['changes_detected'].append(f"Followers: {old_val:,} → {new_val:,} ({diff:+,})")
        changes['has_changes'] = True
        
    if current['following'] != historical.get('following', 0):
        old_val = historical.get('following', 0)
        new_val = current['following']
        diff = new_val - old_val
        changes['changes_detected'].append(f"Following: {old_val:,} → {new_val:,} ({diff:+,})")
        changes['has_changes'] = True
        
    if current['posts'] != historical.get('posts', 0):
        old_val = historical.get('posts', 0)
        new_val = current['posts']
        diff = new_val - old_val
        changes['changes_detected'].append(f"Posts: {old_val:,} → {new_val:,} ({diff:+,})")
        changes['has_changes'] = True
        
    if current['bio'] != historical.get('bio', ''):
        changes['changes_detected'].append("Bio updated")
        changes['has_changes'] = True
        
    if current['full_name'] != historical.get('full_name', ''):
        changes['changes_detected'].append("Display name changed")
        changes['has_changes'] = True
        
    if current['is_private'] != historical.get('is_private', False):
        status = "private" if current['is_private'] else "public"
        changes['changes_detected'].append(f"Account is now {status}")
        changes['has_changes'] = True
    
    return changes

def try_web_scraping_method(username):
    """Fallback method using web scraping when API fails"""
    try:
        logger.info("Trying web scraping fallback method...")
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add random delay to avoid rate limiting
        time.sleep(random.uniform(1, 3))
        
        url = f"https://www.instagram.com/{username}/"
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code == 404:
            raise ProfileNotExistsException(f"Profile {username} does not exist")
        
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        
        html_content = response.text
        
        # Extract data from HTML using regex patterns
        import re
        
        # Try to find JSON data in the HTML
        patterns = [
            r'"edge_followed_by":{"count":(\d+)}',
            r'"edge_follow":{"count":(\d+)}',
            r'"edge_owner_to_timeline_media":{"count":(\d+)}',
            r'"full_name":"([^"]*)"',
            r'"biography":"([^"]*)"',
            r'"is_private":(true|false)',
            r'"is_verified":(true|false)',
            r'"profile_pic_url":"([^"]*)"'
        ]
        
        followers_match = re.search(patterns[0], html_content)
        following_match = re.search(patterns[1], html_content)
        posts_match = re.search(patterns[2], html_content)
        name_match = re.search(patterns[3], html_content)
        bio_match = re.search(patterns[4], html_content)
        private_match = re.search(patterns[5], html_content)
        verified_match = re.search(patterns[6], html_content)
        pic_match = re.search(patterns[7], html_content)
        
        # Build profile data from extracted information
        profile_data = {
            'username': username,
            'full_name': name_match.group(1) if name_match else username,
            'followers': int(followers_match.group(1)) if followers_match else 0,
            'following': int(following_match.group(1)) if following_match else 0,
            'posts': int(posts_match.group(1)) if posts_match else 0,
            'bio': bio_match.group(1).replace('\\n', '\n') if bio_match else '',
            'is_private': private_match.group(1) == 'true' if private_match else False,
            'is_verified': verified_match.group(1) == 'true' if verified_match else False,
            'profile_pic_url': pic_match.group(1) if pic_match else '',
            'method': 'web_scraping'
        }
        
        logger.info("✅ Web scraping method successful")
        return profile_data
        
    except Exception as e:
        logger.warning(f"Web scraping method failed: {e}")
        return None

def try_instaloader_with_session(username):
    """Try to use Instaloader with session credentials if available"""
    try:
        # Check for session credentials in environment variables
        session_user = os.getenv('INSTAGRAM_SESSION_USERNAME')
        session_pass = os.getenv('INSTAGRAM_SESSION_PASSWORD')
        
        if not session_user or not session_pass:
            logger.info("No session credentials found, skipping authenticated method")
            return None
            
        logger.info("Attempting authenticated Instagram access...")
        
        L = Instaloader(
            quiet=True,
            user_agent=get_random_user_agent(),
            download_videos=False,
            download_comments=False,
            save_metadata=False
        )
        
        # Try to load existing session or login
        try:
            L.load_session_from_file(session_user)
            logger.info("Loaded existing session")
        except FileNotFoundError:
            logger.info("Logging in with credentials...")
            L.login(session_user, session_pass)
            L.save_session_to_file()
            logger.info("New session created")
        
        # Get profile with authentication
        profile = Profile.from_username(L.context, username)
        
        profile_data = {
            'username': profile.username,
            'full_name': profile.full_name or profile.username,
            'followers': profile.followers,
            'following': profile.followees,
            'posts': profile.mediacount,
            'bio': profile.biography or '',
            'is_private': profile.is_private,
            'is_verified': getattr(profile, 'is_verified', False),
            'profile_pic_url': profile.profile_pic_url,
            'method': 'authenticated_api'
        }
        
        logger.info("✅ Authenticated method successful")
        return profile_data
        
    except Exception as e:
        logger.warning(f"Authenticated method failed: {e}")
        return None

def try_instaloader_anonymous(username):
    """Try basic Instaloader without authentication"""
    try:
        logger.info("Attempting anonymous Instagram access...")
        
        L = Instaloader(
            quiet=True,
            user_agent=get_random_user_agent(),
            download_videos=False,
            download_comments=False,
            save_metadata=False
        )
        
        profile = Profile.from_username(L.context, username)
        
        profile_data = {
            'username': profile.username,
            'full_name': profile.full_name or profile.username,
            'followers': profile.followers,
            'following': profile.followees,
            'posts': profile.mediacount,
            'bio': profile.biography or '',
            'is_private': profile.is_private,
            'is_verified': getattr(profile, 'is_verified', False),
            'profile_pic_url': profile.profile_pic_url,
            'method': 'anonymous_api'
        }
        
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

def create_fallback_data(username):
    """Create basic profile data when all methods fail"""
    logger.info("Creating fallback data structure...")
    
    return {
        'username': username,
        'full_name': username,
        'followers': 0,
        'following': 0,
        'posts': 0,
        'bio': '',
        'is_private': True,  # Assume private if we can't access
        'is_verified': False,
        'profile_pic_url': '',
        'method': 'fallback',
        'error': 'Unable to access profile data - may be private or restricted'
    }

def fetch_profile_data(target_user, output_dir="./"):
    """Fetch Instagram profile data using multiple methods with fallbacks"""
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    summary_file = output_path / "monitoring_summary.json"
    
    # Load historical data for change detection
    historical_data = load_historical_data(summary_file)
    
    logger.info(f"Fetching data for: {target_user}")
    
    # Try multiple methods in order of preference
    profile_data = None
    
    # Method 1: Try with session authentication
    profile_data = try_instaloader_with_session(target_user)
    
    # Method 2: Try anonymous Instaloader
    if not profile_data:
        profile_data = try_instaloader_anonymous(target_user)
    
    # Method 3: Try web scraping
    if not profile_data:
        profile_data = try_web_scraping_method(target_user)
    
    # Method 4: Create fallback data
    if not profile_data:
        logger.warning("All data collection methods failed, using fallback data")
        profile_data = create_fallback_data(target_user)
    
    # Add metadata to the profile data
    current_data = {
        **profile_data,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'profile_url': f"https://instagram.com/{target_user}",
        'external_url': None,
        'has_stories': False,
        'story_count': 0,
        'monitoring_session': profile_data.get('method') == 'authenticated_api',
        'last_post_date': None,
        'engagement_rate': 0.0,
        'data_collection_method': profile_data.get('method', 'unknown')
    }
    
    # Detect changes
    changes = detect_changes(current_data, historical_data)
    current_data["changes"] = changes
    
    # Save main monitoring summary
    with open(summary_file, "w", encoding='utf-8') as f:
        json.dump(current_data, f, indent=2, ensure_ascii=False)
        
    # Save historical tracking
    history_file = output_path / "monitoring_history.json"
    history_data = load_historical_data(history_file)
    
    if "entries" not in history_data:
        history_data["entries"] = []
        history_data["username"] = target_user
        
    # Add current entry to history
    history_entry = {
        "timestamp": current_data["timestamp"],
        "followers": current_data["followers"],
        "following": current_data["following"],
        "posts": current_data["posts"],
        "is_private": current_data["is_private"],
        "method": current_data["data_collection_method"]
    }
    
    history_data["entries"].append(history_entry)
    history_data["entries"] = history_data["entries"][-100:]  # Keep last 100
    history_data["last_updated"] = current_data["timestamp"]
    
    with open(history_file, "w", encoding='utf-8') as f:
        json.dump(history_data, f, indent=2, ensure_ascii=False)
    
    # Create quick stats
    stats_file = output_path / "quick_stats.json"
    quick_stats = {
        "username": current_data["username"],
        "followers": current_data["followers"],
        "following": current_data["following"],
        "posts": current_data["posts"],
        "last_updated": current_data["timestamp"],
        "is_private": current_data["is_private"],
        "is_verified": current_data["is_verified"],
        "method": current_data["data_collection_method"]
    }
    
    with open(stats_file, "w", encoding='utf-8') as f:
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
    
    if 'error' in current_data:
        logger.warning(f"   Note: {current_data['error']}")
    
    if changes['has_changes']:
        logger.info(f"   Changes detected: {len(changes['changes_detected'])}")
        for change in changes['changes_detected']:
            logger.info(f"     • {change}")
    else:
        logger.info("   No changes detected since last run")
        
    # List generated files
    logger.info("   Generated files:")
    for file in output_path.glob("*.json"):
        logger.info(f"     • {file.name}")
        
    return True

def main():
    parser = argparse.ArgumentParser(
        description="Monitor Instagram profile stats with multiple fallback methods",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py --target-user dominance.information
  python monitor.py --target-user cristiano --output-dir ./data

Environment Variables:
  INSTAGRAM_SESSION_USERNAME - Instagram username for authenticated access
  INSTAGRAM_SESSION_PASSWORD - Instagram password for authenticated access
        """
    )
    
    parser.add_argument(
        "--target-user", 
        required=True, 
        help="Instagram username to monitor"
    )
    
    parser.add_argument(
        "--output-dir", 
        default="./", 
        help="Output directory for data files (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Clean username (remove @ if present)
    clean_username = args.target_user.replace('@', '').strip()
    
    if not clean_username:
        logger.error("Invalid username provided")
        sys.exit(1)
    
    logger.info(f"Starting Instagram monitoring for: {clean_username}")
    logger.info(f"Output directory: {Path(args.output_dir).absolute()}")
    
    # Check for authentication credentials
    if os.getenv('INSTAGRAM_SESSION_USERNAME'):
        logger.info("Authentication credentials found - will attempt authenticated access")
    else:
        logger.info("No authentication credentials - will use anonymous/fallback methods")
    
    try:
        success = fetch_profile_data(clean_username, args.output_dir)
        
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
