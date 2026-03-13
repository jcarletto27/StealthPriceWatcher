import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from rate_limiter import DomainRateLimiter

class StealthScraper:
    def __init__(self):
        # Initialize our 2 requests/min rate limiter
        self.limiter = DomainRateLimiter(max_requests=2, period_seconds=60)
        
        # Setup Undetected ChromeDriver
        options = uc.ChromeOptions()
        options.add_argument('--headless') # Run in the background without a GUI
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--no-sandbox') # CRITICAL for Linux servers to prevent crashes
        options.add_argument('--disable-dev-shm-usage') # CRITICAL to prevent memory limits
        
        # Force a normal desktop monitor size (Headless defaults to a tiny, bot-like window)
        options.add_argument('--window-size=1920,1080')
        # Spoof a real Windows machine User-Agent
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        
        print("Starting Stealth Browser...")
        
        # Point directly to the Chromium binary we just installed via apt
        self.driver = uc.Chrome(
            options=options, 
            browser_executable_path='/usr/bin/chromium',
            version_main=145 # Locked to match Debian's repository version
        )

    def fetch_page(self, url):
        self.limiter.wait_if_needed(url)
        print(f"Fetching: {url}")
        self.driver.get(url)
        
        page_title = self.driver.title
        print(f"➔ LANDED ON PAGE TITLE: {page_title}")
        
        return BeautifulSoup(self.driver.page_source, 'html.parser')

    def take_screenshot(self, filepath):
        try:
            self.driver.save_screenshot(filepath)
            print(f"Screenshot saved to {filepath}")
        except Exception as e:
            print(f"Failed to take screenshot: {e}")

    def close(self):
        # Always quit the driver to prevent zombie Chrome processes from eating your RAM
        self.driver.quit()
