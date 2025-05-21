# instagram_monitor release notes

This is a high-level summary of the most important changes. 

# Changes in 1.6 (21 May 2025)

**Features and Improvements**:

- **NEW:** The tool can now be installed via pip: `pip install instagram_monitor`
- **NEW:** Added support for external config files, environment-based secrets and dotenv integration with auto-discovery
- **NEW:** Added full support for Instagram reels (not just video posts) and optimized post/reel fetching to reduce API calls
- **NEW:** Added `--import-firefox-session` to load session from Firefox cookies with detection of all profiles (replaces old script)
- **IMPROVE:** Improved detail extraction for posts and reels (via mobile API)
- **NEW:** Added notification for follow-request acceptance and for removed posts/reels
- **NEW:** Display access scope and session user info, including reels count and content visibility
- **IMPROVE:** Enhanced session-login logic to auto‐load or create Instaloader sessions
- **IMPROVE:** Display whether the user can access all content of the monitored account
- **IMPROVE:** Enhanced startup summary to show loaded config, dotenv and ignore-playlists file paths
- **IMPROVE:** Auto detect and display availability of `imgcat` binary for profile picture preview
- **IMPROVE:** Simplified and renamed command-line arguments for improved usability
- **NEW:** Implemented SIGHUP handler for dynamic reload of secrets from dotenv files
- **NEW:** Added configuration option to control clearing the terminal screen at startup
- **IMPROVE:** Changed connectivity check to use Instagram API endpoint for better reliability
- **IMPROVE:** Added check for missing pip dependencies with install guidance
- **IMPROVE:** Allow disabling liveness check by setting interval to 0 (default changed to 12h)
- **IMPROVE:** Improved handling of log file creation
- **IMPROVE:** Refactored CSV file initialization and processing
- **NEW:** Added support for `~` path expansion across all file paths
- **IMPROVE:** Added validation for configured time zones
- **IMPROVE:** Refactored code structure to support packaging for PyPI
- **IMPROVE:** Enforced configuration option precedence: code defaults < config file < env vars < CLI flags
- **IMPROVE:** Made empty profile picture template path configurable
- **IMPROVE:** Only show profile picture template status if the file exists
- **IMPROVE:** Renamed Caption to Description in logs and email bodies
- **IMPROVE:** Email notifications now auto-disable if SMTP config is invalid
- **IMPROVE:** Minimum required Python version increased to 3.9
- **IMPROVE:** Removed short option for `--send-test-email` to avoid ambiguity

**Bug fixes**:

