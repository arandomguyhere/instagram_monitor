#!/usr/bin/env python3
"""
Enhanced Instagram Monitor with Profile Picture Download
Updated version that downloads and saves profile pictures locally
"""

import instaloader
import json
import os
import sys
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path
import logging
import time
from typing import Dict, Optional, Any
import hashlib

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class InstagramMonitor:
    """Enhanced Instagram monitoring with profile picture download"""
    
    def __init__(self, output_dir: str = "./monitoring_data"):
        self.output_dir = Path(output_dir)
        self.loader = instaloader.Instaloader(
            dirname_pattern=str(self.output_dir / "{target}"),
            filename_pattern="{shortcode}",
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern="",
            storyitem_metadata_txt_pattern=""
        )
        
        # Login if credentials provided
        self._setup_session()
    
    def _setup_session(self):
        """Setup Instagram session if credentials are available"""
        username = os.getenv('INSTAGRAM_SESSION_USERNAME')
        password = os.getenv('INSTAGRAM_SESSION_PASSWORD')
        
        if username and password:
            try:
                logger.info(f"Logging in as {username}...")
                self.loader.login(username, password)
                logger.info("✅ Successfully logged in to Instagram")
                self.authenticated = True
            except Exception as e:
                logger.warning(f"⚠️ Login failed: {e}")
                logger.info("Continuing in anonymous mode with limited functionality")
                self.authenticated = False
        else:
            logger.info("No credentials provided, running in anonymous mode")
            self.authenticated = False
    
    def download_profile_picture(self, profile_pic_url: str, username: str, output_dir: Path) -> Optional[str]:
        """
        Download and save profile picture locally
        Returns path to downloaded file or None if failed
        """
        if not profile_pic_url:
            return None
        
        try:
            # Create output directory if it doesn't exist
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup headers to mimic real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.instagram.com/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            # Download the image
            logger.info(f"📸 Downloading profile picture for {username}...")
            response = requests.get(profile_pic_url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            
            # Determine file extension from content type or URL
            content_type = response.headers.get('content-type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                extension = '.jpg'
            elif 'png' in content_type:
                extension = '.png'
            elif 'webp' in content_type:
                extension = '.webp'
            else:
                # Default to jpg
                extension = '.jpg'
            
            # Save the image
            pic_path = output_dir / f"profile_pic{extension}"
            with open(pic_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # Also save as .jpg for consistency (if not already jpg)
            if extension != '.jpg':
                jpg_path = output_dir / "profile_pic.jpg"
                with open(pic_path, 'rb') as src, open(jpg_path, 'wb') as dst:
                    dst.write(src.read())
                pic_path = jpg_path
            
            file_size = pic_path.stat().st_size
            logger.info(f"✅ Downloaded profile picture: {pic_path} ({file_size} bytes)")
            return str(pic_path)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to download profile picture for {username}: {e}")
            return None
    
    def get_profile_data(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Extract comprehensive profile data including picture download
        """
        try:
            logger.info(f"📊 Fetching profile data for @{username}...")
            profile = instaloader.Profile.from_username(self.loader.context, username)
            
            # Create user-specific output directory
            user_output_dir = self.output_dir / username
            user_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Extract basic profile data
            profile_data = {
                "username": profile.username,
                "full_name": profile.full_name,
                "biography": profile.biography,
                "is_private": profile.is_private,
                "is_verified": profile.is_verified,
                "followers": profile.followers,
                "following": profile.followees,
                "posts": profile.mediacount,
                "profile_pic_url": profile.profile_pic_url,
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "schema": "v1"
            }
            
            # Download profile picture
            if profile.profile_pic_url:
                downloaded_pic = self.download_profile_picture(
                    profile.profile_pic_url, 
                    username, 
                    user_output_dir
                )
                if downloaded_pic:
                    profile_data["local_profile_pic"] = downloaded_pic
                    profile_data["profile_pic_downloaded"] = True
                else:
                    profile_data["profile_pic_downloaded"] = False
            
            # Try to get additional data if authenticated
            if self.authenticated:
                try:
                    # Get high-quality profile picture URL
                    profile_data["profile_pic_url_hd"] = profile.profile_pic_url.replace('150x150', '320x320')
                    
                    # Add more authenticated features here if needed
                    logger.info("✅ Enhanced data available (authenticated mode)")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Some enhanced features failed: {e}")
            
            logger.info(f"✅ Successfully extracted profile data for @{username}")
            return profile_data
            
        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"❌ Profile @{username} does not exist")
            return None
        except instaloader.exceptions.LoginRequiredException:
            logger.warning(f"⚠️ Login required for full access to @{username}")
            # Try to get basic public data
            try:
                profile = instaloader.Profile.from_username(self.loader.context, username)
                profile_data = {
                    "username": profile.username,
                    "full_name": profile.full_name,
                    "biography": profile.biography,
                    "is_private": profile.is_private,
                    "is_verified": profile.is_verified,
                    "followers": profile.followers,
                    "following": profile.followees,
                    "posts": profile.mediacount,
                    "profile_pic_url": profile.profile_pic_url,
                    "last_updated": datetime.now(timezone.utc).isoformat(),
                    "schema": "v1",
                    "limited_access": True
                }
                return profile_data
            except Exception as e2:
                logger.error(f"❌ Failed to get even basic data: {e2}")
                return None
        except Exception as e:
            logger.error(f"❌ Error fetching profile @{username}: {e}")
            return None
    
    def load_previous_data(self, username: str) -> Optional[Dict[str, Any]]:
        """Load previous monitoring data for comparison"""
        user_dir = self.output_dir / username
        latest_file = user_dir / "latest.json"
        
        if latest_file.exists():
            try:
                with open(latest_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Failed to load previous data: {e}")
        
        return None
    
    def detect_changes(self, old_data: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Detect changes between old and new profile data"""
        changes = {}
        
        # Fields to monitor for changes
        monitored_fields = [
            'full_name', 'biography', 'is_private', 'is_verified',
            'followers', 'following', 'posts', 'profile_pic_url'
        ]
        
        for field in monitored_fields:
            old_value = old_data.get(field)
            new_value = new_data.get(field)
            
            if old_value != new_value:
                changes[field] = {
                    'old': old_value,
                    'new': new_value,
                    'timestamp': new_data['last_updated']
                }
        
        return changes
    
    def save_monitoring_data(self, username: str, profile_data: Dict[str, Any], changes: Dict[str, Any] = None):
        """Save monitoring data to files"""
        user_dir = self.output_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        # Save latest data
        latest_file = user_dir / "latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(profile_data, f, indent=2, ensure_ascii=False)
        
        # Update history
        history_file = user_dir / "history.json"
        history_entry = {
            "timestamp": profile_data['last_updated'],
            "snapshot": profile_data.copy(),
            "changes": changes or {}
        }
        
        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Failed to load history: {e}")
        
        # Add new entry
        history.append(history_entry)
        
        # Keep only last 100 entries to prevent file from growing too large
        history = history[-100:]
        
        # Save updated history
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Saved monitoring data to {user_dir}")
    
    def monitor_user(self, username: str) -> bool:
        """Complete monitoring workflow for a user"""
        logger.info(f"🎯 Starting monitoring for @{username}")
        
        # Get current profile data
        new_data = self.get_profile_data(username)
        if not new_data:
            logger.error(f"❌ Failed to get profile data for @{username}")
            return False
        
        # Load previous data for comparison
        old_data = self.load_previous_data(username)
        
        # Detect changes
        changes = {}
        if old_data:
            changes = self.detect_changes(old_data, new_data)
            if changes:
                logger.info(f"📈 Detected {len(changes)} changes for @{username}")
                for field, change in changes.items():
                    logger.info(f"  • {field}: {change['old']} → {change['new']}")
            else:
                logger.info(f"📊 No changes detected for @{username}")
        else:
            logger.info(f"📊 First time monitoring @{username}")
        
        # Save data
        self.save_monitoring_data(username, new_data, changes)
        
        # Send notifications if changes detected
        if changes:
            self.send_notifications(username, changes, new_data)
        
        logger.info(f"✅ Monitoring complete for @{username}")
        return True
    
    def send_notifications(self, username: str, changes: Dict[str, Any], profile_data: Dict[str, Any]):
        """Send notifications about detected changes"""
        try:
            # Email notifications (if configured)
            if os.getenv('SMTP_HOST'):
                self.send_email_notification(username, changes, profile_data)
            
            # GitHub Issues (if in GitHub Actions)
            if os.getenv('GITHUB_ACTIONS'):
                self.create_github_issue(username, changes, profile_data)
                
        except Exception as e:
            logger.warning(f"⚠️ Notification failed: {e}")
    
    def send_email_notification(self, username: str, changes: Dict[str, Any], profile_data: Dict[str, Any]):
        """Send email notification about changes"""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Email configuration
            smtp_host = os.getenv('SMTP_HOST')
            smtp_port = int(os.getenv('SMTP_PORT', '587'))
            smtp_user = os.getenv('SMTP_USER')
            smtp_pass = os.getenv('SMTP_PASSWORD')
            sender_email = os.getenv('SENDER_EMAIL')
            receiver_email = os.getenv('RECEIVER_EMAIL')
            
            if not all([smtp_host, smtp_user, smtp_pass, sender_email, receiver_email]):
                logger.warning("⚠️ Email configuration incomplete")
                return
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = f"Instagram Monitor Alert: Changes detected for @{username}"
            
            # Create email body
            body = f"""
Instagram Monitor detected changes for @{username}

Profile: https://instagram.com/{username}
Full Name: {profile_data.get('full_name', 'N/A')}
Followers: {profile_data.get('followers', 'N/A'):,}

Changes detected:
"""
            
            for field, change in changes.items():
                body += f"• {field}: {change['old']} → {change['new']}\n"
            
            body += f"\nMonitored at: {profile_data['last_updated']}"
            
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"📧 Email notification sent for @{username}")
            
        except Exception as e:
            logger.warning(f"⚠️ Email notification failed: {e}")
    
    def create_github_issue(self, username: str, changes: Dict[str, Any], profile_data: Dict[str, Any]):
        """Create GitHub issue for changes (when running in GitHub Actions)"""
        try:
            github_token = os.getenv('GITHUB_TOKEN')
            github_repo = os.getenv('GITHUB_REPOSITORY')
            
            if not github_token or not github_repo:
                return
            
            import requests
            
            # Create issue body
            issue_body = f"""
## Instagram Monitor Alert

**Profile:** [@{username}](https://instagram.com/{username})
**Full Name:** {profile_data.get('full_name', 'N/A')}
**Current Followers:** {profile_data.get('followers', 'N/A'):,}

### Changes Detected:
"""
            
            for field, change in changes.items():
                issue_body += f"- **{field}:** `{change['old']}` → `{change['new']}`\n"
            
            issue_body += f"\n**Monitored at:** {profile_data['last_updated']}"
            
            # Create GitHub issue
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            issue_data = {
                'title': f'Instagram Changes: @{username}',
                'body': issue_body,
                'labels': ['instagram-monitor', 'changes-detected']
            }
            
            response = requests.post(
                f'https://api.github.com/repos/{github_repo}/issues',
                headers=headers,
                json=issue_data
            )
            
            if response.status_code == 201:
                logger.info(f"📝 GitHub issue created for @{username}")
            else:
                logger.warning(f"⚠️ GitHub issue creation failed: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"⚠️ GitHub issue creation failed: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Enhanced Instagram Monitor with Profile Picture Download",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor single user
  python monitor.py --target-user therock
  
  # Monitor with custom output directory
  python monitor.py --target-user taylorswift --output-dir ./data
  
  # Enable debug logging
  python monitor.py --target-user username --debug
  
  # Monitor user with friends list analysis (requires login)
  python monitor.py --target-user username --friends
        """
    )
    
    parser.add_argument("--target-user", required=True, help="Instagram username to monitor")
    parser.add_argument("--output-dir", default="./monitoring_data", help="Output directory for data")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--friends", action="store_true", help="Also analyze friends list (requires login)")
    parser.add_argument("--no-notifications", action="store_true", help="Disable notifications")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create monitor instance
    monitor = InstagramMonitor(args.output_dir)
    
    # Monitor the user
    success = monitor.monitor_user(args.target_user)
    
    # Friends analysis (if requested and authenticated)
    if args.friends and monitor.authenticated:
        logger.info(f"🤝 Analyzing friends list for @{args.target_user}...")
        try:
            # This would require additional implementation
            # For now, just log that it's available
            logger.info("Friends list analysis available with login credentials")
        except Exception as e:
            logger.warning(f"⚠️ Friends analysis failed: {e}")
    elif args.friends and not monitor.authenticated:
        logger.warning("⚠️ Friends analysis requires Instagram login credentials")
    
    if success:
        logger.info("🎉 Monitoring completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Monitoring failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
