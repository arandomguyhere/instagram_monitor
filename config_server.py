#!/usr/bin/env python3
"""
Configuration API Server for Instagram Monitor
Simple HTTP server to handle configuration changes from the web UI
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import logging

# Configuration file path
CONFIG_FILE = Path("instagram_monitor_config.json")
DEFAULT_CONFIG = {
    "enableEmailNotifications": False,
    "smtpHost": "",
    "smtpPort": 587,
    "smtpUser": "",
    "smtpPassword": "",
    "notificationEmail": "",
    "detectProfilePics": True,
    "useHdPics": True,
    "keepPicHistory": 10,
    "trackFollowers": False,
    "notifyMilestones": True,
    "checkInterval": 60,
    "anonymousMode": False,
    "rotateUserAgents": True,
    "exportCsv": False,
    "keepHistoryDays": 30,
    # Advanced settings
    "webhookUrl": "",
    "discordWebhook": "",
    "slackWebhook": "",
    "backupEnabled": False,
    "maxRetries": 3,
    "requestTimeout": 30
}

class ConfigurationHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests for configuration"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/config':
            self.handle_get_config()
        elif parsed_path.path == '/api/status':
            self.handle_get_status()
        elif parsed_path.path == '/api/test-email':
            self.handle_test_email()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """Handle POST requests for configuration updates"""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/api/config':
            self.handle_update_config()
        elif parsed_path.path == '/api/trigger-monitoring':
            self.handle_trigger_monitoring()
        else:
            self.send_error(404, "Not Found")
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_cors_headers()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())
    
    def load_config(self):
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved_config = json.load(f)
                # Merge with defaults to ensure all keys exist
                config = {**DEFAULT_CONFIG, **saved_config}
                return config
            except Exception as e:
                logging.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG.copy()
    
    def save_config(self, config):
        """Save configuration to file"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Error saving config: {e}")
            return False
    
    def handle_get_config(self):
        """Return current configuration"""
        config = self.load_config()
        
        # Don't send sensitive data like passwords in GET requests
        safe_config = config.copy()
        if 'smtpPassword' in safe_config:
            safe_config['smtpPassword'] = '***' if safe_config['smtpPassword'] else ''
        
        self.send_json_response({
            "success": True,
            "config": safe_config
        })
    
    def handle_update_config(self):
        """Update configuration"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            new_config = json.loads(post_data.decode())
            
            # Load current config
            current_config = self.load_config()
            
            # Update only provided fields
            for key, value in new_config.items():
                if key in DEFAULT_CONFIG:  # Only allow known config keys
                    current_config[key] = value
            
            # Save updated config
            if self.save_config(current_config):
                # Apply configuration to environment variables
                self.apply_config_to_env(current_config)
                
                self.send_json_response({
                    "success": True,
                    "message": "Configuration updated successfully"
                })
            else:
                self.send_json_response({
                    "success": False,
                    "error": "Failed to save configuration"
                }, 500)
                
        except json.JSONDecodeError:
            self.send_json_response({
                "success": False,
                "error": "Invalid JSON data"
            }, 400)
        except Exception as e:
            self.send_json_response({
                "success": False,
                "error": str(e)
            }, 500)
    
    def apply_config_to_env(self, config):
        """Apply configuration to environment variables"""
        env_mapping = {
            'enableEmailNotifications': 'ENABLE_EMAIL_NOTIFICATIONS',
            'smtpHost': 'SMTP_HOST',
            'smtpPort': 'SMTP_PORT', 
            'smtpUser': 'SMTP_USER',
            'smtpPassword': 'SMTP_PASSWORD',
            'notificationEmail': 'RECEIVER_EMAIL',
            'checkInterval': 'CHECK_INTERVAL_MINUTES',
            'detectProfilePics': 'DETECT_PROFILE_PICS',
            'trackFollowers': 'TRACK_FOLLOWERS',
            'anonymousMode': 'ANONYMOUS_MODE',
            'exportCsv': 'EXPORT_CSV'
        }
        
        for config_key, env_var in env_mapping.items():
            if config_key in config:
                value = config[config_key]
                if isinstance(value, bool):
                    os.environ[env_var] = 'true' if value else 'false'
                else:
                    os.environ[env_var] = str(value)
    
    def handle_get_status(self):
        """Return monitoring status"""
        # Check if monitoring is running, last update time, etc.
        status = {
            "monitoring_active": False,
            "last_update": None,
            "active_users": [],
            "errors": []
        }
        
        # Check for recent data files to determine status
        data_dir = Path("data")
        if data_dir.exists():
            active_users = []
            for user_dir in data_dir.iterdir():
                if user_dir.is_dir():
                    stats_file = user_dir / "quick_stats.json"
                    if stats_file.exists():
                        try:
                            with open(stats_file, 'r') as f:
                                data = json.load(f)
                                active_users.append({
                                    "username": data.get("username", user_dir.name),
                                    "last_updated": data.get("last_updated"),
                                    "followers": data.get("followers", 0),
                                    "method": data.get("method", "unknown")
                                })
                        except Exception:
                            pass
            
            status["active_users"] = active_users
            status["monitoring_active"] = len(active_users) > 0
        
        self.send_json_response({
            "success": True,
            "status": status
        })
    
    def handle_test_email(self):
        """Test email configuration"""
        config = self.load_config()
        
        if not config.get('enableEmailNotifications'):
            self.send_json_response({
                "success": False,
                "error": "Email notifications are disabled"
            })
            return
        
        # Import and test email functionality
        try:
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            # Create test email
            msg = MIMEMultipart()
            msg['From'] = config.get('smtpUser', '')
            msg['To'] = config.get('notificationEmail', '')
            msg['Subject'] = "Instagram Monitor - Test Email"
            
            body = "This is a test email from Instagram Monitor. Your email configuration is working correctly!"
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(config.get('smtpHost', ''), config.get('smtpPort', 587))
            server.starttls(context=ssl.create_default_context())
            server.login(config.get('smtpUser', ''), config.get('smtpPassword', ''))
            server.sendmail(config.get('smtpUser', ''), config.get('notificationEmail', ''), msg.as_string())
            server.quit()
            
            self.send_json_response({
                "success": True,
                "message": "Test email sent successfully!"
            })
            
        except Exception as e:
            self.send_json_response({
                "success": False,
                "error": f"Email test failed: {str(e)}"
            })
    
    def handle_trigger_monitoring(self):
        """Trigger manual monitoring run"""
        try:
            import subprocess
            
            # Get the username from POST data
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode())
                username = data.get('username', 'therock')
            else:
                username = 'therock'
            
            # Run monitoring script
            result = subprocess.run([
                sys.executable, 'monitor.py',
                '--target-user', username,
                '--output-dir', f'./data/{username}'
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                self.send_json_response({
                    "success": True,
                    "message": f"Monitoring completed for {username}",
                    "output": result.stdout
                })
            else:
                self.send_json_response({
                    "success": False,
                    "error": f"Monitoring failed: {result.stderr}",
                    "output": result.stdout
                })
                
        except subprocess.TimeoutExpired:
            self.send_json_response({
                "success": False,
                "error": "Monitoring timed out (60 seconds)"
            })
        except Exception as e:
            self.send_json_response({
                "success": False,
                "error": f"Failed to trigger monitoring: {str(e)}"
            })
    
    def log_message(self, format, *args):
        """Override to reduce log noise"""
        if self.path.startswith('/api/'):
            logging.info(f"{self.address_string()} - {format % args}")

def main():
    """Main function to start the configuration server"""
    port = int(os.getenv('CONFIG_PORT', 8080))
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print(f"Starting Instagram Monitor Configuration Server on port {port}")
    print(f"Configuration file: {CONFIG_FILE.absolute()}")
    print(f"Web interface: http://localhost:{port}")
    print("Press Ctrl+C to stop the server")
    
    try:
        server = HTTPServer(('', port), ConfigurationHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down configuration server...")
        server.shutdown()

if __name__ == "__main__":
    main()
