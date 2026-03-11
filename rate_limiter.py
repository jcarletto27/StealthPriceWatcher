import time
import tldextract
from collections import deque

# GLOBAL memory so it persists across different scraper instances and background jobs
GLOBAL_DOMAIN_HISTORY = {}

class DomainRateLimiter:
    def __init__(self, max_requests=2, period_seconds=60):
        self.max_requests = max_requests
        self.period = period_seconds

    def wait_if_needed(self, url):
        # Extract the root domain (e.g., 'amazon.com')
        extracted = tldextract.extract(url)
        domain = f"{extracted.domain}.{extracted.suffix}"

        if domain not in GLOBAL_DOMAIN_HISTORY:
            GLOBAL_DOMAIN_HISTORY[domain] = deque(maxlen=self.max_requests)

        history = GLOBAL_DOMAIN_HISTORY[domain]

        # If we have hit our max request limit for this domain...
        if len(history) == self.max_requests:
            elapsed_time = time.time() - history[0]
            
            # If the oldest request was made within our 60 second window, we must wait
            if elapsed_time < self.period:
                sleep_time = self.period - elapsed_time
                print(f"[Rate Limiter] {domain} limit reached. Sleeping for {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)

        # Record the timestamp of the new request
        history.append(time.time())
