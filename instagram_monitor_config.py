# Instagram Monitor Advanced Configuration
# Add this to your existing monitor.py or create as separate config

# Email Notifications
ENABLE_EMAIL_NOTIFICATIONS = False  # Set to True to enable
SMTP_HOST = "your_smtp_server"
SMTP_PORT = 587
SMTP_USER = "your_email@domain.com"
SMTP_PASSWORD = "your_app_password"
SMTP_SSL = True
SENDER_EMAIL = "your_email@domain.com" 
RECEIVER_EMAIL = "notifications@domain.com"

# Advanced Features
DETECT_PROFILE_CHANGES = True
SAVE_PROFILE_PICTURES = True
TRACK_FOLLOWERS = False  # Warning: Can be slow and rate-limited
TRACK_POSTS_DETAILS = True
SAVE_POST_IMAGES = False  # Save post thumbnails
HUMAN_LIKE_DELAYS = True  # Add random delays to avoid detection

# Monitoring Intervals (in seconds)
CHECK_INTERVAL = 3600  # 1 hour
RANDOM_DELAY_MIN = 300  # 5 minutes
RANDOM_DELAY_MAX = 900  # 15 minutes

# File Retention
HISTORY_KEEP_DAYS = 30
MAX_PROFILE_PICS = 10  # Keep last N profile pictures

# Rate Limiting
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds
USER_AGENT_ROTATION = True

# Logging
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_FILE_MAX_SIZE = 10 * 1024 * 1024  # 10MB
KEEP_LOG_FILES = 5

# Change Detection Settings
DETECT_BIO_CHANGES = True
DETECT_NAME_CHANGES = True
DETECT_VERIFICATION_CHANGES = True
DETECT_PRIVACY_CHANGES = True
DETECT_FOLLOWER_CHANGES = False  # Can be noisy
DETECT_POST_COUNT_CHANGES = True

# Notification Triggers
NOTIFY_ON_NEW_POSTS = True
NOTIFY_ON_PROFILE_CHANGES = True
NOTIFY_ON_FOLLOWER_MILESTONES = True  # 1K, 10K, 100K, etc.
NOTIFY_ON_VERIFICATION = True
NOTIFY_ON_PRIVACY_CHANGE = True

# Follower Milestone Thresholds
FOLLOWER_MILESTONES = [1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000]

# Data Export Options
EXPORT_TO_CSV = True
CSV_INCLUDE_CHANGES_ONLY = False  # True = only export when changes detected
CSV_DELIMITER = ","
CSV_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Webhook Integration (Optional)
WEBHOOK_ENABLED = False
WEBHOOK_URL = "https://your-webhook-endpoint.com/instagram-changes"
WEBHOOK_SECRET = "your_webhook_secret"

# Advanced Instagram API Settings
USE_MOBILE_API = True
ROTATE_USER_AGENTS = True
RESPECT_RATE_LIMITS = True
BACKOFF_ON_ERRORS = True
SESSION_PERSISTENCE = True

# Custom User Agents (Optional - leave empty for auto-generation)
CUSTOM_USER_AGENTS = [
    # Add your custom user agents here if needed
]

# Profile Picture Settings
PROFILE_PIC_QUALITY = "hd"  # "hd" or "normal"
PROFILE_PIC_FORMAT = "jpg"
COMPRESS_PROFILE_PICS = True
PROFILE_PIC_MAX_SIZE = 500  # KB

# Security & Privacy
ENCRYPT_SENSITIVE_DATA = False  # Encrypt stored session data
ANONYMIZE_LOGS = False  # Remove usernames from logs
SECURE_DELETE_OLD_FILES = False  # Securely delete old files

# Performance Settings
CONCURRENT_REQUESTS = 1  # Don't increase unless you know what you're doing
REQUEST_TIMEOUT = 30  # seconds
CONNECTION_POOL_SIZE = 5
MAX_REDIRECTS = 3

# Error Handling
CONTINUE_ON_ERRORS = True
ERROR_NOTIFICATION_COOLDOWN = 3600  # Don't spam error emails
FALLBACK_TO_WEB_SCRAPING = True
AUTO_RETRY_FAILED_REQUESTS = True

# Development & Debugging
DEBUG_MODE = False
VERBOSE_LOGGING = False
SAVE_RAW_RESPONSES = False  # Save API responses for debugging
DRY_RUN_MODE = False  # Don't save any data, just test

# Integration Settings
DISCORD_WEBHOOK_URL = ""  # Optional Discord notifications
SLACK_WEBHOOK_URL = ""    # Optional Slack notifications
TELEGRAM_BOT_TOKEN = ""   # Optional Telegram notifications
TELEGRAM_CHAT_ID = ""

# Data Retention Policies
AUTO_CLEANUP_ENABLED = True
CLEANUP_INTERVAL_DAYS = 7
KEEP_CRITICAL_CHANGES = True  # Always keep verification, privacy changes
COMPRESS_OLD_DATA = True

# Backup Settings
AUTO_BACKUP_ENABLED = False
BACKUP_DIRECTORY = "./backups"
BACKUP_INTERVAL_DAYS = 7
BACKUP_RETENTION_DAYS = 30
BACKUP_COMPRESSION = True
