from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
import sqlite3
import tldextract
import re
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Import your existing modules
from db import init_db
from scraper import StealthScraper

# Load environment variables
load_dotenv()
SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.jcarletto.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 465))
SMTP_USER = os.getenv("SMTP_USER", "PriceAlerts@mail.jcarletto.com")
SMTP_PASS = os.getenv("SMTP_PASS")

# --- SCHEDULER SETUP ---
def run_scheduled_scrapes():
    print("[Scheduler] Starting routine batch scrape...")
    conn = get_db_connection()
    try:
        # Fetch all product IDs from the database
        products = conn.execute("SELECT id FROM products").fetchall()
        for p in products:
            # The rate limiter inside StealthScraper will automatically pause this loop 
            # if we hit the same domain too many times rapidly.
            scrape_product(p['id'])
    except Exception as e:
        print(f"[Scheduler] Error during batch scrape: {e}")
    finally:
        conn.close()
    print("[Scheduler] Routine batch scrape complete.")

scheduler = BackgroundScheduler()
# Schedule the job to run every 6 hours (4 times a day)
scheduler.add_job(run_scheduled_scrapes, 'interval', hours=6)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    init_db()
    scheduler.start()
    print("Background scheduler started (Running every 6 hours).")
    yield
    # Shutdown Events
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

# --- Pydantic Models ---
class TrackRequest(BaseModel):
    url: str
    name_selector: str
    price_selector: str
    alert_email: Optional[str] = None
    alert_threshold: Optional[float] = None
    alert_lowest_30d: bool = False

class UpdateRequest(BaseModel):
    url: str
    name_selector: str
    price_selector: str
    alert_email: Optional[str] = None
    alert_threshold: Optional[float] = None
    alert_lowest_30d: bool = False

class TestEmailRequest(BaseModel):
    email: str

