# Instagram Monitor - GitHub Actions Edition

<div align="center">
  <img src="assets/IGlogo.png" alt="Instagram Monitor Logo" width="120"/>
  <h3>Modern Instagram Monitoring with GitHub Actions</h3>
  <p>Track Instagram users' activities with automated monitoring, friends list analysis, and beautiful analytics dashboard</p>
</div>

A modern, cloud-native Instagram monitoring tool that runs on GitHub Actions and displays beautiful analytics on GitHub Pages. Track Instagram users' activities, follower changes, posts, stories, friends lists, and more - all automatically and for free.

## ✨ Features

- 🔄 **Automated Monitoring** - Runs every 3 hours via GitHub Actions
- 👥 **Friends List Analysis** - Track followers, followings, and mutual connections
- 🎯 **Workflow Integration** - Auto-queue friends for monitoring
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

### Friends List Features ✨ NEW
- **Complete friends tracking** - Monitor who follows and who they follow
- **Mutual friends detection** - Identify shared connections
- **Friends change detection** - Track new followers, lost followers, unfollows
- **Relationship mapping** - Analyze social connections and networks
- **Export capabilities** - JSON, CSV, and TXT formats
- **Workflow automation** - Auto-queue friends for monitoring

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

## 🚫 **What Requires Login (Currently Missing)**

### **1. Friends List Data**
* ❌ **Followers list** - Cannot retrieve the actual usernames of followers
* ❌ **Followings list** - Cannot retrieve the actual usernames of people they follow
* ❌ **Mutual friends analysis** - No way to identify mutual connections
* ❌ **Friends changes tracking** - Can't detect who unfollowed/followed

### **2. Detailed Post/Reel Content**
* ❌ **Latest posts/reels details** - Limited to basic info only
* ❌ **Post comments** - Cannot retrieve comments on posts
* ❌ **Post likes list** - Cannot see who liked posts
* ❌ **Tagged users** - Cannot see who's tagged in posts
* ❌ **Post locations** - Cannot retrieve location data

### **3. Stories Information**
* ❌ **Story details** - Cannot access any story content
* ❌ **Story expiry times** - No access to story metadata
* ❌ **Story media** - Cannot download story images/videos

### **4. Enhanced Monitoring**
* ❌ **Real-time change detection** - Limited change tracking
* ❌ **Detailed relationship mapping** - No social network analysis
* ❌ **Advanced analytics** - Missing engagement data

## ✅ **What Still Works Without Login (Anonymous Mode)**

### **Basic Profile Information:**
* ✅ **Username** - @therock (Dwayne Johnson)
* ✅ **Follower count** - 392,939,125
* ✅ **Following count** - 174
* ✅ **Posts count** - 8,133
* ✅ **Profile status** - Public/Private, Verified status
* ✅ **Bio text** - Profile description
* ✅ **Profile picture URL** - Can download profile pics
* ✅ **Basic change detection** - Follower count changes, bio changes

### **Limited Post Data:**
* ✅ **Post count changes** - Can detect new posts
* ✅ **Basic post metadata** - Timestamps, URLs
* ✅ **Public post thumbnails** - Can download images

## 🔧 **What You Need Login For (The Missing 80%)**

The friends list functionality you want requires **authenticated access** because Instagram treats this as sensitive data:

```python
# This fails without login:
followers = [follower.username for follower in profile.get_followers()]
followings = [followee.username for followee in profile.get_followees()]

# Error: "Login required to get a profile's followers/followees"
```

## 🎯 **The Bottom Line**

**Without login, you get about 20% of the functionality:**
* Basic profile metrics (what you saw in your test)
* Profile picture changes
* Bio changes
* Post count changes

**With login, you unlock the remaining 80%:**
* Complete friends lists (followers/followings)
* Friends analysis and mutual connections
* Detailed post/story content
* Advanced change tracking
* Social network mapping

Your test run was actually **successful** for anonymous monitoring, but the friends list feature (which is the main value-add) requires authentication. That's why the script said "Login required to get a profile's followers."

To unlock the full functionality and get the friends lists that feed into the workflow automation, you'll need to add Instagram credentials.

## 🚀 Quick Setup

### 1. Fork this Repository
Click the "Fork" button at the top of this repository to create your own copy.

### 2. Configure Secrets
Go to your repository's Settings → Secrets and Variables → Actions, then add:

**Required for Basic Monitoring:**
```
TARGET_USERNAME=username_to_monitor
```

**Required for Friends List & Advanced Features:**
```
INSTAGRAM_SESSION_USERNAME=your_instagram_username
INSTAGRAM_SESSION_PASSWORD=your_instagram_password
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

## 🎯 Friends List & Workflow Integration

### Generate Friends List
```bash
# Monitor a celebrity and get their friends list
python monitor.py --target-user taylorswift --friends

