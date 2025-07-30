from requests.exceptions import SSLError
import cloudscraper
import requests
import os
import random
import logging
import aiohttp
import asyncio
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Tuple, Dict, Optional

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FILENAME = "urls.txt"
# FILENAME = "urls50.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Cache-Control": "no-cache"
}
USER_AGENTS = [
    # Chrome – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",

    # Firefox – Windows
    "Mozilla/5.0 (Windows NT 10.0; rv:102.0) Gecko/20100101 Firefox/102.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0",

    # Safari – macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",

    # Chrome – Android
    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Mobile Safari/537.36",

    # Safari – iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1"

    # Edge – Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.110 Safari/537.36 Edg/115.0.1901.188",
]
MAX_CONCURRENT_REQUESTS = 5  # Sesuaikan dengan kapasitas server target!
LOG_NAME = '📝 Log Error Lengkap'
LOG_FILENAME = 'log.txt'
BATCH_SIZE = 100  # Process URLs in batches to reduce memory pressure
MAX_RETRIES = 2  # Increased from 2
BASE_TIMEOUT = 30  # Base timeout in seconds

# Enhanced logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)

# === FUNCTION ===
def load_urls_from_file():
    urls = []

    if not os.path.exists(FILENAME):
        logging.error(f"File {FILENAME} not found")
        return urls

    with open(FILENAME, "r") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
            # if not url.startswith(('http://', 'https://')):
            #     url = f"https://{url}"
            urls.append(url)
    return urls

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        logging.info(f"Notifikasi berhasil dikirim dengan status code {response.status_code} dan text {response.text}")
    except Exception as e:
        logging.error(f"Gagal mengirim notifikasi ke Telegram: {e}")

def send_telegram_file(results):
    with open(LOG_FILENAME, "w", encoding="utf-8") as f:
        f.write("\n".join(results))

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(LOG_FILENAME, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': CHAT_ID, 'caption': LOG_NAME}
        requests.post(url, data=data, files=files)
    if os.path.exists(LOG_FILENAME):
        os.remove(LOG_FILENAME)

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
        "Cookie": "session=test; botcheck=pass"
    }

