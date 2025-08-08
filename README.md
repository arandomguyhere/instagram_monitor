# Instagram Monitor - GitHub Actions Edition

<div align="center">
  <img src="https://raw.githubusercontent.com/arandomguyhere/instagram-monitor/main/assets/logo.png" alt="Instagram Monitor Logo" width="120"/>
  <h3>Modern Instagram Monitoring with GitHub Actions</h3>
  <p>Track Instagram users' activities with automated monitoring and beautiful analytics dashboard</p>
</div>

A modern, cloud-native Instagram monitoring tool that runs on GitHub Actions and displays beautiful analytics on GitHub Pages. Track Instagram users' activities, follower changes, posts, stories, and more - all automatically and for free.

## ✨ Features

- 🔄 **Automated Monitoring** - Runs every 3 hours via GitHub Actions
- 📊 **Beautiful Dashboard** - Modern web interface with charts and analytics
- 📈 **Historical Tracking** - Complete history of all changes and activities
- 🔔 **Multiple Notifications** - GitHub Issues, email, and webhook support
- 📱 **Responsive Design** - Works perfectly on desktop and mobile
- 🎨 **Modern UI** - Clean, professional interface with dark/light themes
- 📊 **Interactive Charts** - Follower growth, posting patterns, engagement metrics
- 💾 **Version Control** - All data stored in Git with full history
- 🆓 **Completely Free** - Runs on GitHub's free tier

## 📊 What It Monitors

### Profile Analytics
- Follower count changes with detailed diff tracking
- Following count changes
- Bio/description updates
- Profile picture changes
- Account visibility (public/private) changes

### Content Tracking
- New posts and reels with full metadata
- Story updates and expiration tracking
- Post engagement metrics (likes, comments)
- Tagged users and locations
- Post descriptions and hashtags

### Advanced Features
- Historical trend analysis
- Growth rate calculations
- Engagement rate tracking
- Content posting patterns
- Follower acquisition patterns

## 🚀 Quick Setup

### 1. Fork this Repository
Click the "Fork" button at the top of this repository to create your own copy.

### 2. Configure Secrets
Go to your repository's Settings → Secrets and Variables → Actions, then add:

**Required:**
```
INSTAGRAM_USER=your_instagram_username
INSTAGRAM_PASS=your_instagram_password
TARGET_USERNAME=username_to_monitor
```

**Optional Email Notifications:**
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SENDER_EMAIL=your-email@gmail.com
RECEIVER_EMAIL=notifications@example.com
```

### 3. Enable GitHub Pages
1. Go to Settings → Pages
2. Set Source to "GitHub Actions"
3. Your dashboard will be available at: `https://yourusername.github.io/instagram-monitor/`

### 4. Enable Actions
1. Go to the Actions tab
2. Click "I understand my workflows, go ahead and enable them"
3. The monitoring will start automatically

## 📋 Detailed Setup Guide

### Prerequisites
- GitHub account
- Instagram account for monitoring (recommended: create a dedicated account)
- Target Instagram username to monitor

### Step-by-Step Configuration

#### 1. Repository Setup
```bash
# Clone your forked repository
git clone https://github.com/yourusername/instagram-monitor.git
cd instagram-monitor

# Optionally customize the monitoring target
echo "TARGET_USERNAME=celebrity_username" >> .env
```

#### 2. Instagram Credentials Setup

**Option A: Username/Password (Recommended for automation)**
- Create a dedicated Instagram account for monitoring
- Use strong, unique credentials
- Add to repository secrets

**Option B: Session Import (Advanced)**
- Export session from your main Instagram account
- More secure but requires manual renewal

#### 3. Monitoring Configuration

Edit `.github/workflows/monitor.yml` to customize:

```yaml
schedule:
  - cron: '0 */3 * * *'  # Every 3 hours (customizable)
```

Available schedules:
- Every hour: `'0 * * * *'`
- Every 6 hours: `'0 */6 * * *'`
- Daily at 9 AM: `'0 9 * * *'`
- Twice daily: `'0 9,21 * * *'`

#### 4. Notification Setup

**GitHub Issues (Default):**
Notifications are automatically created as GitHub Issues in your repository.

**Email Notifications:**
Add SMTP credentials to repository secrets for email alerts.

**Webhook Notifications:**
Add `WEBHOOK_URL` secret for Slack, Discord, or custom webhooks.

### 5. Advanced Configuration

Create `config.json` for advanced settings:

```json
{
  "monitoring": {
    "check_interval_hours": 3,
    "enable_stories": true,
    "enable_posts": true,
    "enable_followers": true,
    "max_history_entries": 1000
  },
  "notifications": {
    "github_issues": true,
    "email_on_new_post": true,
    "email_on_follower_change": true,
    "webhook_on_all_changes": false
  },
  "ui": {
    "theme": "auto",
    "show_sensitive_data": false,
    "chart_animation": true
  }
}
```

