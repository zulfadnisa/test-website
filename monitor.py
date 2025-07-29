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
# FILENAME = "testing.txt"
FILENAME = "urls.txt"
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
MAX_WORKERS = 6

# === FUNCTION ===
def load_urls_from_file():
    urls = []
    with open(FILENAME, "r") as file:
        for line in file:
            url = line.strip()
            if not url:
                continue
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
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
        "Cookie": "session=test; botcheck=pass"
    }

def try_request(url):
    # delay = 2
    retries = 1
    timeouts = [10, 15]


    for attempt in range(retries + 1):
        try:
            timeout = timeouts[min(attempt, len(timeouts)-1)]
            response = requests.get(url, headers=get_random_headers(), timeout=timeout) #30 detik kalau di uptimerobot
            if response.status_code in [403, 468]:
                time.sleep(1)
                scraper = cloudscraper.create_scraper()
                response = scraper.get(url, timeout=timeout)
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < retries:
                time.sleep(1)
                continue
            else:
                raise

def check_single_website(url):
    try:
        response = try_request(url)
        status_code = response.status_code

        if 200 <= status_code < 400:
            return ("success", url, None)
        elif status_code == 403 or status_code == 468:
            # print(f"ERROR {url} STATUS CODE {status_code}")

            if "cloudflare" in response.text.lower() or "access denied" in response.text.lower():
                return ("bot_block", url, f"Bot-blocked ({status_code})")
            elif "safeline" in response.text.lower() or "/.safeline/" in response.text.lower():
                return ("bot_block", url, f"Bot-blocked ({status_code} / SafeLine)")
            else:
                return ("error", url, f"Akses ditolak ({status_code})")
        else:
            # print(f"ERROR {url} STATUS CODE: {status_code} TEXT: {response.text.lower()}")
            return ("error", url, f"Error ({status_code})")
    except requests.exceptions.Timeout:
        return ("timeout", url, "Timeout")
    except requests.exceptions.ConnectionError as e:
        # print(f"EXCEPT ConnectionERrror {url} TEXT: {response.text.lower()}")
        msg = str(e).lower()
        if "name or service not known" in msg or "temporary failure in name resolution" in msg or "nodename nor servname" in msg or "dns" in msg:
            return ("dns_error", url, "DNS Lookup Failed")
        elif "ssl" in msg:
            return ("ssl_error", url, "SSL Certificate Error (from conn error)")
        else:
            return ("conn_error", url, "Connection Error")
    except SSLError:
        return ("ssl_error", url, "SSL Certificate Error")
    except requests.exceptions.TooManyRedirects:
        return ("redirect_error", url, "Terlalu banyak redirect")
    except requests.exceptions.RequestException as e:
        # print(f"EXCEPT {url} TEXT: {response.text.lower()}")
        return ("other_error", url, f"Gagal Akses ({type(e).__name__})")

def check_websites_parallel(urls):
    results = []
    counters = {
        "success": 0,
        "timeout": 0,
        "conn_error": 0,
        "bot_block": 0,
        "error": 0,
        "ssl_error":0,
        "dns_error":0,
        "redirect_error": 0,
        "other_error": 0
    }

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(check_single_website, url): url for url in urls}

        for future in as_completed(future_to_url):
            status, url, message = future.result()
            counters[status] += 1
            if status != "success":
                icon = {'timeout': '⏰',
                        'conn_error': '❓',
                        'redirect_error': '⚠️',
                        'other_error': '⚠️'
                        }.get(status, '❌')
                results.append(f"{icon} {url} - {message}")

    return results, counters

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("✅ Notifikasi berhasil dikirim.", response.status_code, response.text)
    except Exception as e:
        print(f"❌ Gagal mengirim notifikasi ke Telegram: {e}")

def send_telegram_file(filename, caption="Log"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    with open(filename, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': CHAT_ID, 'caption': caption}
        requests.post(url, data=data, files=files)

def create_report(duration,total_urls,counters,results):
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"📡 Website Monitor\n"
        f"📅 {timestamp}\n"
        f"⏱️ Durasi: {duration:.2f} detik\n\n"
        f"✅ Aktif: {counters['success']}/{total_urls}\n"
        f"❌ Bermasalah: {total_urls - counters['success']}\n"
        f"  ⏰ Timeout: {counters['timeout']}\n"
        f"  ❓ ConnError: {counters['conn_error']}\n"
        f"  ⛔ Bot-block: {counters['bot_block']}\n"
        f"  🔁 SSL Error: {counters['ssl_error']}\n"
        f"  🔁 DNS Error: {counters['dns_error']}\n"
        f"  🔁 Redirect: {counters['redirect_error']}\n"
        f"  ⚠️ Error lain: {counters['other_error'] + counters['error']}\n"
    )

    error_count = len(results)  # Jumlah error
    if error_count > 10:
        send_telegram(f"{header}\n⚠️ Terlalu banyak error ({error_count}). Detail dikirim sebagai file log.")

        with open("log.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(results))

        send_telegram_file("log.txt", caption="📝 Log Error Lengkap")
        if os.path.exists("log.txt"):
            os.remove("log.txt")
    else:
        detail = "\n".join(results)
        send_telegram(f"{header}\n{detail}")

def main():
    if TELEGRAM_TOKEN is None or CHAT_ID is None:
        print("❌ TELEGRAM_TOKEN atau CHAT_ID tidak ditemukan.")
        return
    
    start_time = time.time()
    urls = load_urls_from_file()
    total_urls = len(urls)
    results, counters = check_websites_parallel(urls)
    end_time = time.time()
    duration = end_time - start_time

    create_report(duration,total_urls,counters,results)


# === RUN CODE ===
if __name__ == "__main__":
    main()

