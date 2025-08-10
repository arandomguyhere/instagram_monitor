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
    
    for user in DEFAULT_USERS:
        print(f"\n📊 Processing: @{user}")
        output_dir = Path(f"monitoring_data/{user}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "python", "monitor.py",
            "--mode", "monitor",
            "--target-user", user,
            "--output-dir", str(output_dir),
            "--download-pfp",
            "--unauth-only",  # Use unauth mode for quick restore
            "--verbosity", "1"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Success: {user}")
                # Check if files were created
                latest = output_dir / "latest.json"
                if latest.exists():
                    print(f"   → Data saved to {latest}")
            else:
                print(f"❌ Failed: {user}")
                print(f"   Error: {result.stderr}")
        except Exception as e:
            print(f"❌ Error processing {user}: {e}")
        
        # Small delay to avoid rate limiting
        time.sleep(2)
    
    print("\n✨ Done! Check monitoring_data/ for results")
    print("📝 Run 'git add monitoring_data' and commit to save")

if __name__ == "__main__":
    main()
