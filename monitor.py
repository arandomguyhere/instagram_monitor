#!/usr/bin/env python3
"""
Instagram Monitor - GitHub Actions Edition
Author: Adapted from misiektoja/instagram_monitor
Version: 2.0-GitHub-Actions

OSINT tool for tracking Instagram user activities via GitHub Actions
Outputs data as JSON for GitHub Pages dashboard consumption
"""

import json
import os
import sys
import time
import requests
import smtplib
import ssl
from datetime import datetime, timezone
from dateutil import relativedelta
import pytz
import instaloader
from instaloader import ConnectionException, Instaloader
from instaloader.exceptions import PrivateProfileNotFollowedException
import logging
import argparse
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class GitHubInstagramMonitor:
    def __init__(self, target_username: str, session_username: Optional[str] = None, session_password: Optional[str] = None):
        self.target_username = target_username
        self.session_username = session_username
        self.session_password = session_password
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize Instaloader
        self.bot = Instaloader(
            quiet=True,
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            max_connection_attempts=3
        )
        
        self.setup_session()
    
    def setup_session(self) -> None:
        """Setup Instagram session if credentials provided"""
        if self.session_username and self.session_password:
            try:
                # Try to load existing session
                self.bot.load_session_from_file(self.session_username)
                logger.info(f"✅ Loaded existing session for {self.session_username}")
            except FileNotFoundError:
                # Create new session
                logger.info(f"🔐 Creating new session for {self.session_username}")
                self.bot.login(self.session_username, self.session_password)
                self.bot.save_session_to_file()
                logger.info(f"✅ Session created and saved for {self.session_username}")
            except Exception as e:
                logger.warning(f"⚠️ Session setup failed: {e}")
        else:
            logger.info("📱 Running in anonymous mode (limited data available)")
    
    def get_profile_data(self) -> Dict[str, Any]:
        """Fetch current profile data"""
        try:
            logger.info(f"🔍 Fetching profile data for @{self.target_username}")
            profile = instaloader.Profile.from_username(self.bot.context, self.target_username)
            
            data = {
                'username': profile.username,
                'user_id': profile.userid,
                'followers': profile.followers,
                'following': profile.followees,
                'posts_count': profile.mediacount,
                'bio': profile.biography or "",
                'is_private': profile.is_private,
                'is_verified': profile.is_verified,
                'profile_pic_url': profile.profile_pic_url,
                'external_url': profile.external_url or "",
                'full_name': profile.full_name or "",
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            # Get recent posts if account is accessible
            if not profile.is_private or (profile.is_private and hasattr(profile, 'followed_by_viewer') and profile.followed_by_viewer):
                try:
                    posts = list(profile.get_posts())
                    if posts:
                        latest_post = posts[0]
                        data['latest_post'] = {
                            'date': latest_post.date_utc.isoformat(),
                            'likes': latest_post.likes,
                            'comments': latest_post.comments,
                            'caption': (latest_post.caption[:500] + '...') if latest_post.caption and len(latest_post.caption) > 500 else (latest_post.caption or ""),
                            'shortcode': latest_post.shortcode,
                            'url': f"https://instagram.com/p/{latest_post.shortcode}/",
                            'is_video': latest_post.is_video,
                            'typename': latest_post.typename
                        }
                        
                        # Calculate engagement rate
                        if data['followers'] > 0:
                            engagement = ((latest_post.likes + latest_post.comments) / data['followers']) * 100
                            data['latest_post']['engagement_rate'] = round(engagement, 2)
                        
                        logger.info(f"📸 Latest post: {latest_post.likes} likes, {latest_post.comments} comments")
                    
                    # Get additional data if session available
                    if self.bot.context.is_logged_in and not self.is_rate_limited():
                        additional_data = self.get_detailed_data(profile)
                        data.update(additional_data)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not fetch posts: {e}")
            else:
                logger.info("🔒 Profile is private and not followed - limited data available")
            
            logger.info(f"✅ Successfully fetched data for @{self.target_username}")
            return data
            
        except Exception as e:
            logger.error(f"❌ Error fetching profile data: {e}")
            raise
    
    def get_detailed_data(self, profile) -> Dict[str, Any]:
        """Get additional data when logged in"""
        data = {}
        
        try:
            # Get stories count
            if hasattr(profile, 'has_public_story'):
                data['has_story'] = profile.has_public_story
            
            # Get highlight reels count
            try:
                highlights = list(profile.get_highlights())
                data['highlights_count'] = len(highlights)
            except Exception:
                data['highlights_count'] = 0
            
            # Get IGTV count (if available)
            try:
                igtv_posts = list(profile.get_igtv_posts())
                data['igtv_count'] = len(list(igtv_posts))
            except Exception:
                data['igtv_count'] = 0
                
        except Exception as e:
            logger.warning(f"⚠️ Error getting detailed data: {e}")
        
        return data
    
    def is_rate_limited(self) -> bool:
        """Simple rate limiting check"""
        # Add basic rate limiting logic if needed
        return False
    
    def load_history(self) -> List[Dict[str, Any]]:
        """Load historical data"""
        history_file = self.data_dir / f"{self.target_username}_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    logger.info(f"📊 Loaded {len(history)} historical records")
                    return history
            except Exception as e:
                logger.warning(f"⚠️ Could not load history: {e}")
        return []
    
    def save_data(self, current_data: Dict[str, Any]) -> None:
        """Save current data and update history"""
        # Save latest data
        latest_file = self.data_dir / f"{self.target_username}_latest.json"
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, indent=2, ensure_ascii=False)
        
        # Load and update history
        history = self.load_history()
        
        # Add current data to history
        history.append(current_data)
        
        # Keep only last 1000 entries to avoid huge files
        if len(history) > 1000:
            history = history[-1000:]
        
        # Save updated history
        history_file = self.data_dir / f"{self.target_username}_history.json"
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Data saved to {latest_file} and {history_file}")
    
    def detect_changes(self, current_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect changes from last run"""
        changes = []
        
        # Load previous data
        latest_file = self.data_dir / f"{self.target_username}_latest.json"
        if not latest_file.exists():
            changes.append({
                'type': 'initial_tracking',
                'message': f"🎯 Started tracking @{self.target_username}",
                'timestamp': current_data['timestamp']
            })
            return changes
        
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                previous_data = json.load(f)
        except Exception as e:
            logger.warning(f"⚠️ Could not load previous data: {e}")
            return changes
        
        # Check for follower changes
        if current_data['followers'] != previous_data.get('followers', 0):
            diff = current_data['followers'] - previous_data.get('followers', 0)
            emoji = "📈" if diff > 0 else "📉"
            changes.append({
                'type': 'followers_change',
                'message': f"{emoji} Followers: {previous_data.get('followers', 0)} → {current_data['followers']} ({diff:+d})",
                'old_value': previous_data.get('followers', 0),
                'new_value': current_data['followers'],
                'difference': diff,
                'timestamp': current_data['timestamp']
            })
        
        # Check for following changes
        if current_data['following'] != previous_data.get('following', 0):
            diff = current_data['following'] - previous_data.get('following', 0)
            emoji = "📈" if diff > 0 else "📉"
            changes.append({
                'type': 'following_change',
                'message': f"{emoji} Following: {previous_data.get('following', 0)} → {current_data['following']} ({diff:+d})",
                'old_value': previous_data.get('following', 0),
                'new_value': current_data['following'],
                'difference': diff,
                'timestamp': current_data['timestamp']
            })
        
        # Check for posts count changes
        if current_data['posts_count'] != previous_data.get('posts_count', 0):
            diff = current_data['posts_count'] - previous_data.get('posts_count', 0)
            emoji = "📸" if diff > 0 else "🗑️"
            changes.append({
                'type': 'posts_change',
                'message': f"{emoji} Posts: {previous_data.get('posts_count', 0)} → {current_data['posts_count']} ({diff:+d})",
                'old_value': previous_data.get('posts_count', 0),
                'new_value': current_data['posts_count'],
                'difference': diff,
                'timestamp': current_data['timestamp']
            })
        
        # Check for bio changes
        if current_data['bio'] != previous_data.get('bio', ''):
            changes.append({
                'type': 'bio_change',
                'message': f"📝 Bio changed",
                'old_value': previous_data.get('bio', ''),
                'new_value': current_data['bio'],
                'timestamp': current_data['timestamp']
            })
        
        # Check for profile picture changes
        if current_data['profile_pic_url'] != previous_data.get('profile_pic_url', ''):
            changes.append({
                'type': 'profile_pic_change',
                'message': f"🖼️ Profile picture changed",
                'old_value': previous_data.get('profile_pic_url', ''),
                'new_value': current_data['profile_pic_url'],
                'timestamp': current_data['timestamp']
            })
        
        # Check for verification status changes
        if current_data['is_verified'] != previous_data.get('is_verified', False):
            status = "verified" if current_data['is_verified'] else "unverified"
            changes.append({
                'type': 'verification_change',
                'message': f"✅ Account {status}",
                'old_value': previous_data.get('is_verified', False),
                'new_value': current_data['is_verified'],
                'timestamp': current_data['timestamp']
            })
        
        # Check for privacy changes
        if current_data['is_private'] != previous_data.get('is_private', False):
            status = "private" if current_data['is_private'] else "public"
            emoji = "🔒" if current_data['is_private'] else "🌐"
            changes.append({
                'type': 'privacy_change',
                'message': f"{emoji} Account is now {status}",
                'old_value': previous_data.get('is_private', False),
                'new_value': current_data['is_private'],
                'timestamp': current_data['timestamp']
            })
        
        # Check for new posts
        current_post = current_data.get('latest_post')
        previous_post = previous_data.get('latest_post')
        
        if current_post and previous_post:
            if current_post['shortcode'] != previous_post['shortcode']:
                changes.append({
                    'type': 'new_post',
                    'message': f"📷 New post: {current_post['url']}",
                    'post_data': current_post,
                    'timestamp': current_data['timestamp']
                })
        elif current_post and not previous_post:
            changes.append({
                'type': 'new_post',
                'message': f"📷 New post: {current_post['url']}",
                'post_data': current_post,
                'timestamp': current_data['timestamp']
            })
        
        if changes:
            logger.info(f"🔄 Detected {len(changes)} changes")
            for change in changes:
                logger.info(f"  • {change['message']}")
        else:
            logger.info("😴 No changes detected")
        
        return changes
    
    def create_github_issue(self, changes: List[Dict[str, Any]]) -> None:
        """Create GitHub issue for significant changes"""
        if not changes:
            return
        
        github_token = os.getenv('GITHUB_TOKEN')
        github_repo = os.getenv('GITHUB_REPOSITORY')
        
        if not github_token or not github_repo:
            logger.info("ℹ️ GitHub token or repository not configured, skipping issue creation")
            return
        
        # Only create issues for significant changes
        significant_types = ['new_post', 'followers_change', 'bio_change', 'verification_change', 'privacy_change']
        significant_changes = [c for c in changes if c['type'] in significant_types]
        
        if not significant_changes:
            logger.info("ℹ️ No significant changes detected, skipping issue creation")
            return
        
        try:
            title = f"📊 Instagram Update: @{self.target_username} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body_lines = [
                f"## 🔔 Changes detected for @{self.target_username}",
                "",
                "### 📈 Summary"
            ]
            
            for change in significant_changes:
                icon_map = {
                    'new_post': '📷',
                    'followers_change': '👥',
                    'following_change': '🔗',
                    'posts_change': '📸',
                    'bio_change': '📝',
                    'profile_pic_change': '🖼️',
                    'verification_change': '✅',
                    'privacy_change': '🔒'
                }
                icon = icon_map.get(change['type'], '📱')
                body_lines.append(f"- {icon} **{change['type'].replace('_', ' ').title()}**: {change['message']}")
            
            body_lines.extend([
                "",
                "### 📊 Current Stats",
                f"- **Followers**: {self.data.get('followers', 'N/A')}",
                f"- **Following**: {self.data.get('following', 'N/A')}",
                f"- **Posts**: {self.data.get('posts_count', 'N/A')}",
                "",
                f"**⏰ Timestamp**: {datetime.now().isoformat()}",
                f"**📈 Dashboard**: [View Dashboard](https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/)",
                "",
                "---",
                "*This is an automated message from Instagram Monitor*"
            ])
            
            issue_data = {
                'title': title,
                'body': '\n'.join(body_lines),
                'labels': ['instagram-monitor', 'automated', 'changes-detected']
            }
            
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Instagram-Monitor-Bot/1.0'
            }
            
            response = requests.post(
                f'https://api.github.com/repos/{github_repo}/issues',
                headers=headers,
                json=issue_data,
                timeout=30
            )
            
            if response.status_code == 201:
                issue_url = response.json().get('html_url', '')
                logger.info(f"✅ Created GitHub issue: {issue_url}")
            else:
                logger.warning(f"⚠️ Failed to create GitHub issue: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error creating GitHub issue: {e}")
    
    def send_email_notification(self, changes: List[Dict[str, Any]]) -> None:
        """Send email notification if configured"""
        smtp_host = os.getenv('SMTP_HOST')
        smtp_user = os.getenv('SMTP_USER')
        smtp_pass = os.getenv('SMTP_PASS')
        sender_email = os.getenv('SENDER_EMAIL')
        receiver_email = os.getenv('RECEIVER_EMAIL')
        
        if not all([smtp_host, smtp_user, smtp_pass, sender_email, receiver_email]) or not changes:
            return
        
        try:
            # Filter for important changes
            important_changes = [c for c in changes if c['type'] in ['new_post', 'followers_change', 'bio_change']]
            if not important_changes:
                return
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = receiver_email
            msg['Subject'] = f'📊 Instagram Monitor: @{self.target_username} - {len(important_changes)} changes detected'
            
            body_lines = [
                f"Instagram Monitor detected {len(important_changes)} changes for @{self.target_username}:",
                "",
                "📊 Changes:"
            ]
            
            for change in important_changes:
                body_lines.append(f"• {change['message']}")
            
            if hasattr(self, 'data') and self.data:
                body_lines.extend([
                    "",
                    "📈 Current Stats:",
                    f"• Followers: {self.data.get('followers', 'N/A')}",
                    f"• Following: {self.data.get('following', 'N/A')}",
                    f"• Posts: {self.data.get('posts_count', 'N/A')}"
                ])
            
            github_repo = os.getenv('GITHUB_REPOSITORY', '')
            if github_repo:
                dashboard_url = f"https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/"
                body_lines.extend([
                    "",
                    f"📈 View Dashboard: {dashboard_url}"
                ])
            
            body_lines.extend([
                "",
                f"⏰ Timestamp: {datetime.now().isoformat()}",
                "",
                "This is an automated message from Instagram Monitor."
            ])
            
            msg.attach(MIMEText('\n'.join(body_lines), 'plain'))
            
            # Send email
            smtp_port = int(os.getenv('SMTP_PORT', 587))
            context = ssl.create_default_context()
            
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            logger.info(f"📧 Email notification sent to {receiver_email}")
            
        except Exception as e:
            logger.error(f"❌ Error sending email notification: {e}")
    
    def send_webhook_notification(self, changes: List[Dict[str, Any]]) -> None:
        """Send webhook notification if configured"""
        webhook_url = os.getenv('WEBHOOK_URL')
        if not webhook_url or not changes:
            return
        
        try:
            github_repo = os.getenv('GITHUB_REPOSITORY', '')
            dashboard_url = f"https://{github_repo.split('/')[0]}.github.io/{github_repo.split('/')[1]}/" if github_repo else ""
            
            payload = {
                'text': f"📊 Instagram Monitor: @{self.target_username}",
                'attachments': [{
                    'color': '#E1306C',
                    'title': f"Changes detected for @{self.target_username}",
                    'fields': [
                        {
                            'title': 'Changes',
                            'value': '\n'.join([f"• {change['message']}" for change in changes[:5]]),
                            'short': False
                        }
                    ],
                    'footer': 'Instagram Monitor',
                    'ts': int(datetime.now().timestamp())
                }]
            }
            
            if dashboard_url:
                payload['attachments'][0]['title_link'] = dashboard_url
            
            response = requests.post(webhook_url, json=payload, timeout=30)
            
            if response.status_code == 200:
                logger.info("📱 Webhook notification sent successfully")
            else:
                logger.warning(f"⚠️ Webhook notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error sending webhook notification: {e}")
    
    def run_monitoring(self) -> None:
        """Run a single monitoring cycle"""
        logger.info(f"🚀 Starting monitoring cycle for @{self.target_username}")
        
        try:
            # Fetch current data
            current_data = self.get_profile_data()
            self.data = current_data  # Store for other methods
            
            # Detect changes
            changes = self.detect_changes(current_data)
            
            # Add changes to current data
            current_data['recent_changes'] = changes
            
            # Save data
            self.save_data(current_data)
            
            # Send notifications
            if changes:
                logger.info(f"📢 Sending notifications for {len(changes)} changes")
                self.create_github_issue(changes)
                self.send_email_notification(changes)
                self.send_webhook_notification(changes)
            else:
                logger.info("😴 No changes detected, skipping notifications")
            
            # Create summary file for GitHub Actions
            summary = {
                'success': True,
                'target_username': self.target_username,
                'timestamp': current_data['timestamp'],
                'changes_count': len(changes),
                'followers': current_data['followers'],
                'following': current_data['following'],
                'posts_count': current_data['posts_count'],
                'monitoring_active': True
            }
            
            with open('monitoring_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info("✅ Monitoring cycle completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Monitoring cycle failed: {e}")
            
            # Create error summary
            summary = {
                'success': False,
                'target_username': self.target_username,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'monitoring_active': False
            }
            
            with open('monitoring_summary.json', 'w') as f:
                json.dump(summary, f, indent=2)
            
            raise

def main():
    parser = argparse.ArgumentParser(
        description='Instagram Monitor - GitHub Actions Edition',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python monitor.py --target-user celebrity_username
  python monitor.py --target-user brand_account --debug
  python monitor.py --target-user competitor --session-user monitoring_account
        """
    )
    
    parser.add_argument('--target-user', required=True, help='Instagram username to monitor')
    parser.add_argument('--session-user', help='Instagram username for login (enables more features)')
    parser.add_argument('--session-pass', help='Instagram password for login')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--version', action='version', version='Instagram Monitor 2.0-GitHub-Actions')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("🐛 Debug mode enabled")
    
    # Get credentials from environment if not provided as arguments
    session_user = args.session_user or os.getenv('INSTAGRAM_USER')
    session_pass = args.session_pass or os.getenv('INSTAGRAM_PASS')
    target_user = args.target_user or os.getenv('TARGET_USERNAME')
    
    if not target_user:
        logger.error("❌ Target username is required (--target-user or TARGET_USERNAME env var)")
        sys.exit(1)
    
    logger.info("🎯 Instagram Monitor - GitHub Actions Edition")
    logger.info(f"📱 Target: @{target_user}")
    logger.info(f"🔐 Session: {'Yes' if session_user else 'No (anonymous mode)'}")
    
    # Initialize and run monitor
    monitor = GitHubInstagramMonitor(
        target_username=target_user,
        session_username=session_user,
        session_password=session_pass
    )
    
    monitor.run_monitoring()

if __name__ == "__main__":
    main()
