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

from instaloader import Instaloader, Profile, ConnectionException

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fetch_profile_data(target_user):
    L = Instaloader()
    
    try:
        logger.info(f"Fetching data for: {target_user}")
        profile = Profile.from_username(L.context, target_user)

        data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "followers": profile.followers,
            "following": profile.followees,
            "is_private": profile.is_private,
            "bio": profile.biography,
            "posts": profile.mediacount,
            "profile_pic_url": profile.profile_pic_url,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Save JSON summary
        with open("monitoring_summary.json", "w") as f:
            json.dump(data, f, indent=2)

        logger.info("✅ monitoring_summary.json created successfully")
        return True

    except ConnectionException as e:
        logger.error(f"Connection error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

    return False

def main():
    parser = argparse.ArgumentParser(description="Monitor Instagram profile stats")
    parser.add_argument("--target-user", required=True, help="Instagram username to monitor")
    args = parser.parse_args()

    success = fetch_profile_data(args.target_user)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
