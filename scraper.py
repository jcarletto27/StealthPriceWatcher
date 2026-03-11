# scraper.py
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from rate_limiter import DomainRateLimiter

class StealthScraper:
    def __init__(self):
        self.limiter = DomainRateLimiter(max_requests=2, period_seconds=60)
        
        options = uc.ChromeOptions()
        options.add_argument('--headless') 
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--no-sandbox') 
        options.add_argument('--disable-dev-shm-usage')
        
        # --- NEW STEALTH TWEAKS ---
        # 1. Force a normal desktop monitor size (Headless defaults to a tiny, bot-like window)
        options.add_argument('--window-size=1920,1080')
        # 2. Spoof a real Windows machine User-Agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        print("Starting Stealth Browser...")
        
        self.driver = uc.Chrome(
            options=options, 
            browser_executable_path='/usr/bin/chromium',
            version_main=145
        )

    def fetch_page(self, url):
        self.limiter.wait_if_needed(url)
        print(f"Fetching: {url}")
        self.driver.get(url)
        
        # --- NEW DEBUGGING LOG ---
        # Print the title of the page to the terminal so we know if we got blocked
        page_title = self.driver.title
        print(f"➔ LANDED ON PAGE TITLE: {page_title}")
        
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    def close(self):
        self.driver.quit()
