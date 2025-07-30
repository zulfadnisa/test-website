import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from concurrent.futures import ThreadPoolExecutor, as_completed #pararel
import random
from requests.exceptions import SSLError
import cloudscraper

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FILENAME = "urls400.txt"
# FILENAME = "urls200.txt"
LOG_FILENAME = "log.txt"
MAX_WORKERS = 10  # Increased from 6 to 10 for better parallelism
MIN_DELAY = 0.5  # Minimum delay between requests in seconds
MAX_DELAY = 2.0  # Maximum delay between requests in seconds

# Enhanced User Agents list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Vivaldi/6.1.3035.111"
]

# === FUNCTION ===
def load_urls_from_file():
    urls = []
    with open(FILENAME, "r") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
            # if not url.startswith("http://") and not url.startswith("https://"):
            #     url = "https://" + url
            urls.append(url)
    return urls

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS), #biar ga dianggap bot/spam oleh server
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Upgrade-Insecure-Requests": "1",
        "Connection": "keep-alive",
        "DNT": "1",  # Do Not Track
        "Cache-Control": "no-cache",
        "Referer": "https://www.google.com/",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cookie": "session=test; botcheck=pass",
        "Accept-Encoding": "gzip, deflate",
    }

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        print("✅ Notifikasi berhasil dikirim.", response.status_code, response.text)
    except Exception as e:
        print(f"⚠️ Failed to send Telegram notification: {e}")

def send_telegram_file(filename, caption="Log"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    try:
        with open(filename, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CHAT_ID, 'caption': caption}
            requests.post(url, data=data, files=files, timeout=15)
    except Exception as e:
        print(f"⚠️ Failed to send file via Telegram: {e}")

# === CORE MONITORING FUNCTIONS ===
def try_request(url):
    """Attempt to request a URL with retry logic and cloudscraper fallback"""
    base_url = url.replace("http://", "").replace("https://", "")
    schemes = ["https://", "http://"]
    timeout = 10  # Increased base timeout
    
    for scheme in schemes:
        try:
            # Initial request with random delay
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
            
            # First attempt with requests
            response = requests.get(
                scheme + base_url, 
                headers=get_random_headers(),
                timeout=timeout,
                allow_redirects=True
            )
            # If blocked, try with cloudscraper
            if response.status_code in [403, 429, 468]:
                time.sleep(random.uniform(1, 3))  # Longer delay for retry
                scraper = cloudscraper.create_scraper()
                response = scraper.get(
                    scheme + base_url,
                    timeout=timeout,
                    headers=get_random_headers()
                )
                
            return response
            
        except requests.exceptions.RequestException:
            continue        
    raise requests.exceptions.ConnectionError(f"Failed to connect to {url}")

def check_single_website(url):
    try:
        response = try_request(url)
        status_code = response.status_code
        
        if 200 <= status_code < 400:
            return ("success", url, None)
        elif status_code in [403, 468]:
            if any(x in response.text.lower() for x in ["cloudflare", "access denied"]):
                return ("bot_block", url, f"Bot-blocked ({status_code})")
            elif any(x in response.text.lower() for x in ["safeline", "/.safeline/"]):
                return ("bot_block", url, f"SafeLine block ({status_code})")
            else:
                return ("error", url, f"Access denied ({status_code})")
        else:
            return ("error", url, f"HTTP Error ({status_code})")
    except requests.exceptions.Timeout:
        return ("timeout", url, "Timeout")
    except requests.exceptions.SSLError:
        return ("ssl_error", url, "SSL Error")
    except requests.exceptions.ConnectionError as e:
        msg = str(e).lower()
        if any(x in msg for x in ["dns", "name resolution", "nodename"]):
            return ("dns_error", url, "DNS Error")
        else:
            return ("conn_error", url, "Connection Error")
    except Exception as e:
        return ("other_error", url, f"{type(e).__name__}: {str(e)}")

def check_websites_parallel(urls):
    results = []
    counters = {
        "success": 0,
        "timeout": 0,
        "conn_error": 0,
        "bot_block": 0,
        "error": 0,
        "ssl_error": 0,
        "dns_error": 0,
        "redirect_error": 0,
        "other_error": 0
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(check_single_website, url): url for url in urls}
        
        for future in as_completed(futures):
            status, url, message = future.result()
            counters[status] += 1
            if status != "success":
                icons = {
                    'timeout': '⏰',
                    'conn_error': '🔌',
                    'bot_block': '🤖',
                    'ssl_error': '🔒',
                    'dns_error': '🌐',
                    'redirect_error': '🔄',
                    'other_error': '⚠️'
                }
                icon = icons.get(status, '❌')
                results.append(f"{icon} {url} - {message}")
    return results, counters

def create_report(duration,total_urls,counters,results):
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"📡 <b>Website Monitoring Report</b>\n\n"
        f"<i>{timestamp}</i>\n"
        f"<b>Running time:</b> {duration:.2f} seconds\n\n"
        f"<b>Successful:</b> {counters['success']}/{total_urls}\n"
        f"<b>Issues:</b> {total_urls - counters['success']}\n\n"
        f"<b>Details:</b>\n"
        f"  ⏰ Timeout: {counters['timeout']}\n"
        f"  🔌 Connection Error: {counters['conn_error']}\n"
        f"  🤖 Bot Blocked: {counters['bot_block']}\n"
        f"  🔒 SSL Errors: {counters['ssl_error']}\n"
        f"  🌐 DNS Errors: {counters['dns_error']}\n"
        f"  🔄 Redirect Issues: {counters['redirect_error']}\n"
        f"  ⚠️ Other Errors: {counters['other_error'] + counters['error']}\n"
    )

    with open(LOG_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    send_telegram(f"{header} \nSee attached log file.")
    send_telegram_file(LOG_FILENAME)
        
    if os.path.exists(LOG_FILENAME):
        os.remove(LOG_FILENAME)

# === MAIN EXECUTION ===
def main():
    print("🚀 Starting website monitoring...")
    start_time = time.time()

    if TELEGRAM_TOKEN is None or CHAT_ID is None:
        print("❌ TELEGRAM_TOKEN atau CHAT_ID tidak ditemukan.")
        return
        
    try:
        urls = load_urls_from_file()
        print(f"🔗 Loaded {len(urls)} URLs to check")
        
        results, counters = check_websites_parallel(urls)
        duration = time.time() - start_time
        
        print(f"✅ Completed in {duration:.2f} seconds")
        create_report(duration, len(urls), counters, results)
        
    except Exception as e:
        error_msg = f"❌ Critical error in main execution: {str(e)}"
        send_telegram(error_msg)
    

if __name__ == "__main__":
    main()
