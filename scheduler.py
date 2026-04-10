import sys
sys.stdout.reconfigure(encoding='utf-8')
import schedule
import time
import subprocess
import datetime
import os

LOG_FILE = "scraper_log.txt"

def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def run_scraper():
    log("▶️ Running scraper...")
    try:
        result = subprocess.run(
            [sys.executable, "-X", "utf8", "scraper.py"],
            capture_output=True,
            encoding='utf-8',
            timeout=300
        )
        log(f"✅ Scraper done: {result.stdout[-200:] if result.stdout else 'No output'}")
        if result.returncode == 0:
            push_to_github()
        else:
            log(f"❌ Scraper error: {result.stderr[-200:]}")
    except subprocess.TimeoutExpired:
        log("⚠️ Scraper timed out after 5 minutes")
    except Exception as e:
        log(f"❌ Exception: {e}")

def push_to_github():
    log("📤 Pushing to GitHub...")
    try:
        os.system('git add jobs.json')
        os.system(f'git commit -m "Auto update: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}"')
        os.system('git push origin main')
        log("✅ Pushed to GitHub successfully")
    except Exception as e:
        log(f"❌ GitHub push error: {e}")

# Schedule runs
schedule.every(6).hours.do(run_scraper)          # Every 6 hours
schedule.every().day.at("07:00").do(run_scraper)  # Every morning 7 AM
schedule.every().day.at("18:00").do(run_scraper)  # Every evening 6 PM

log("🕐 Scheduler started. Scraper will run every 6 hours.")
log("Next run times:")
log(f"  • Every 6 hours")
log(f"  • Daily at 7:00 AM")
log(f"  • Daily at 6:00 PM")

# Run once immediately on start
run_scraper()

while True:
    schedule.run_pending()
    time.sleep(60)