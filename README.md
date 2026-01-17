# Instagram Monitor

<div align="center">
  <img src="assets/IGlogo.png" alt="Instagram Monitor Logo" width="120"/>
  <h3>Modern Instagram Monitoring with CI/CD</h3>
  <p>Track Instagram users' profile metrics with automated monitoring and a beautiful analytics dashboard</p>
</div>

A cloud-native Instagram monitoring tool that runs on **GitHub Actions** or **GitLab CI/CD** and displays analytics on GitHub/GitLab Pages. Track Instagram users' follower counts, profile changes, and more - automatically and for free.

## Features

- **Automated Monitoring** - Runs on a schedule via GitHub Actions or GitLab CI
- **Profile Tracking** - Monitor followers, following, posts, bio changes
- **Profile Pictures** - Automatic download and caching of profile images
- **Change Detection** - Track and log all profile changes over time
- **Beautiful Dashboard** - Modern web interface with dark theme
- **Historical Data** - Complete history of all monitored changes
- **Multiple Notifications** - GitHub Issues and email support
- **Responsive Design** - Works on desktop and mobile
- **Version Control** - All data stored in Git with full history
- **Completely Free** - Runs on GitHub's free tier

## What It Monitors

### Profile Analytics (Anonymous Mode)
- Follower count changes
- Following count changes
- Post count changes
- Bio/description updates
- Profile picture changes
- Account visibility (public/private)
- Verification status

### With Authentication
- All anonymous features
- Extended API access
- Higher rate limits

## Quick Start

### 1. Fork this Repository
Click the "Fork" button to create your own copy.

### 2. Configure Secrets
Go to Settings > Secrets and Variables > Actions, then add:

**Required:**
```
TARGET_USERNAME=username_to_monitor
```

**Optional - Instagram Authentication:**
```
INSTAGRAM_SESSION_USERNAME=your_instagram_username
INSTAGRAM_SESSION_PASSWORD=your_instagram_password
```

**Optional - Email Notifications:**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SENDER_EMAIL=your-email@gmail.com
RECEIVER_EMAIL=notifications@example.com
```

### 3. Enable GitHub Pages
1. Go to Settings > Pages
2. Set Source to "GitHub Actions"
3. Your dashboard will be available at: `https://yourusername.github.io/instagram_monitor/`

### 4. Enable Actions
1. Go to the Actions tab
2. Click "I understand my workflows, go ahead and enable them"
3. Monitoring will start automatically on schedule

---

## GitLab Setup

### 1. Create a New Project
Create a new GitLab project or import this repository.

### 2. Configure CI/CD Variables
Go to Settings > CI/CD > Variables, then add:

**Required for committing data back:**
```
GITLAB_TOKEN = <your-personal-access-token>
```
Create a Personal Access Token with `api` and `write_repository` scopes.

**Optional - Instagram Authentication:**
```
INSTAGRAM_SESSION_USERNAME = your_instagram_username
INSTAGRAM_SESSION_PASSWORD = your_instagram_password
```

**Optional - Custom User:**
```
TARGET_USERNAME = username_to_monitor
```

### 3. Enable GitLab Pages
GitLab Pages is enabled automatically when the `pages` job runs. Your dashboard will be available at:
`https://yourusername.gitlab.io/instagram-monitor/`

### 4. Set Up Pipeline Schedule
1. Go to CI/CD > Schedules
2. Click "New schedule"
3. Set interval (e.g., `0 */6 * * *` for every 6 hours)
4. Save the schedule

### 5. Run Pipeline Manually (Optional)
1. Go to CI/CD > Pipelines
2. Click "Run pipeline"
3. Optionally set `TARGET_USERNAME` variable for custom user

---

## Command Line Usage

### Basic Monitoring
```bash
# Monitor a single user
python monitor.py --target-user therock

# Monitor with custom output directory
python monitor.py --target-user taylorswift --output-dir ./data

# Enable debug logging
python monitor.py --target-user username --debug

# Disable notifications
python monitor.py --target-user username --no-notifications
```

### Available Arguments

| Argument | Description |
|----------|-------------|
| `--target-user` | Instagram username to monitor (required) |
| `--output-dir` | Output directory for data (default: `./monitoring_data`) |
| `--debug` | Enable debug logging |
| `--friends` | Analyze friends list (requires login) |
| `--no-notifications` | Disable email and GitHub issue notifications |

### Bulk Restore
```bash
# Fetch data for all default users
python restore_all_users.py
```

### Workflow Integration
```bash
# Build monitoring queue from friends analysis
python workflow_integration.py \
    --friends-file data/user_friends_analysis.json \
    --priority mutuals,following,followers \
    --batch-size 8 \
    --days-between 2
```

## Project Structure

```
instagram_monitor/
├── .github/workflows/           # GitHub Actions
│   ├── monitor.yml              # Main monitoring workflow
│   └── monitor-friends.yml      # Friends monitoring workflow
├── .gitlab-ci.yml               # GitLab CI/CD pipeline
├── monitoring_data/             # Generated monitoring data
│   └── {username}/
│       ├── latest.json          # Current profile state
│       ├── history.json         # Historical snapshots
│       └── profile_pic.jpg      # Downloaded profile picture
├── data/                        # Legacy data directory
├── assets/                      # UI assets and logos
├── monitor.py                   # Core monitoring script
├── workflow_integration.py      # Queue builder for batch monitoring
├── restore_all_users.py         # Bulk data restoration script
├── index.html                   # Dashboard homepage
├── requirements.txt             # Python dependencies
└── README.md
```

## Data Format

### latest.json
```json
{
  "username": "therock",
  "full_name": "Dwayne Johnson",
  "biography": "...",
  "is_private": false,
  "is_verified": true,
  "followers": 392930049,
  "following": 175,
  "posts": 8133,
  "profile_pic_url": "https://...",
  "last_updated": "2025-08-10T23:52:54+00:00",
  "schema": "v1"
}
```

### history.json
Array of snapshots with timestamps and detected changes.

## Configuration

### Monitoring Schedule

**GitHub Actions:** Edit `.github/workflows/monitor.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours (default)
```

**GitLab CI:** Create a pipeline schedule in CI/CD > Schedules with cron expression.

Common schedules:
- Every hour: `0 * * * *`
- Every 3 hours: `0 */3 * * *`
- Every 6 hours: `0 */6 * * *`
- Daily at 9 AM UTC: `0 9 * * *`
- Twice daily: `0 9,21 * * *`

### Default Monitored Users
Edit the user list in `restore_all_users.py` or the workflow file:
- therock
- cristiano
- selenagomez
- taylorswift
- kimkardashian

## Troubleshooting

### "Profile does not exist"
- Verify the username is spelled correctly
- Check if the account is active

### "Login required"
- Add Instagram credentials to GitHub secrets
- Consider creating a dedicated monitoring account

### Actions Not Running
- Check if Actions are enabled in repository settings
- Verify cron syntax in workflow file

### Rate Limiting
The system includes built-in delays between requests. If you hit rate limits:
- Reduce monitoring frequency
- Add Instagram credentials for higher limits
- Increase delays between batch operations

## Security

### Best Practices
- Never commit credentials - use GitHub secrets
- Use a dedicated Instagram account for monitoring
- Rotate credentials periodically

### Data Privacy
- All data is stored in your GitHub repository
- No third-party services required
- You control all collected information

## Dependencies

- Python 3.8+
- instaloader
- requests
- python-dateutil
- pytz

Install with:
```bash
pip install -r requirements.txt
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Built on [Instaloader](https://instaloader.github.io/)
- Powered by GitHub Actions and Pages

---

**Star this repository if you find it helpful!**
