#!/usr/bin/env python3
"""
Friends List to Workflow Integration
Save this as: workflow_integration.py
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
import argparse
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class WorkflowManager:
    """Manages integration between friends list and GitHub Actions workflows"""
    
    def __init__(self, output_dir: str = "./"):
        self.output_dir = Path(output_dir)
        self.workflows_dir = self.output_dir / ".github" / "workflows"
        self.queue_file = self.output_dir / "monitoring_queue.json"
        self.config_file = self.output_dir / "workflow_config.json"
    
    def load_friends_data(self, username: str) -> Optional[Dict]:
        """Load friends analysis data"""
        friends_file = self.output_dir / f"{username}_friends_analysis.json"
        
        if not friends_file.exists():
            logger.error(f"No friends data found for {username}")
            return None
        
        try:
            with open(friends_file, 'r', encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load friends data: {e}")
            return None
    
    def create_monitoring_queue(self, source_user: str, categories: List[str] = None, 
                              max_users: int = 50, priority_mutual: bool = True) -> bool:
        """Create a queue of users to monitor based on friends list"""
        
        if categories is None:
            categories = ["mutual_friends", "followers_only", "followings_only"]
        
        friends_data = self.load_friends_data(source_user)
        if not friends_data:
            return False
        
        queue = {
            "source_user": source_user,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config": {
                "max_users": max_users,
                "categories": categories,
                "priority_mutual": priority_mutual
            },
            "queue": [],
            "status": "pending"
        }
        
        # Collect users based on priority
        users_to_monitor = []
        
        # Priority 1: Mutual friends (if enabled)
        if priority_mutual and "mutual_friends" in categories:
            mutual_friends = friends_data.get("mutual_friends", [])
            users_to_monitor.extend([
                {"username": user, "category": "mutual_friend", "priority": 1}
                for user in mutual_friends[:max_users//2]
            ])
        
        # Priority 2: Recent followers/followings
        remaining_slots = max_users - len(users_to_monitor)
        
        if "followers_only" in categories and remaining_slots > 0:
            followers_only = friends_data.get("followers_only", [])
            users_to_monitor.extend([
                {"username": user, "category": "follower_only", "priority": 2}
                for user in followers_only[:remaining_slots//2]
            ])
        
        remaining_slots = max_users - len(users_to_monitor)
        
        if "followings_only" in categories and remaining_slots > 0:
            followings_only = friends_data.get("followings_only", [])
            users_to_monitor.extend([
                {"username": user, "category": "following_only", "priority": 3}
                for user in followings_only[:remaining_slots]
            ])
        
        # Add metadata
        for i, user_data in enumerate(users_to_monitor):
            user_data.update({
                "queue_position": i + 1,
                "status": "queued",
                "added_at": datetime.now(timezone.utc).isoformat(),
                "estimated_start": None,
                "monitoring_started": None,
                "last_check": None
            })
        
        queue["queue"] = users_to_monitor
        queue["total_users"] = len(users_to_monitor)
        
        # Save queue
        try:
            with open(self.queue_file, 'w', encoding="utf-8") as f:
                json.dump(queue, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Created monitoring queue with {len(users_to_monitor)} users")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save monitoring queue: {e}")
            return False
    
    def generate_github_workflow(self, workflow_name: str = "monitor-friends") -> str:
        """Generate GitHub Actions workflow for monitoring friends"""
        
        workflow_content = f"""name: Monitor Friends List

on:
  schedule:
    # Run every 6 hours
    - cron: '0 */6 * * *'
  workflow_dispatch:
    inputs:
      target_user:
        description: 'Specific user to monitor (optional)'
        required: false
        type: string
      batch_size:
        description: 'Number of users to process in this run'
        required: false
        default: '5'
        type: string

jobs:
  setup:
    runs-on: ubuntu-latest
    outputs:
      users: ${{{{ steps.queue.outputs.users }}}}
      batch_size: ${{{{ steps.queue.outputs.batch_size }}}}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install instaloader requests python-dateutil pytz
      
      - name: Get monitoring queue
        id: queue
        run: |
          python3 -c "
