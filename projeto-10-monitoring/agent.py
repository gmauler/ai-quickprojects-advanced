import anthropic
import os
import psycopg2
import hashlib
import requests
import smtplib
import json
import time
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Email config — set these as environment variables
# SMTP_EMAIL=your@gmail.com
# SMTP_PASSWORD=your_app_password (Gmail App Password, not account password)
# ALERT_EMAIL=destination@email.com
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
ALERT_EMAIL = os.getenv("ALERT_EMAIL", SMTP_EMAIL)

DB_CONFIG = {
    "host": "localhost", "port": 5432,
    "database": "aidb", "user": "postgres", "password": "password123"
}

def connect():
    return psycopg2.connect(**DB_CONFIG)

def create_tables():
    """
    Two tables:
    - monitored_urls: URLs to watch with check frequency and status
    - url_snapshots: history of content versions with change analysis
    """
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS monitored_urls (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE NOT NULL,
            name VARCHAR(100),
            check_interval_minutes INTEGER DEFAULT 60,
            last_checked TIMESTAMP,
            last_changed TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS url_snapshots (
            id SERIAL PRIMARY KEY,
            url_id INTEGER REFERENCES monitored_urls(id),
            content_hash VARCHAR(32),
            content_preview TEXT,
            change_summary TEXT,
            is_relevant BOOLEAN DEFAULT FALSE,
            checked_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def add_url(url: str, name: str, interval_minutes: int = 60):
    """Register a URL for monitoring."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO monitored_urls (url, name, check_interval_minutes)
        VALUES (%s, %s, %s)
        ON CONFLICT (url) DO UPDATE
        SET name = %s, check_interval_minutes = %s, is_active = TRUE
    """, (url, name, interval_minutes, name, interval_minutes))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Registered: {name} ({url})")

def fetch_content(url: str) -> tuple[str, str]:
    """
    Fetch URL content and return (text_content, md5_hash).
    Strips HTML tags for cleaner comparison.
    """
    headers = {"User-Agent": "Mozilla/5.0 (monitoring-agent/1.0)"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    # Simple HTML stripping — remove tags, keep text
    import re
    text = re.sub(r'<[^>]+>', ' ', response.text)
    text = re.sub(r'\s+', ' ', text).strip()

    content_hash = hashlib.md5(text.encode()).hexdigest()
    return text, content_hash

def get_last_snapshot(url_id: int) -> dict | None:
    """Get the most recent snapshot for a URL."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT content_hash, content_preview
        FROM url_snapshots
        WHERE url_id = %s
        ORDER BY checked_at DESC
        LIMIT 1
    """, (url_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"hash": row[0], "preview": row[1]} if row else None

def analyse_change(url: str, old_content: str, new_content: str) -> dict:
    """
    Use Claude to determine if a content change is relevant.

    The key insight: most web page changes are noise (ads, timestamps,
    view counters). We only want to alert on meaningful changes like
    new incidents, updated documentation, or status changes.
    """
    # Create a simple diff — show first 500 chars of each
    old_preview = old_content[:500] if old_content else "No previous content"
    new_preview = new_content[:500]

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": f"""Analyse this website content change and determine if it is relevant.

URL: {url}

Previous content (first 500 chars):
{old_preview}

New content (first 500 chars):
{new_preview}

Answer these questions:
1. Is this change relevant? (yes/no) — Relevant means: new incidents, status changes, 
   documentation updates, announcements. NOT relevant: timestamps, view counters, ads.
2. One sentence summarising what changed.
3. Urgency: low/medium/high

Return ONLY JSON: {{"relevant": true/false, "summary": "...", "urgency": "low/medium/high"}}"""
        }]
    )

    try:
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except:
        return {"relevant": False, "summary": "Could not analyse change", "urgency": "low"}

def send_alert(url_name: str, url: str, summary: str, urgency: str):
    """
    Send an email alert for a relevant change.
    Requires SMTP_EMAIL and SMTP_PASSWORD environment variables.
    Uses Gmail SMTP with TLS.
    """
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print(f"  [Alert] Email not configured. Change detected: {summary}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[{urgency.upper()}] Change detected: {url_name}"
    msg["From"] = SMTP_EMAIL
    msg["To"] = ALERT_EMAIL

    body = f"""
Monitoring Alert
================
Source: {url_name}
URL: {url}
Urgency: {urgency.upper()}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}

What changed:
{summary}

---
Sent by AI Monitoring Agent
"""
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.sendmail(SMTP_EMAIL, ALERT_EMAIL, msg.as_string())
        print(f"  Alert email sent to {ALERT_EMAIL}")
    except Exception as e:
        print(f"  Email failed: {e}")

def save_snapshot(url_id: int, content_hash: str, content_preview: str,
                  change_summary: str, is_relevant: bool):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO url_snapshots
        (url_id, content_hash, content_preview, change_summary, is_relevant)
        VALUES (%s, %s, %s, %s, %s)
    """, (url_id, content_hash, content_preview[:1000],
          change_summary, is_relevant))
    cur.execute("""
        UPDATE monitored_urls
        SET last_checked = NOW()
        WHERE id = %s
    """, (url_id,))
    conn.commit()
    cur.close()
    conn.close()

