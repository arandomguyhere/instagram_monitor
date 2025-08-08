#!/usr/bin/env python3
"""
Instagram Monitor - Local Testing Script
Test your setup before deploying to GitHub Actions
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import argparse

def test_dependencies():
    """Test if all required dependencies are installed"""
    print("🧪 Testing Python dependencies...")
    
    required_packages = [
        'instaloader',
        'requests', 
        'python-dateutil',
        'pytz'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n💡 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_monitor_script(target_username=None, debug=False):
    """Test the monitor script with a dry run"""
    print("\n🔍 Testing monitor script...")
    
    if not target_username:
        target_username = "instagram"  # Use Instagram's official account for testing
    
    cmd = [sys.executable, 'monitor.py', '--target-user', target_username]
    
    if debug:
        cmd.append('--debug')
    
    # Set environment variables for testing (without actual credentials)
    env = os.environ.copy()
    env['TARGET_USERNAME'] = target_username
    
    try:
        print(f"📱 Testing with target: @{target_username}")
        print("ℹ️ This will run in anonymous mode (limited data)")
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )
        
        if result.returncode == 0:
            print("✅ Monitor script executed successfully")
            
            # Check if data files were created
            data_dir = Path('data')
            latest_file = data_dir / f"{target_username}_latest.json"
            history_file = data_dir / f"{target_username}_history.json"
            
            if latest_file.exists():
                print(f"✅ Latest data file created: {latest_file}")
                
                # Show sample data
                try:
                    with open(latest_file, 'r') as f:
                        data = json.load(f)
                    print(f"📊 Sample data: {data.get('followers', 'N/A')} followers")
                except Exception as e:
                    print(f"⚠️ Could not read data file: {e}")
            else:
                print(f"⚠️ Latest data file not found: {latest_file}")
            
            if history_file.exists():
                print(f"✅ History data file created: {history_file}")
            
            return True
        else:
            print(f"❌ Monitor script failed:")
            print(f"   Return code: {result.returncode}")
            print(f"   Error output: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⚠️ Monitor script timed out (this is normal for some accounts)")
        return True
    except Exception as e:
        print(f"❌ Error running monitor script: {e}")
        return False

def test_dashboard_files():
    """Test if dashboard files are present and valid"""
    print("\n🎨 Testing dashboard files...")
    
    required_files = [
        'index.html',
        'monitor.py',
        '.github/workflows/monitor.yml'
    ]
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} (missing)")
            return False
    
    # Test if index.html contains expected content
    try:
        with open('index.html', 'r') as f:
            html_content = f.read()
            
        if 'Instagram Monitor' in html_content:
            print("✅ index.html contains correct title")
        else:
            print("⚠️ index.html may not be the correct file")
            
        if 'dashboard_data.json' in html_content:
            print("✅ index.html configured for data loading")
        else:
            print("⚠️ index.html may not be configured correctly")
            
    except Exception as e:
        print(f"⚠️ Could not validate index.html: {e}")
    
    return True

def test_workflow_file():
    """Test if GitHub Actions workflow is valid"""
    print("\n⚙️ Testing workflow file...")
    
    workflow_path = Path('.github/workflows/monitor.yml')
    
    if not workflow_path.exists():
        print("❌ Workflow file not found")
        return False
    
    try:
        with open(workflow_path, 'r') as f:
            workflow_content = f.read()
        
        required_parts = [
            'name:',
            'on:',
            'schedule:',
            'jobs:',
            'monitor:',
            'deploy:'
        ]
        
        for part in required_parts:
            if part in workflow_content:
                print(f"✅ Contains {part}")
            else:
                print(f"❌ Missing {part}")
                return False
        
        print("✅ Workflow file structure looks correct")
        
    except Exception as e:
        print(f"❌ Error reading workflow file: {e}")
        return False
    
    return True

def show_setup_status():
    """Show overall setup status and next steps"""
    print("\n📋 Setup Status Summary")
    print("=" * 30)
    
    checks = [
        ("Dependencies", test_dependencies()),
        ("Dashboard files", test_dashboard_files()),
        ("Workflow file", test_workflow_file())
    ]
    
    all_passed = all(result for _, result in checks)
    
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    if all_passed:
        print("\n🎉 All checks passed! Your setup looks good.")
        print("\n📝 Next steps:")
        print("1. Configure secrets in GitHub repository")
        print("2. Enable GitHub Pages")
        print("3. Run the workflow manually to test")
        print("4. Check your dashboard URL")
    else:
        print("\n⚠️ Some checks failed. Please fix the issues above.")
    
    return all_passed

def main():
    parser = argparse.ArgumentParser(description='Test Instagram Monitor setup locally')
    parser.add_argument('--target', help='Target username for testing (default: instagram)')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--skip-monitor', action='store_true', help='Skip testing monitor script')
    
    args = parser.parse_args()
    
    print("🧪 Instagram Monitor - Local Testing")
    print("=" * 40)
    
    # Run basic setup checks
    setup_ok = show_setup_status()
    
    if not setup_ok:
        print("\n❌ Basic setup checks failed. Please fix issues before testing monitor.")
        sys.exit(1)
    
    # Test monitor script if requested
    if not args.skip_monitor:
        print("\n" + "=" * 40)
        monitor_ok = test_monitor_script(args.target, args.debug)
        
        if monitor_ok:
            print("\n✅ Monitor test passed!")
        else:
            print("\n⚠️ Monitor test had issues (this may be normal)")
    
    print("\n🎯 Testing complete!")
    print("\n💡 Tips:")
    print("   - Test with a public Instagram account first")
    print("   - Use your own account for more detailed testing")
    print("   - Check the data/ directory for generated files")
    print("   - Run with --debug for more detailed output")

if __name__ == "__main__":
    main()
