# main.py
from db import init_db, insert_price
from scraper import StealthScraper
import re

def extract_price(soup):
    # This is a very basic example. In reality, you need site-specific logic
    # (e.g., looking for <span class="a-price-whole"> for Amazon)
    text = soup.get_text()
    matches = re.findall(r'\$\s*(\d+\.\d{2})', text)
    if matches:
        return float(matches[0])
    return None

def main():
    conn = init_db()
    scraper = StealthScraper()
    
    # Example URLs (both pointing to the same domain to test the rate limiter)
    urls_to_scrape = [
        "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
        "https://books.toscrape.com/catalogue/tipping-the-velvet_999/index.html",
        "https://books.toscrape.com/catalogue/soumission_998/index.html" # This 3rd one will trigger the 60s sleep
    ]
    
    try:
        for url in urls_to_scrape:
            soup = scraper.fetch_page(url)
            price = extract_price(soup)
            
            if price:
                print(f"Found price: ${price}")
                # You would normally look up the product_id from the DB here
                # insert_price(conn, product_id=1, price=price)
            else:
                print("Could not find a price on this page.")
                
    finally:
        scraper.close()
        conn.close()

if __name__ == "__main__":
    main()
    