def check_url(url_id: int, url: str, name: str):
    """Check a single URL for changes."""
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking: {name}")

    try:
        content, content_hash = fetch_content(url)
        last = get_last_snapshot(url_id)

        # First check — save baseline
        if not last:
            save_snapshot(url_id, content_hash, content[:1000], "Initial snapshot", False)
            print(f"  Baseline stored ({len(content)} chars)")
            return

        # No change
        if last["hash"] == content_hash:
            print(f"  No change detected")
            save_snapshot(url_id, content_hash, content[:1000], "No change", False)
            return

        # Change detected — analyse with Claude
        print(f"  Change detected! Analysing...")
        analysis = analyse_change(url, last["preview"] or "", content)

        print(f"  Relevant: {analysis['relevant']} | {analysis['summary']}")

        save_snapshot(url_id, content_hash, content[:1000],
                     analysis["summary"], analysis["relevant"])

        # Only alert for relevant changes
        if analysis["relevant"]:
            send_alert(name, url, analysis["summary"], analysis["urgency"])

    except requests.RequestException as e:
        print(f"  Fetch error: {e}")
    except Exception as e:
        print(f"  Error: {e}")

def check_all_urls():
    """Check all active monitored URLs."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, url, name FROM monitored_urls
        WHERE is_active = TRUE
    """)
    urls = cur.fetchall()
    cur.close()
    conn.close()

    for url_id, url, name in urls:
        check_url(url_id, url, name)

def show_status():
    """Display current monitoring status."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.name, m.url, m.last_checked,
               COUNT(s.id) as total_checks,
               SUM(CASE WHEN s.is_relevant THEN 1 ELSE 0 END) as alerts
        FROM monitored_urls m
        LEFT JOIN url_snapshots s ON m.id = s.url_id
        WHERE m.is_active = TRUE
        GROUP BY m.id, m.name, m.url, m.last_checked
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print("\nMonitoring Status:")
    print("-" * 70)
    for row in rows:
        last = row[2].strftime('%H:%M:%S') if row[2] else "never"
        print(f"  {row[0]:<30} checks: {row[3]}  alerts: {row[4]}  last: {last}")

if __name__ == "__main__":
    create_tables()

    # Register URLs to monitor
    # Using public status pages and documentation as examples
    add_url(
        "https://www.anthropic.com/news",
        "Anthropic News",
        interval_minutes=30
    )
    add_url(
        "https://status.github.com",
        "GitHub Status",
        interval_minutes=5
    )
    add_url(
        "https://httpbin.org/uuid",
        "Test URL (changes every check)",
        interval_minutes=1
    )

    print("\nRunning initial check on all URLs...")
    check_all_urls()

    print("\nWaiting 10 seconds then checking again (to detect httpbin change)...")
    time.sleep(10)
    check_all_urls()

    show_status()

    # Uncomment to run continuous monitoring with scheduler:
    # print("\nStarting scheduler (Ctrl+C to stop)...")
    # scheduler = BlockingScheduler()
    # scheduler.add_job(check_all_urls, IntervalTrigger(minutes=1))
    # scheduler.start()