# === CORE MONITORING FUNCTIONS ===
async def try_request_async(url: str, session: aiohttp.ClientSession):
    """Make an async request with retry logic"""
    base_url = url.replace("http://", "").replace("https://", "")
    schemes = ["https://", "http://"]  # Try HTTPS first
    last_error = None
    
    for scheme in schemes:
        full_url = scheme + base_url
        
        for attempt in range(MAX_RETRIES):
            timeout = BASE_TIMEOUT * (attempt + 1)  # Exponential timeout
            
            try:
                logging.debug(f"Checking {url} (attempt {attempt + 1})")
                
                async with session.get(
                    full_url,
                    headers=get_random_headers(),
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    text = await response.text()
                    
                    # Handle security protections
                    if response.status in [403, 468]:
                        if any(s in text.lower() for s in ['cloudflare', 'safeline', 'ddos']):
                            logging.info(f"Security protection detected on {url}, using fallback")
                            try:
                                # Run cloudscraper in a separate thread
                                sync_response = await asyncio.to_thread(
                                    cloudscraper.create_scraper().get,
                                    full_url,
                                    timeout=timeout
                                )
                                return (
                                    "success" if sync_response.ok else "bot_block",
                                    url,
                                    f"Protected ({sync_response.status_code})"
                                )
                            except Exception as e:
                                logging.warning(f"Fallback failed for {url}: {str(e)}")
                                last_error = f"fallback_failed: {str(e)}"
                                continue
                    
                    if 200 <= response.status < 400:
                        return ("success", url, None)
                    return ("error", url, f"HTTP {response.status}")
                    
            except (aiohttp.ClientSSLError, SSLError) as e:
                last_error = f"ssl_error: {str(e)}"
                continue  # Try next scheme
            except asyncio.TimeoutError as e:
                last_error = f"timeout: {str(e)}"
                await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff
                continue
            except aiohttp.ClientError as e:
                last_error = f"client_error: {str(e)}"
                await asyncio.sleep(1 * (attempt + 1))
                continue
            except Exception as e:
                last_error = f"unexpected_error: {str(e)}"
                logging.error(f"Unexpected error checking {url}: {str(e)}")
                break
    
    # Determine final error status
    error_type = last_error.split(':')[0] if last_error else "unknown_error"
    return (error_type, url, last_error or "Unknown error")

async def check_single_website(url: str, session: aiohttp.ClientSession):
    """Check a single website's availability"""
    try:
        status, checked_url, message = await try_request_async(url, session)
        
        # Additional error classification
        if status == "conn_error" and message:
            if "name or service not known" in message.lower() or "dns" in message.lower():
                status = "dns_error"
        
        return (status, checked_url, message)
    
    except asyncio.TimeoutError:
        return ("timeout", url, "Request timed out")
    except aiohttp.ClientSSLError:
        return ("ssl_error", url, "SSL certificate error")
    except aiohttp.ClientConnectionError:
        return ("conn_error", url, "Connection failed")
    except Exception as e:
        logging.error(f"Unexpected error checking {url}: {str(e)}")
        return ("error", url, f"Unexpected error: {str(e)}")

async def process_batch(batch: List[str], session: aiohttp.ClientSession):
    """Process a batch of URLs"""
    counters = {
        "success": 0,
        "error": 0,
        "timeout": 0,
        "bot_block": 0,
        "ssl_error": 0,
        "dns_error": 0,
        "conn_error": 0,
        # "unknown_error":0,
        # "client_error":0,
        # "unexpected_error":0
    }
    results = []
    
    tasks = [check_single_website(url, session) for url in batch]
    
    for future in asyncio.as_completed(tasks):
        try:
            status, url, msg = await future
            counters[status] += 1
            if status != "success":
                results.append(f"{url} - {msg}")
        except Exception as e:
            logging.error(f"Error processing URL: {str(e)}")
            counters["error"] += 1
            results.append(f"UNKNOWN - Processing error: {str(e)}")
    
    return counters, results

async def check_websites_async(urls: List[str]):
    """Main website checking function with batch processing"""
    total_counters = {k: 0 for k in [
        "success", "error", "timeout", "bot_block", 
        "ssl_error", "dns_error", "conn_error"
    ]}
    all_results = []
    
    connector = aiohttp.TCPConnector(
        limit=MAX_CONCURRENT_REQUESTS,
        force_close=False,
        enable_cleanup_closed=True,
        ssl=False
    )
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # Process in batches to reduce memory usage
        for i in range(0, len(urls), BATCH_SIZE):
            batch = urls[i:i + BATCH_SIZE]
            logging.info(f"Processing batch {i//BATCH_SIZE + 1}/{(len(urls)-1)//BATCH_SIZE + 1}")
            
            batch_counters, batch_results = await process_batch(batch, session)
            all_results.extend(batch_results)
            
            # Update totals
            for k in total_counters:
                total_counters[k] += batch_counters.get(k, 0)
            
            # Brief pause between batches
            await asyncio.sleep(1)
    
    return total_counters, all_results

def create_report(duration: float, total_urls: int, counters: Dict[str, int], results: List[str]):
    """Generate and send monitoring report"""
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    
    # Create summary message with Markdown formatting
    summary = (
        f"🚀 Website Monitoring Report\n"
        f"Date: {now:%Y-%m-%d %H:%M:%S}\n\n"
        f"• Total URLs Checked: {total_urls}\n"
        f"• Time Elapsed: {duration:.2f} seconds\n"
        f"• Success Rate: {counters['success']/total_urls:.1%}\n\n"
        f"Status Breakdown:\n"
        f"✅ Success: {counters['success']}\n"
        f"⏱️ Timeout: {counters['timeout']}\n"
        f"🔒 Blocked: {counters['bot_block']}\n"
        f"🔐 SSL Errors: {counters['ssl_error']}\n"
        f"🌐 DNS Errors: {counters['dns_error']}\n"
        f"🔌 Connection Errors: {counters['conn_error']}\n"
        f"❓ Other Errors: {counters['error']}\n\n"
        f"_Detailed error log is attached_"
    )
    
    # Send summary
    if not send_telegram(summary):
        logging.error("Failed to send summary report")
    
    # Send detailed log if there were errors
    if results and not send_telegram_file(results):
        logging.error("Failed to send detailed error log")

# === MAIN EXECUTION ===
async def main():
    """Main execution function"""
    logging.info("Starting website monitoring")
    
    # Validate environment
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logging.error("Missing Telegram credentials (TELEGRAM_TOKEN or CHAT_ID)")
        return
    
    # Load URLs
    try:
        start_time = time.time()
        urls = load_urls_from_file()
        
        if not urls:
            logging.error("No URLs found to check")
            send_telegram("⚠️ No URLs found to monitor. Check your urls.txt file.")
            return
        
        logging.info(f"Loaded {len(urls)} URLs for monitoring")
        
        # Run monitoring
        counters, results = await check_websites_async(urls)
        duration = time.time() - start_time
        
        # Generate report
        create_report(duration, len(urls), counters, results)
        logging.info(f"Monitoring completed in {duration:.2f} seconds")
    
    except Exception as e:
        error_msg = f"🔥 Monitoring failed: {str(e)}"
        logging.error(error_msg)
        send_telegram(error_msg)

if __name__ == "__main__":
    asyncio.run(main())
