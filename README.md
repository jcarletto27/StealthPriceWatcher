# Stealth Price Tracker

A robust, self-hosted web application for tracking product prices across various e-commerce platforms. Built with Python, FastAPI, and Undetected ChromeDriver to bypass basic anti-bot protections.

## Overview

Unlike standard web scrapers that fail when encountering Cloudflare or Amazon's bot-detection, this tracker uses a fully configured headless Chromium browser to simulate real user traffic. It allows you to track prices on virtually any website using universal CSS selectors, view historical price trends, and receive automated email alerts when a price drops.

## Features


- **Universal Tracking:** Track items on any website by providing custom CSS selectors for the product name and price.


- **Stealth Engine:** Utilizes `undetected-chromedriver` to bypass automated bot checks and CAPTCHAs.


- **Domain Rate Limiting:** Built-in sliding window rate limiter prevents your server from hammering target websites (defaulted to 2 requests per minute per domain) to avoid IP bans.


- **Email Alerts:** Secure SMTP integration to notify you when a product drops below your target price or hits a 30-day low.


- **Historical Data:** SQLite database tracks price changes over time, visualized via an interactive Chart.js dashboard.


- **Modern UI:** Responsive frontend built with Tailwind CSS, featuring a built-in dark mode and slide-out product configuration panels.



## Prerequisites


- Docker


- Docker Compose



## Installation


1. **Clone the repository:**

```
git clone https://github.com/jcarletto27/StealthPriceWatcher.git
cd stealth-price-tracker   

```


1. **Initialize the database file:** Docker requires the database file to exist on the host machine before mounting it, otherwise it will create a directory instead.

```
touch tracker.db   

```


1. **Configure Environment Variables:** Create a `.env` file in the root directory to configure your SMTP email settings for alerts.

```
# .env
SMTP_SERVER=mail.yourdomain.com
SMTP_PORT=465
SMTP_USER=alerts@yourdomain.com
SMTP_PASS=your_secure_password   

```


1. **Build and start the container:**

```
docker compose up -d --build   

```



The application will now be running at `http://localhost:8821` (or your server's local IP address on port 8821).

## Usage Guide

### Tracking a New Product


1. Navigate to the web dashboard.


1. Paste the **Target URL** of the product.


1. Provide the **Name Selector**. This is the CSS selector for the HTML element containing the product title (e.g., `h1` or `.product-title`).


1. Provide the **Price Selector**. This is the CSS selector for the HTML element containing the price (e.g., `.price-value` or `.a-price-whole`).


1. (Optional) Set a target price threshold and an alert email to receive notifications.



### Finding CSS Selectors

To track a new site, you need to find the correct CSS selectors:


1. Open the product page in Google Chrome.


1. Right-click the price text and select **Inspect**.


1. In the Elements panel, look at the highlighted HTML tag.


1. If the tag is `<span class="price-display">$49.99</span>`, your selector is `.price-display`.


1. For complex sites like Amazon, use specific classes like `.a-price-whole`.



## Architecture


- **Backend:** Python 3.12, FastAPI, Uvicorn


- **Scraper:** Undetected-ChromeDriver, BeautifulSoup4


- **Database:** SQLite


- **Frontend:** HTML5, Tailwind CSS, Chart.js


- **Containerization:** Docker (Debian Slim with native Chromium)
