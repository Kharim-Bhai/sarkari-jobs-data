import asyncio
import json
import hashlib
import datetime
import re
from playwright.async_api import async_playwright

OUTPUT_FILE = "jobs.json"

def make_id(title, org):
    raw = f"{title}{org}".lower()
    return hashlib.md5(raw.encode()).hexdigest()[:12]

def detect_mode(text):
    text = text.lower()
    online = ["apply online", "online application", "web portal", "register online"]
    offline = ["send by post", "speed post", "registered post", "demand draft",
               "offline application", "send to address", "walk-in", "postal order"]
    has_online = any(k in text for k in online)
    has_offline = any(k in text for k in offline)
    if has_online and has_offline:
        return "BOTH"
    elif has_offline:
        return "OFFLINE"
    elif has_online:
        return "ONLINE"
    return "ONLINE"  # default

def days_left(date_str):
    try:
        deadline = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return (deadline - datetime.datetime.now()).days
    except:
        return 999

async def scrape_ssc(page):
    jobs = []
    try:
        await page.goto("https://ssc.gov.in/portal/latestNotification", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        items = await page.query_selector_all("a[href*='notification'], .notification-item, td a")
        for item in items[:10]:
            title = (await item.inner_text()).strip()
            link = await item.get_attribute("href") or "https://ssc.gov.in"
            if len(title) < 10:
                continue
            if not link.startswith("http"):
                link = "https://ssc.gov.in" + link
            jobs.append({
                "id": make_id(title, "SSC"),
                "title": title,
                "org": "Staff Selection Commission",
                "category": "SSC",
                "category_id": "ssc",
                "level": "Central",
                "state": "All India",
                "state_id": "all_india",
                "application_mode": detect_mode(title),
                "apply_link": link,
                "deadline": get_deadline_from_title(title),
                "posted": "Today",
                "featured": False,
                "type": "Permanent",
                "min_qual_id": "graduate",
                "qualification": "As per notification",
                "age": "As per notification",
                "salary": "As per 7th Pay Commission",
                "posts": 0,
                "description": f"SSC notification: {title}",
                "tags": ["SSC"],
            })
    except Exception as e:
        print(f"SSC scrape error: {e}")
    return jobs

async def scrape_upsc(page):
    jobs = []
    try:
        await page.goto("https://upsc.gov.in/notifications", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        items = await page.query_selector_all("a")
        for item in items[:10]:
            title = (await item.inner_text()).strip()
            link = await item.get_attribute("href") or "https://upsc.gov.in"
            if len(title) < 10 or "upsc" not in title.lower() and "recruitment" not in title.lower():
                continue
            if not link.startswith("http"):
                link = "https://upsc.gov.in" + link
            jobs.append({
                "id": make_id(title, "UPSC"),
                "title": title,
                "org": "Union Public Service Commission",
                "category": "UPSC",
                "category_id": "upsc",
                "level": "Central",
                "state": "All India",
                "state_id": "all_india",
                "application_mode": "ONLINE",
                "apply_link": link,
                "deadline": get_deadline_from_title(title),
                "posted": "Today",
                "featured": True,
                "type": "Permanent",
                "min_qual_id": "graduate",
                "qualification": "As per notification",
                "age": "21-32 years",
                "salary": "₹56,100+",
                "posts": 0,
                "description": f"UPSC notification: {title}",
                "tags": ["UPSC", "IAS", "IPS"],
            })
    except Exception as e:
        print(f"UPSC scrape error: {e}")
    return jobs

async def scrape_employment_news(page):
    jobs = []
    try:
        await page.goto("https://www.employmentnews.gov.in/NewEmp/home.aspx", timeout=30000)
        await page.wait_for_load_state("networkidle", timeout=15000)
        items = await page.query_selector_all("a[href*='advt'], .advt-link, td a")
        for item in items[:15]:
            title = (await item.inner_text()).strip()
            link = await item.get_attribute("href") or "https://employmentnews.gov.in"
            if len(title) < 10:
                continue
            if not link.startswith("http"):
                link = "https://www.employmentnews.gov.in" + link
            mode = detect_mode(title)
            jobs.append({
                "id": make_id(title, "EmploymentNews"),
                "title": title,
                "org": "Employment News / Various Departments",
                "category": "Central Govt",
                "category_id": "groupc",
                "level": "Central",
                "state": "All India",
                "state_id": "all_india",
                "application_mode": mode,
                "apply_link": link if mode == "ONLINE" else None,
                "deadline": get_deadline_from_title(title),
                "posted": "This week",
                "featured": False,
                "type": "Permanent",
                "min_qual_id": "tenth",
                "qualification": "As per notification",
                "age": "As per notification",
                "salary": "As per notification",
                "posts": 0,
                "description": title,
                "tags": ["Central Govt"],
            })
    except Exception as e:
        print(f"Employment News scrape error: {e}")
    return jobs

def get_deadline_from_title(title):
    # Try to extract date from title like "last date 30 June 2025"
    months = {
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }
    title_lower = title.lower()
    for month, num in months.items():
        pattern = rf'(\d{{1,2}})[- ]{month}[a-z]*[- ](\d{{4}})'
        match = re.search(pattern, title_lower)
        if match:
            day = match.group(1).zfill(2)
            year = match.group(2)
            return f"{year}-{num}-{day}"
    # Default: 30 days from now
    future = datetime.datetime.now() + datetime.timedelta(days=30)
    return future.strftime("%Y-%m-%d")

def merge_jobs(existing, new_jobs):
    existing_ids = {j['id'] for j in existing}
    added = 0
    for job in new_jobs:
        if job['id'] not in existing_ids:
            existing.append(job)
            existing_ids.add(job['id'])
            added += 1
    print(f"Added {added} new jobs. Total: {len(existing)}")
    return existing

async def main():
    print("🚀 Starting scraper...")

    # Load existing jobs
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            existing = json.load(f)
        print(f"Loaded {len(existing)} existing jobs")
    except:
        existing = []
        print("Starting fresh")

    all_new = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        print("Scraping SSC...")
        ssc_jobs = await scrape_ssc(page)
        all_new.extend(ssc_jobs)
        print(f"  Found {len(ssc_jobs)} SSC items")

        await asyncio.sleep(3)  # Be respectful to servers

        print("Scraping UPSC...")
        upsc_jobs = await scrape_upsc(page)
        all_new.extend(upsc_jobs)
        print(f"  Found {len(upsc_jobs)} UPSC items")

        await asyncio.sleep(3)

        print("Scraping Employment News...")
        en_jobs = await scrape_employment_news(page)
        all_new.extend(en_jobs)
        print(f"  Found {len(en_jobs)} Employment News items")

        await browser.close()

    # Merge and save
    merged = merge_jobs(existing, all_new)

    # Remove expired jobs older than 90 days
    cutoff = datetime.datetime.now() - datetime.timedelta(days=90)
    merged = [j for j in merged if days_left(j.get('deadline', '')) > -90]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"✅ Saved {len(merged)} jobs to {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(main())