# Show existing friends analysis
python monitor.py --target-user taylorswift --show-friends

# Export friends to CSV
python monitor.py --target-user taylorswift --export-friends csv
```

### Create Monitoring Queue
```bash
# Create queue with top 30 mutual friends + followers
python workflow_integration.py --source-user taylorswift --create-queue --max-users 30

# Only mutual friends (higher engagement)
python workflow_integration.py --source-user celebrity --create-queue --categories mutual_friends --max-users 20
```

### Setup Automated Workflow
```bash
# Generate GitHub Actions workflow
python workflow_integration.py --setup-workflow

# Check queue status
python workflow_integration.py --queue-status

# Add users manually
python workflow_integration.py --add-users user1 user2 user3
```

### Workflow Features
- **Smart Batching** - Processes users in configurable batches
- **Priority System** - Mutual friends get highest priority
- **Progress Tracking** - Real-time queue status updates
- **Parallel Processing** - Up to 3 users simultaneously
- **Artifact Storage** - Data saved for 30 days
- **Email Notifications** - Get notified of changes

## 📁 File Structure

```
instagram-monitor/
├── .github/
│   └── workflows/
│       ├── monitor.yml              # Main monitoring workflow
│       └── monitor-friends.yml      # Friends monitoring workflow
├── data/                           # Generated monitoring data
│   ├── username_latest.json        # Current state
│   ├── username_history.json       # Historical data
│   ├── username_friends_analysis.json  # Friends analysis
│   └── username_followers.json     # Complete followers list
├── monitoring_data/                # Queue processing results
│   ├── monitoring_queue.json       # Queue of users to monitor
│   └── user1/                     # Individual user data
├── assets/                         # UI assets
├── css/ & js/                     # Dashboard files
├── monitor.py                     # Core monitoring script
├── workflow_integration.py        # Friends → workflow integration
├── index.html                     # Dashboard homepage
└── README.md                      # This file
```

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
```

#### 2. Instagram Credentials Setup

**Option A: Username/Password (Recommended for automation)**
- Create a dedicated Instagram account for monitoring
- Use strong, unique credentials
- Add to repository secrets

**Option B: Anonymous Mode (Limited functionality)**
- No credentials needed
- Only basic profile metrics available
- Friends list features disabled

#### 3. Friends List Monitoring Setup

```bash
# 1. Install dependencies locally (for setup)
pip install instaloader requests python-dateutil pytz

# 2. Get a celebrity's friends list
python monitor.py --target-user taylorswift --friends

# 3. Create monitoring queue from friends
python workflow_integration.py --source-user taylorswift --create-queue --max-users 30

# 4. Setup automated workflow
python workflow_integration.py --setup-workflow

# 5. Commit and push
git add .
git commit -m "Setup automated friends monitoring"
git push
```

#### 4. Monitoring Configuration

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

## 🔧 Advanced Configuration

### Friends List Categories
- **Mutual Friends** - People who both follow and are followed by the target
- **Followers Only** - People who follow the target but aren't followed back
- **Followings Only** - People the target follows but who don't follow back

### Queue Management
```bash
# Check queue status
python workflow_integration.py --queue-status

# Add users manually
python workflow_integration.py --add-users user1 user2 user3

# Reset queue
python workflow_integration.py --reset-queue
```

### Export Options
```bash
# Export friends to CSV
python monitor.py --target-user username --export-friends csv

# Export to JSON
python monitor.py --target-user username --export-friends json

# View timeline
python monitor.py --target-user username --friends-timeline
```

## 🚨 Troubleshooting

### Common Issues

**1. "Login required for followers"**
- Add Instagram credentials to GitHub secrets
- Use INSTAGRAM_SESSION_USERNAME and INSTAGRAM_SESSION_PASSWORD
- Consider creating a dedicated monitoring account

**2. Actions Not Running**
- Check if Actions are enabled in repository settings
- Verify cron syntax in workflow file
- Ensure repository is not archived

**3. Authentication Errors**
- Verify Instagram credentials in secrets
- Check for recent Instagram security changes
- Try using session import method locally first

**4. Missing Friends Data**
- Ensure authentication is working
- Check that target profile is public or accessible
- Verify sufficient API rate limits

### Debug Mode
Enable debug logging by adding to secrets:
```
DEBUG_MODE=true
```

### Rate Limiting
Instagram has strict rate limits. The system includes:
- Built-in delays between requests
- Batch processing with pauses
- Smart retry logic
- Parallel processing limits

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
