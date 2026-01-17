#!/usr/bin/env python3
"""
Quick script to restore/fetch data for all default users
Run this locally to populate initial data
"""

import subprocess
import sys
import time
from pathlib import Path

DEFAULT_USERS = [
    "therock",
    "cristiano",
    "selenagomez",
    "taylorswift",
    "kimkardashian"
]

def main():
    print("🚀 Fetching data for all default users...")

    # Use the parent monitoring_data directory - monitor.py creates user subdirs
    output_dir = Path("monitoring_data")
    output_dir.mkdir(parents=True, exist_ok=True)

    success_count = 0
    failed_users = []

    for user in DEFAULT_USERS:
        print(f"\n📊 Processing: @{user}")

        # Build command with only valid arguments that monitor.py accepts
        cmd = [
            sys.executable, "monitor.py",
            "--target-user", user,
            "--output-dir", str(output_dir)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"✅ Success: {user}")
                # Check if files were created
                latest = output_dir / user / "latest.json"
                if latest.exists():
                    print(f"   → Data saved to {latest}")
                success_count += 1
            else:
                print(f"❌ Failed: {user}")
                if result.stderr:
                    # Show only last few lines of error
                    error_lines = result.stderr.strip().split('\n')[-3:]
                    for line in error_lines:
                        print(f"   {line}")
                failed_users.append(user)
        except subprocess.TimeoutExpired:
            print(f"❌ Timeout: {user} (took longer than 120s)")
            failed_users.append(user)
        except Exception as e:
            print(f"❌ Error processing {user}: {e}")
            failed_users.append(user)

        # Small delay to avoid rate limiting
        time.sleep(2)

    print(f"\n✨ Done! {success_count}/{len(DEFAULT_USERS)} users fetched successfully")
    if failed_users:
        print(f"⚠️  Failed users: {', '.join(failed_users)}")
    print("📝 Run 'git add monitoring_data && git commit -m \"Update data\"' to save")

if __name__ == "__main__":
    main()