## 📊 Dashboard Features

### Main Analytics View
- **Real-time Statistics** - Current follower count, posts, engagement
- **Growth Charts** - Interactive follower growth over time
- **Recent Activity** - Latest posts, stories, and changes
- **Engagement Metrics** - Average likes, comments, posting frequency

### Historical Analysis
- **Timeline View** - All changes in chronological order
- **Growth Trends** - Daily, weekly, monthly growth patterns
- **Content Analysis** - Most successful posts, optimal posting times
- **Follower Insights** - Acquisition and loss patterns

### Data Export
- **CSV Export** - Raw data for external analysis
- **JSON API** - Programmatic access to all data
- **Chart Export** - Save charts as images
- **Report Generation** - Automated summary reports

## 🔧 Customization

### Monitoring Frequency
Edit `.github/workflows/monitor.yml`:
```yaml
schedule:
  - cron: '0 */1 * * *'  # Every hour
```

### Adding Multiple Users
```yaml
strategy:
  matrix:
    target: ['user1', 'user2', 'user3']
env:
  TARGET_USERNAME: ${{ matrix.target }}
```

### Custom Notifications
Create custom notification logic in `monitor.py`:
```python
def send_custom_notification(change_type, data):
    # Your custom notification logic
    webhook_url = os.getenv('CUSTOM_WEBHOOK')
    # Send to your preferred service
```

## 📁 File Structure

```
instagram-monitor/
├── .github/
│   └── workflows/
│       └── monitor.yml          # GitHub Actions workflow
├── data/                        # Generated monitoring data
│   ├── username_latest.json     # Current state
│   └── username_history.json    # Historical data
├── assets/                      # UI assets
│   ├── logo.png                # Application logo
│   └── favicon.ico             # Browser favicon
├── css/
│   └── style.css               # Dashboard styles
├── js/
│   └── dashboard.js            # Dashboard functionality
├── monitor.py                  # Core monitoring script
├── index.html                  # Dashboard homepage
├── config.json                 # Configuration file
└── README.md                   # This file
```

## 🚨 Troubleshooting

### Common Issues

**1. Actions Not Running**
- Check if Actions are enabled in repository settings
- Verify cron syntax in workflow file
- Ensure repository is not archived

**2. Authentication Errors**
- Verify Instagram credentials in secrets
- Check for recent Instagram security changes
- Consider using session import method

**3. Missing Data**
- Check Actions logs for error messages
- Verify target username exists and is public
- Ensure sufficient API rate limits

**4. Dashboard Not Loading**
- Verify GitHub Pages is enabled
- Check that `index.html` exists in root
- Clear browser cache and try again

### Debug Mode
Enable debug logging by adding to secrets:
```
DEBUG_MODE=true
```

### Rate Limiting
Instagram has strict rate limits. If you encounter issues:
- Increase monitoring interval
- Use session-based authentication
- Add random delays between requests

## 🔒 Security & Privacy

### Best Practices
- **Never commit credentials** - Always use GitHub secrets
- **Use dedicated accounts** - Don't use your main Instagram account
- **Regular credential rotation** - Update passwords periodically
- **Monitor access logs** - Check for suspicious activity

### Data Privacy
- All data is stored in your GitHub repository
- No third-party services have access to your data
- You maintain full control over all information
- Data can be deleted by deleting the repository

### Instagram ToS Compliance
- This tool respects Instagram's rate limits
- Only accesses publicly available information
- Does not perform automated interactions
- Mimics normal user browsing patterns

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/instagram-monitor.git

# Install dependencies
pip install -r requirements.txt

# Run locally
python monitor.py --target-user testuser --debug
```

### Running Tests
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run test suite
pytest tests/

# Run with coverage
pytest --cov=monitor tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built on top of [Instaloader](https://instaloader.github.io/) library
- Inspired by the original [instagram_monitor](https://github.com/misiektoja/instagram_monitor) tool
- Uses Chart.js for beautiful visualizations
- Powered by GitHub Actions and Pages

## 📞 Support

- 🐛 **Bug Reports**: [Open an issue](https://github.com/yourusername/instagram-monitor/issues)
- 💬 **Questions**: [Discussions tab](https://github.com/yourusername/instagram-monitor/discussions)
- 📧 **Email**: support@your-domain.com
- 💬 **Discord**: [Join our community](https://discord.gg/your-invite)

---

**⭐ Star this repository if you find it helpful!**

Made with ❤️ for the open source community
