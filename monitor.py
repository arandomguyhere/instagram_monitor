#!/usr/bin/env python3
"""
Instagram Monitor - GitHub Actions Edition
Adapted from misiektoja/instagram_monitor
Version: 2.0-GitHub-Actions
OSINT tool for tracking Instagram user activities via GitHub Actions
Outputs data as JSON for GitHub Pages dashboard consumption
"""
import json
import os
import sys
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from instaloader import Instaloader, Profile, ConnectionException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def fetch_profile_data(target_user, output_dir="./"):
    """Fetch Instagram profile data and save to specified directory"""
    L = Instaloader(quiet=True, download_videos=False, download_comments=False, save_metadata=False)
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    summary_file = output_path / "monitoring_summary.json"
    
    try:
        logger.info(f"Fetching data for: {target_user}")
        
        # Load historical data for change detection
        historical_data = load_historical_data(summary_file)
        
        # Get profile data
        profile = Profile.from_username(L.context, target_user)
        
        # Check for stories (basic check without session)
        has_stories = False
        story_count = 0
        try:
            if hasattr(profile, 'has_public_story'):
                has_stories = profile.has_public_story
                if has_stories:
                    story_count = 1
        except:
            pass
        
        # Build comprehensive profile data
        current_data = {
            "username": profile.username,
            "full_name": profile.full_name or profile.username,
            "followers": profile.followers,
            "following": profile.followees,
            "is_private": profile.is_private,
            "is_verified": getattr(profile, 'is_verified', False),
            "bio": profile.biography or "",
            "posts": profile.mediacount,
            "profile_pic_url": profile.profile_pic_url,
            "external_url": getattr(profile, 'external_url', None),
            "has_stories": has_stories,
            "story_count": story_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "profile_url": f"https://instagram.com/{profile.username}",
            "monitoring_session": False,  # No session login in basic version
            "last_post_date": None,
            "engagement_rate": 0.0  # Would need session for accurate calculation
        }
        
        # Try to get last post date (limited without session)
        try:
            posts = list(profile.get_posts())
            if posts:
                last_post = posts[0]
                current_data["last_post_date"] = last_post.date_utc.isoformat()
                # Basic engagement rate calculation
                if current_data["followers"] > 0:
                    avg_likes = last_post.likes
                    current_data["engagement_rate"] = round((avg_likes / current_data["followers"]) * 100, 2)
        except Exception as e:
            logger.warning(f"Could not fetch posts data: {e}")
        
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
            "engagement_rate": current_data.get("engagement_rate", 0.0)
        }
        
        history_data["entries"].append(history_entry)
        
        # Keep only last 100 entries to prevent file bloat
        history_data["entries"] = history_data["entries"][-100:]
        history_data["last_updated"] = current_data["timestamp"]
        
        with open(history_file, "w", encoding='utf-8') as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
        
        # Create a simple stats summary for quick access
        stats_file = output_path / "quick_stats.json"
        quick_stats = {
            "username": current_data["username"],
            "followers": current_data["followers"],
            "following": current_data["following"],
            "posts": current_data["posts"],
            "last_updated": current_data["timestamp"],
            "is_private": current_data["is_private"],
            "is_verified": current_data["is_verified"]
        }
        
        with open(stats_file, "w", encoding='utf-8') as f:
            json.dump(quick_stats, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ Data collection completed successfully")
        logger.info(f"   Output directory: {output_path.absolute()}")
        logger.info(f"   Profile: @{current_data['username']} ({current_data['full_name']})")
        logger.info(f"   Followers: {current_data['followers']:,}")
        logger.info(f"   Following: {current_data['following']:,}")
        logger.info(f"   Posts: {current_data['posts']:,}")
        logger.info(f"   Private: {current_data['is_private']}")
        logger.info(f"   Verified: {current_data['is_verified']}")
        
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
        
    except ConnectionException as e:
        logger.error(f"Connection error: {e}")
        logger.error("This could be due to rate limiting or network issues")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
    return False

def main():
    parser = argparse.ArgumentParser(
        description="Monitor Instagram profile stats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py --target-user bob
  python monitor.py --target-user cristiano --output-dir ./data
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
    
    success = fetch_profile_data(clean_username, args.output_dir)
    
    if not success:
        logger.error("❌ Instagram monitoring failed")
        sys.exit(1)
        
    logger.info("🎉 Instagram monitoring completed successfully!")

if __name__ == "__main__":
    main()