import json
import sys
from pathlib import Path

queue_file = Path('monitoring_queue.json')
if not queue_file.exists():
    print('No monitoring queue found')
    sys.exit(1)

with open(queue_file) as f:
    queue_data = json.load(f)

batch_size = int('${{{{ github.event.inputs.batch_size or '5' }}}}')
pending_users = [u for u in queue_data.get('queue', []) if u.get('status') == 'queued']

if '${{{{ github.event.inputs.target_user }}}}':
    # Monitor specific user
    users = ['${{{{ github.event.inputs.target_user }}}}']
else:
    # Monitor next batch from queue
    users = [u['username'] for u in pending_users[:batch_size]]

print(f'users={{json.dumps(users)}}')
print(f'batch_size={{len(users)}}')
          " >> $GITHUB_OUTPUT

  monitor:
    needs: setup
    runs-on: ubuntu-latest
    if: needs.setup.outputs.users != '[]'
    strategy:
      matrix:
        user: ${{{{ fromJson(needs.setup.outputs.users) }}}}
      max-parallel: 3
      fail-fast: false
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install instaloader requests python-dateutil pytz
      
      - name: Create output directory
        run: mkdir -p monitoring_data/${{{{ matrix.user }}}}
      
      - name: Monitor user
        env:
          INSTAGRAM_SESSION_USERNAME: ${{{{ secrets.INSTAGRAM_SESSION_USERNAME }}}}
          INSTAGRAM_SESSION_PASSWORD: ${{{{ secrets.INSTAGRAM_SESSION_PASSWORD }}}}
          SMTP_HOST: ${{{{ secrets.SMTP_HOST }}}}
          SMTP_USER: ${{{{ secrets.SMTP_USER }}}}
          SMTP_PASSWORD: ${{{{ secrets.SMTP_PASSWORD }}}}
          SENDER_EMAIL: ${{{{ secrets.SENDER_EMAIL }}}}
          RECEIVER_EMAIL: ${{{{ secrets.RECEIVER_EMAIL }}}}
        run: |
          python3 monitor.py \\
            --target-user ${{{{ matrix.user }}}} \\
            --output-dir monitoring_data/${{{{ matrix.user }}}} \\
            --friends \\
            --enable-email \\
            --workflow-mode \\
            --update-queue \\
            --history-keep 50
      
      - name: Upload monitoring data
        uses: actions/upload-artifact@v4
        with:
          name: monitoring-data-${{{{ matrix.user }}}}
          path: monitoring_data/${{{{ matrix.user }}}}
          retention-days: 30
      
      - name: Commit data (if changed)
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add monitoring_data/${{{{ matrix.user }}}} monitoring_queue.json
          git diff --staged --quiet || git commit -m "Update monitoring data for ${{{{ matrix.user }}}}"
          git push
        continue-on-error: true

  summary:
    needs: [setup, monitor]
    runs-on: ubuntu-latest
    if: always()
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate summary
        run: |
          echo "# Friends Monitoring Summary" >> $GITHUB_STEP_SUMMARY
          echo "**Batch size:** ${{{{ needs.setup.outputs.batch_size }}}}" >> $GITHUB_STEP_SUMMARY
          echo "**Users processed:** ${{{{ needs.setup.outputs.users }}}}" >> $GITHUB_STEP_SUMMARY
          echo "**Timestamp:** $(date -u)" >> $GITHUB_STEP_SUMMARY