- **BUGFIX:** Fixed data key error, but due to Instagram changes, post/reel details can't be fetched in mode 1 (no session), but count differences are still reported
- **BUGFIX:** Fixed post location fetching after Instagram broke legacy endpoints
- **BUGFIX:** Corrected public vs. private story checks and iteration ([#9](https://github.com/misiektoja/instagram_monitor/issues/9))
- **BUGFIX:** Fixed rare issue with reporting changed profile pic even though timestamp is the same
- **BUGFIX:** Fixed issue where manually defined `LOCAL_TIMEZONE` wasn't applied correctly
- **BUGFIX:** Fixed imgcat command under Windows (use `echo. &` instead of `echo ;`)

# Changes in 1.5 (03 Nov 2024)

**Features and Improvements**:

- **NEW:** Possibility to skip getting posts details (new **-w** / **--skip_getting_posts_details** parameter)
- **IMPROVE:** Print message changed when empty followers list is returned
- **IMPROVE:** Added message about fetching user's latest post/reel (as it might take a while)

**Bug fixes**:

- **BUGFIX:** Fixed bug with saving removed followers/followings to CSV file when empty list is returned and count is > 0
- **BUGFIX:** Fixed wrong CSV entry timestamp in case posts number decreases

# Changes in 1.4 (02 Aug 2024)

**Features and Improvements**:

- **NEW:** Detection when user changes profile visibility from public to private and vice-versa; the code already supported both private and public profiles, however it did not inform the user when the profile visibility has changed; now the tool will notify about it in the console and also via email notifications (**-s**) and CSV file records (**-b**)
- **IMPROVE:** Added info about used mode of the tool in the main screen, so it is easier to correlate it with the description in the README

**Bug fixes**:

- **BUGFIX:** Indentation fixes in the code

# Changes in 1.3 (14 Jun 2024)

**Features and Improvements**:

- **NEW:** Added new parameter (**-z|*8 / **--send_test_email_notification**) which allows to send test email notification to verify SMTP settings defined in the script
- **IMPROVE:** Checking if correct version of Python (>=3.8) is installed
- **IMPROVE:** Possibility to define email sending timeout (default set to 15 secs)

**Bug fixes**:

- **BUGFIX:** Fixed "SyntaxError: f-string: unmatched (" issue in older Python versions
- **BUGFIX:** Fixed "SyntaxError: f-string expression part cannot include a backslash" issue in older Python versions

# Changes in 1.2 (07 Jun 2024)

**Features and Improvements**:

- **IMPROVE:** pyright complained the code is too complex to analyze, so it has been simplified little bit (so it does not complain anymore)
- **IMPROVE:** Changed email notifications string in SIGUSR1 signal handler

**Bug fixes**:

- **BUGFIX:** Fixed nasty bug terminating the script in case of issues while processing story items (yes, copy & paste bug ;-))

# Changes in 1.1 (03 Jun 2024)

**Features and Improvements**:

- **NEW:** Support for **detecting multiple stories** (if session login is used)
- **NEW:** **Fully anonymous download of user's story images & videos** (thumbnail image will be also attached in email notifications and displayed in the terminal if imgcat is installed); yes, user won't know you watched their stories 😉
- **NEW:** **Download of user's post images & videos** (thumbnail image will be also attached in email notifications and displayed in the terminal if imgcat is installed)
- **NEW:** **Detection of changed profile pictures**; since Instagram user's profile picture URL seems to change from time to time, the tool detects changed profile picture by doing binary comparison of saved jpeg files; initially it saves the profile pic to *instagram_{user}_profile_pic.jpeg* file after the tool is started; then during every check the new picture is fetched and the tool does binary comparison if it has changed or not; in case of changes the old profile picture is moved to *instagram_{user}_profile_pic_old.jpeg* file and the new one is saved to *instagram_{user}_profile_pic.jpeg* and also to file named *instagram_{user}_profile_pic_YYmmdd_HHMM.jpeg* (so we can have history of all profile pictures); in order to control the feature there is a new **DETECT_CHANGED_PROFILE_PIC** variable set to True by default; the feature can be disabled by setting it to *False* or by enabling **-k** / **--do_not_detect_changed_profile_pic** parameter
- **NEW:** **Detection of empty profile pictures**; Instagram does not signal the fact of empty user's profile image in their API, that's why we can detect it by using empty profile image template (which seems to be the same on binary level for all users); to use this feature put [instagram_profile_pic_empty.jpeg](instagram_profile_pic_empty.jpeg) file in the dir from which you run the script; this way the tool will be able to detect when user does not have profile image set; it is not mandatory, but highly recommended as otherwise the tool will treat empty profile pic as regular one, so for example user's removal of profile picture will be detected as changed profile picture
- **NEW:** **Attaching changed profile pics and stories/posts images directly in email notifications** (when **-s** parameter is used)
- **NEW:** Feature allowing to **display the profile picture and stories/posts images right in your terminal** (if you have *imgcat* installed); put path to your *imgcat* binary in **IMGCAT_PATH** variable (or leave it empty to disable this functionality)
- **IMPROVE:** Improvements for running the code in **Python under Windows**
- **NEW:** **Automatic detection of local timezone** if you set LOCAL_TIMEZONE variable to 'Auto' (it is default now); requires tzlocal pip module
- **NEW:** Support for honoring last-modified timestamp for saved profile pics (it turned out it reflects timestamp when the picture has been actually added by the user)
- **IMPROVE:** Information about time zone and posts checking hours is displayed in the start screen now
- **NEW:** Fetching of post's location and comments + likes list is back (however needs to be enabled via -t parameter as it highly increases the risk that Instagram will mark the account as an automated tool)
- **NEW:** Added new parameter **-r** / **--skip_getting_story_details** to skip getting detailed info about stories and its images/videos, even if session login is used; you will still get generic information about new stories in such case
- **NEW:** Added new parameter **-t** / **--get_more_post_details** to get more detailed info about new posts like its location and comments + likes list, only possible if session login is used; if not enabled you will still get generic information about new posts; it is disabled by default as for some unknown reasons it highly increases the risk of the account being flagged as an automated tool
- **NEW:** Added new parameter **-k** / **--do_not_detect_changed_profile_pic** which allows to disable detection of changed user's profile picture
- **IMPROVE:** Email sending function send_email() has been rewritten to detect invalid SMTP settings + possibility to attach images
- **IMPROVE:** Strings converted to f-strings for better code visibility
- **IMPROVE:** Rewritten get_date_from_ts(), get_short_date_from_ts(), get_hour_min_from_ts() and get_range_of_dates_from_tss() functions to automatically detect it time object is timestamp (int/float) or datetime
- **IMPROVE:** Better checking for wrong command line arguments
- **IMPROVE:** Help screen reorganization
- **IMPROVE:** pep8 style convention corrections

**Bug fixes**:

- **BUGFIX:** Improved exception handling while processing JSON files
- **BUGFIX:** Escaping of potentially dangerous variables in HTML email templates
- **BUGFIX:** Fix for saving empty followers/followings list to JSON file when the tool is started and Instagram API returns empty list

# Changes in 1.0 (25 Apr 2024)

**Features and Improvements**:

- **NEW:** Support for Instagram users having no posts yet
- **NEW:** Support for handling private profiles
- **IMPROVE:** Improvements in monitoring Instagram user activity without session

**Bug fixes**:

- **BUGFIX:** Disabled fetching location, list of likes and comments for posts due to errors after recent Instagram changes (HTTP Error 400)
