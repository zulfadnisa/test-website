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

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FILENAME = "urls.txt"
# FILENAME = "testing.txt"
HEADERS = {
    "User-Agent": 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",  # Do Not Track
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

# Setup logging to file
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === FUNCTION ===
def load_urls_from_file():
    urls = []
    with open(FILENAME, "r") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
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

async def try_request_async(url, session):
    base_url = url.replace("http://", "").replace("https://", "")
    schemes = ["https://", "http://"]
    
    for scheme in schemes:
        full_url = scheme + base_url
        for attempt in range(2):  # Retry sekali per scheme
            timeout = aiohttp.ClientTimeout(total=30 if attempt == 0 else 45)  # Timeout lebih panjang
            try:
                async with session.get(full_url, headers=get_random_headers(), timeout=timeout) as response:
                    text = await response.text()
                    
                    # Handle 403/468 dengan cloudscraper
                    if response.status in [403, 468]:
                        if "safeline" in text.lower() or "cloudflare" in text.lower():
                            scraper = cloudscraper.create_scraper()
                            logging.warning(f"⚠️  Using cloudscraper for {full_url}")
                            sync_response = scraper.get(full_url, timeout=timeout.total)
                            return sync_response
                    return response
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logging.error(f"Attempt {attempt + 1} failed for {full_url}: {str(e)}. Retrying...")
                continue  # Retry sekali
            except aiohttp.ClientSSLError as ssl_error:
                logging.error(f"SSL error on {full_url}: {str(ssl_error)}")
                break  # Langsung skip ke scheme berikutnya
            except Exception as e:
                logging.error(f"Unexpected error on {full_url}: {str(e)}")
                raise

    raise ConnectionError(f"Failed after retries: {url}")

async def check_single_website(url, session):
    try:
        response = await try_request_async(url, session)
        
        if isinstance(response, cloudscraper.CloudScraper):
            status_code = response.status_code
            text = response.text
        else:
            status_code = response.status
            text = await response.text()
        
        if 200 <= status_code < 400:
            return ("success", url, None)
        elif status_code in [403, 468]:
            if "safeline" in text.lower():
                return ("bot_block", url, f"Blocked by Safeline ({status_code})")
            elif "cloudflare" in text.lower():
                return ("bot_block", url, f"Blocked by Cloudflare ({status_code})")
            else:
                return ("error", url, f"Access denied ({status_code})")
        else:
            return ("error", url, f"HTTP {status_code}")
    except requests.exceptions.Timeout:
        return ("timeout", url, "Timeout")
    except ConnectionError as e:
        msg = str(e).lower()
        if "name or service not known" in msg or "temporary failure in name resolution" in msg or "nodename nor servname" in msg or "dns" in msg:
            return ("dns_error", url, "DNS Lookup Failed")
        elif "ssl" in msg:
            return ("ssl_error", url, "SSL Certificate Error (from conn error)")
        else:
            return ("conn_error", url, f"Connection Error: ({type(e).__name__})")
    except SSLError:
        return ("ssl_error", url, "SSL Certificate Error")
    # except requests.exceptions.TooManyRedirects:
    #     return ("redirect_error", url, "Terlalu banyak redirect")
    except Exception as e:
        return ("other_error", url, f"Gagal Akses ({type(e).__name__})")

async def check_websites_async(urls):
    counters = {
        "success": 0,
        "bot_block": 0,
        "timeout": 0,
        "conn_error": 0,
        "ssl_error":0,
        "dns_error":0,
        "error": 0,
        "redirect_error": 0,
        "other_error": 0
    }
    results = []
    
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [check_single_website(url, session) for url in urls]
        
        for future in asyncio.as_completed(tasks):
            status, url, msg = await future
            counters[status] += 1
            if status != "success":
                results.append(f"{url} - {msg}")
    
    return results, counters

def create_report(duration,total_urls,counters,results):
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    header = (
    f"📡 Website Monitor Report: {timestamp}\n"
    f"⏱️ Running time: {duration:.2f} detik\n\n"
    f"✅ Status: {counters['success']}/{total_urls} aktif\n"
    f"❌ Masalah: {total_urls - counters['success']} tidak aktif\n"
    f"  - Timeout: {counters['timeout']}\n"
    f"  - Koneksi Error: {counters['conn_error']}\n"
    f"  - Bot Block: {counters['bot_block']}\n"
    f"  - SSL Error: {counters['ssl_error']}\n"
    f"  - DNS Error: {counters['dns_error']}\n"
    # f"  - Redirect Error: {counters['redirect_error']}\n"
    f"  - Error Lain: {counters['other_error'] + counters['error']}\n"
    )
    send_telegram(f"{header}\n Detail report akan dikirim sebagai file log.")
    send_telegram_file(results)



async def main():
    if TELEGRAM_TOKEN is None or CHAT_ID is None:
        logging.error(f"TELEGRAM_TOKEN ({TELEGRAM_TOKEN}) atau CHAT_ID({CHAT_ID}) tidak ditemukan.")
        return
    
    start_time = time.time()
    urls = load_urls_from_file()
    # results, counters = check_websites_parallel(urls)
    results, counters = await check_websites_async(urls)
    duration = time.time() - start_time
    create_report(duration, len(urls), counters, results)

# === RUN CODE ===
if __name__ == "__main__":
    asyncio.run(main())