def get_db_connection():
    conn = sqlite3.connect('tracker.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = 1") 
    return conn

# --- Email Sender Function ---
def send_alert_email(to_email: str, subject: str, html_body: str):
    if not to_email or not SMTP_PASS:
        print("Skipping email: Missing recipient or SMTP password in .env")
        return False
        
    msg = MIMEMultipart()
    msg['From'] = f"Price Tracker <{SMTP_USER}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        print(f"Alert email successfully sent to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

# --- The Scraper Engine ---
def scrape_product(product_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = c.fetchone()
    
    if not product:
        conn.close()
        return

    c.execute("UPDATE products SET last_status = 'scraping', last_error = NULL WHERE id = ?", (product_id,))
    conn.commit()

    scraper = StealthScraper()
    try:
        soup = scraper.fetch_page(product['url'])
        
        price = None
        product_name = product['name']

        name_element = soup.select_one(product['name_selector'])
        if name_element:
            product_name = name_element.text.strip()

        price_element = soup.select_one(product['price_selector'])
        if price_element:
            clean_price = re.sub(r'[^\d.]', '', price_element.text.strip())
            if clean_price:
                price = float(clean_price)

        if price:
            c.execute("UPDATE products SET name = ?, last_status = 'success', last_error = NULL WHERE id = ?", (product_name, product_id))
            c.execute("INSERT INTO prices (product_id, price) VALUES (?, ?)", (product_id, price))
            new_price_id = c.lastrowid
            conn.commit()
            
            # --- EVALUATE ALERTS ---
            if product['alert_email']:
                c.execute("SELECT price FROM prices WHERE product_id = ? ORDER BY timestamp DESC LIMIT 2", (product_id,))
                recent = c.fetchall()
                prev_price = recent[1]['price'] if len(recent) > 1 else None
                
                send_email = False
                subject = f"Price Alert: {product_name}"
                body = f"<h2>Price Update for {product_name}</h2>"
                
                threshold = product['alert_threshold']
                if threshold and price <= threshold:
                    if prev_price is None or price < prev_price:
                        send_email = True
                        body += f"<p>🔥 The price has dropped to <b>${price:.2f}</b>, which is below your target of ${threshold:.2f}!</p>"
                
                if product['alert_lowest_30d']:
                    c.execute("SELECT MIN(price) as min_p FROM prices WHERE product_id = ? AND id != ? AND timestamp >= datetime('now', '-30 days')", (product_id, new_price_id))
                    min_30d = c.fetchone()['min_p']
                    
                    if min_30d is not None and price < min_30d:
                        send_email = True
                        subject = f"30-Day Low! {product_name}"
                        body += f"<p>📉 This is the lowest price seen in 30 days! (Previous low was ${min_30d:.2f}).</p>"
                
                if send_email:
                    body += f"<br><p><a href='{product['url']}'>Click here to view the product page</a></p>"
                    send_alert_email(product['alert_email'], subject, body)

        else:
            c.execute("UPDATE products SET last_status = 'failed', last_error = 'Price selector not found on page' WHERE id = ?", (product_id,))
            conn.commit()
            
    except Exception as e:
        c.execute("UPDATE products SET last_status = 'failed', last_error = ? WHERE id = ?", (str(e), product_id))
        conn.commit()
    finally:
        scraper.close()
        conn.close()

# --- API Routes ---

@app.get("/")
def serve_ui():
    return FileResponse("index.html")

@app.get("/api/products")
def get_products():
    conn = get_db_connection()
    products = conn.execute('''
        SELECT p.*, 
               (SELECT price FROM prices WHERE product_id = p.id ORDER BY timestamp DESC LIMIT 1) as latest_price,
               (SELECT timestamp FROM prices WHERE product_id = p.id ORDER BY timestamp DESC LIMIT 1) as last_checked
        FROM products p
        ORDER BY p.id DESC
    ''').fetchall()
    conn.close()
    return [dict(p) for p in products]

@app.post("/api/track")
def track_new_product(req: TrackRequest, background_tasks: BackgroundTasks):
    conn = get_db_connection()
    c = conn.cursor()
    extracted = tldextract.extract(req.url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    
    try:
        c.execute('''
            INSERT INTO products (name, url, domain, name_selector, price_selector, last_status, alert_email, alert_threshold, alert_lowest_30d) 
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?)
        ''', ("Pending Scrape...", req.url, domain, req.name_selector, req.price_selector, req.alert_email, req.alert_threshold, req.alert_lowest_30d))
        product_id = c.lastrowid
        conn.commit()
        background_tasks.add_task(scrape_product, product_id)
        return {"status": "success", "message": "Tracking started"}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="URL is already being tracked")
    finally:
        conn.close()

@app.get("/api/products/{product_id}/history")
def get_product_history(product_id: int):
    conn = get_db_connection()
    history = conn.execute("SELECT price, timestamp FROM prices WHERE product_id = ? ORDER BY timestamp ASC", (product_id,)).fetchall()
    conn.close()
    return [dict(h) for h in history]

@app.post("/api/products/{product_id}/scrape")
def force_scrape(product_id: int, background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_product, product_id)
    return {"status": "success"}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, req: UpdateRequest):
    conn = get_db_connection()
    c = conn.cursor()
    extracted = tldextract.extract(req.url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    
    c.execute('''
        UPDATE products SET url = ?, domain = ?, name_selector = ?, price_selector = ?, alert_email = ?, alert_threshold = ?, alert_lowest_30d = ?
        WHERE id = ?
    ''', (req.url, domain, req.name_selector, req.price_selector, req.alert_email, req.alert_threshold, req.alert_lowest_30d, product_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int):
    conn = get_db_connection()
    conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/test-email")
def test_email(req: TestEmailRequest):
    success = send_alert_email(req.email, "Test Alert from Stealth Price Tracker", "<h1>It Works!</h1><p>Your SMTP configuration is working perfectly.</p>")
    if success:
        return {"status": "success", "message": "Test email sent!"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Check terminal logs.")