"""
        
        return workflow_content
    
    def generate_workflow_config(self) -> Dict:
        """Generate configuration for workflow automation"""
        config = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "settings": {
                "batch_size": 5,
                "max_concurrent": 3,
                "retry_failed": True,
                "notification_on_complete": True,
                "data_retention_days": 30
            },
            "categories": {
                "mutual_friends": {
                    "enabled": True,
                    "priority": 1,
                    "max_users": 25
                },
                "followers_only": {
                    "enabled": True,
                    "priority": 2,
                    "max_users": 15
                },
                "followings_only": {
                    "enabled": True,
                    "priority": 3,
                    "max_users": 10
                }
            },
            "monitoring": {
                "interval_hours": 6,
                "enable_email": True,
                "track_changes": True,
                "save_profile_pics": False,
                "history_keep": 50
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return config
        except Exception as e:
            logger.error(f"Failed to save workflow config: {e}")
            return {}
    
    def setup_workflow_files(self, workflow_name: str = "monitor-friends") -> bool:
        """Setup all necessary workflow files"""
        try:
            # Create workflows directory
            self.workflows_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate and save workflow
            workflow_content = self.generate_github_workflow(workflow_name)
            workflow_file = self.workflows_dir / f"{workflow_name}.yml"
            
            with open(workflow_file, 'w', encoding="utf-8") as f:
                f.write(workflow_content)
            
            # Generate config
            self.generate_workflow_config()
            
            logger.info(f"Workflow files created:")
            logger.info(f"  - {workflow_file}")
            logger.info(f"  - {self.config_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup workflow files: {e}")
            return False
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        if not self.queue_file.exists():
            return {"status": "no_queue", "message": "No monitoring queue found"}
        
        try:
            with open(self.queue_file, 'r', encoding="utf-8") as f:
                queue_data = json.load(f)
            
            total_users = queue_data.get("total_users", 0)
            completed = len([u for u in queue_data.get("queue", []) if u.get("status") == "completed"])
            pending = len([u for u in queue_data.get("queue", []) if u.get("status") == "queued"])
            
            return {
                "status": "active",
                "total_users": total_users,
                "completed": completed,
                "pending": pending,
                "progress": f"{completed}/{total_users}",
                "source_user": queue_data.get("source_user"),
                "created_at": queue_data.get("created_at")
            }
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to read queue: {e}"}
    
    def reset_queue(self) -> bool:
        """Reset the monitoring queue"""
        try:
            if self.queue_file.exists():
                self.queue_file.unlink()
            logger.info("Monitoring queue reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset queue: {e}")
            return False
    
    def add_users_to_queue(self, usernames: List[str], category: str = "manual") -> bool:
        """Manually add users to the monitoring queue"""
        
        # Load existing queue or create new one
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r', encoding="utf-8") as f:
                    queue_data = json.load(f)
            except Exception:
                queue_data = {"queue": [], "total_users": 0}
        else:
            queue_data = {
                "source_user": "manual",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "queue": [],
                "total_users": 0,
                "status": "pending"
            }
        
        # Get existing usernames to avoid duplicates
        existing_users = {u["username"] for u in queue_data.get("queue", [])}
        
        # Add new users
        new_users = []
        for username in usernames:
            if username not in existing_users:
                new_users.append({
                    "username": username,
                    "category": category,
                    "priority": 4,  # Manual additions get lower priority
                    "queue_position": len(queue_data["queue"]) + len(new_users) + 1,
                    "status": "queued",
                    "added_at": datetime.now(timezone.utc).isoformat(),
                    "estimated_start": None,
                    "monitoring_started": None,
                    "last_check": None
                })
        
        if new_users:
            queue_data["queue"].extend(new_users)
            queue_data["total_users"] = len(queue_data["queue"])
            
            try:
                with open(self.queue_file, 'w', encoding="utf-8") as f:
                    json.dump(queue_data, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Added {len(new_users)} users to monitoring queue")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update queue: {e}")
                return False
        else:
            logger.info("No new users to add (all already in queue)")
            return True

def main():
    parser = argparse.ArgumentParser(
        description="Friends List to Workflow Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create monitoring queue from friends list
  python workflow_integration.py --source-user username --create-queue
  
  # Setup GitHub Actions workflow
  python workflow_integration.py --setup-workflow
  
  # Check queue status
  python workflow_integration.py --queue-status
  
  # Manually add users to queue
  python workflow_integration.py --add-users user1 user2 user3
  
  # Reset queue
  python workflow_integration.py --reset-queue
        """
    )
    
    parser.add_argument("--output-dir", default="./", help="Output directory")
    parser.add_argument("--source-user", help="Source user to extract friends from")
    
    # Queue management
    parser.add_argument("--create-queue", action="store_true", help="Create monitoring queue from friends list")
    parser.add_argument("--queue-status", action="store_true", help="Show queue status")
    parser.add_argument("--reset-queue", action="store_true", help="Reset monitoring queue")
    parser.add_argument("--add-users", nargs="+", help="Manually add users to queue")
    
    # Workflow setup
    parser.add_argument("--setup-workflow", action="store_true", help="Setup GitHub Actions workflow")
    parser.add_argument("--workflow-name", default="monitor-friends", help="Workflow name")
    
    # Configuration
    parser.add_argument("--max-users", type=int, default=50, help="Maximum users to queue")
    parser.add_argument("--categories", nargs="+", 
                       choices=["mutual_friends", "followers_only", "followings_only"],
                       default=["mutual_friends", "followers_only"],
                       help="Categories to include in queue")
    parser.add_argument("--no-priority-mutual", action="store_true", 
                       help="Don't prioritize mutual friends")
    
    args = parser.parse_args()
    
    workflow_manager = WorkflowManager(args.output_dir)
    
    # Handle specific commands
    if args.setup_workflow:
        logger.info("Setting up GitHub Actions workflow...")
        success = workflow_manager.setup_workflow_files(args.workflow_name)
        if success:
            print("\n✅ Workflow setup complete!")
            print("\nNext steps:")
            print("1. Add these secrets to your GitHub repository:")
            print("   - INSTAGRAM_SESSION_USERNAME")
            print("   - INSTAGRAM_SESSION_PASSWORD") 
            print("   - SMTP_HOST, SMTP_USER, SMTP_PASSWORD")
            print("   - SENDER_EMAIL, RECEIVER_EMAIL")
            print("\n2. Commit and push the workflow files")
            print("3. Create a monitoring queue with --create-queue")
        sys.exit(0 if success else 1)
    
    if args.queue_status:
        status = workflow_manager.get_queue_status()
        print("\n📊 Queue Status:")
        print(f"Status: {status.get('status')}")
        if status.get('status') == 'active':
            print(f"Source user: {status.get('source_user')}")
            print(f"Total users: {status.get('total_users')}")
            print(f"Completed: {status.get('completed')}")
            print(f"Pending: {status.get('pending')}")
            print(f"Progress: {status.get('progress')}")
            print(f"Created: {status.get('created_at')}")
        elif status.get('status') == 'no_queue':
            print("No monitoring queue found. Create one with --create-queue")
        else:
            print(f"Error: {status.get('message')}")
        sys.exit(0)
    
    if args.reset_queue:
        success = workflow_manager.reset_queue()
        sys.exit(0 if success else 1)
    
    if args.add_users:
        success = workflow_manager.add_users_to_queue(args.add_users)
        sys.exit(0 if success else 1)
    
    if args.create_queue:
        if not args.source_user:
            logger.error("--source-user required for creating queue")
            sys.exit(1)
        
        logger.info(f"Creating monitoring queue from {args.source_user} friends list...")
        success = workflow_manager.create_monitoring_queue(
            args.source_user,
            args.categories,
            args.max_users,
            not args.no_priority_mutual
        )
        
        if success:
            status = workflow_manager.get_queue_status()
            print(f"\n✅ Queue created successfully!")
            print(f"Total users queued: {status.get('total_users')}")
            print(f"Categories: {', '.join(args.categories)}")
            print("\nNext steps:")
            print("1. Setup workflow with --setup-workflow (if not done)")
            print("2. Push to GitHub to trigger monitoring")
        
        sys.exit(0 if success else 1)
    
    # Default: show help
    parser.print_help()

if __name__ == "__main__":
    main()
