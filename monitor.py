import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time
from concurrent.futures import ThreadPoolExecutor, as_completed #pararel

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FILENAME = "urls50.txt"
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
MAX_WORKERS = 8

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

def try_request(url):
    delay = 2
    retries = 1

    for attempt in range(retries + 1):
        timeoutVal = 10 if attempt == 0 else 15
        try:
            response = requests.get(url, headers=HEADERS, timeout=timeoutVal) #30 detik kalau di uptimerobot
            if response.status_code in [403, 503] and attempt < retries:
                time.sleep(delay)
                continue
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < retries:
                time.sleep(delay)
            else:
                raise

def check_single_website(url):
    try:
        response = try_request(url)
        status_code = response.status_code

        if 200 <= status_code < 400:
            return ("success", url, None)
        elif status_code == 403:
            if "cloudflare" in response.text.lower() or "access denied" in response.text.lower():
                return ("bot_block", url, "Bot-blocked (403)")
            else:
                return ("error", url, f"Akses ditolak (403)")
        else:
            return ("error", url, f"Error ({status_code})")
    except requests.exceptions.Timeout:
        return ("timeout", url, "Timeout")
    except requests.exceptions.ConnectionError:
        return ("conn_error", url, "Connection Error")
    except requests.exceptions.TooManyRedirects:
        return ("redirect_error", url, "Terlalu banyak redirect")
    except requests.exceptions.RequestException as e:
        return ("other_error", url, f"Gagal Akses ({type(e).__name__})")

def check_websites_parallel(urls):
    results = []
    counters = {
        "success": 0,
        "timeout": 0,
        "conn_error": 0,
        "bot_block": 0,
        "error": 0,
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

# def check_websites(urls):
#     results = []
#     total_success = 0
#     total_timeout = 0

#     for url in urls:
#         try:
#             response = try_request(url)
#             status_code = response.status_code

#             if 200 <= status_code < 400 :
#                 total_success+=1
#             elif status_code == 403:
#                 if "cloudflare" in response.text.lower() or "access denied" in response.text.lower():
#                     results.append(f"❌ {url} - Bot-blocked (403)")
#                 else:
#                     results.append(f"❌ {url} - Akses ditolak (403)")
#             else:
#                 results.append(f"❌ {url} - Error ({status_code})")
#         except requests.exceptions.Timeout:
#             results.append(f"⏰ {url} - Timeout")
#             total_timeout+=1
#         except requests.exceptions.ConnectionError:
#             results.append(f"❓ {url} - Connection Error")
#         except requests.exceptions.TooManyRedirects:
#             results.append(f"⚠️ {url} - Gagal Akses (Terlalu banyak redirect)")
#         except requests.exceptions.RequestException as e:
#             results.append(f"⚠️ {url} - Gagal Akses ({type(e).__name__})")

#     return results,total_success,total_timeout

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("✅ Notifikasi berhasil dikirim.", response.status_code, response.text)
    except Exception as e:
        print(f"❌ Gagal mengirim notifikasi ke Telegram: {e}")

def main():
    if TELEGRAM_TOKEN is None or CHAT_ID is None:
        print("❌ TELEGRAM_TOKEN atau CHAT_ID tidak ditemukan.")
        return
    
    start_time = time.time()

    urls = load_urls_from_file()
    results, counters = check_websites_parallel(urls)
    end_time = time.time()
    duration = end_time - start_time

    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    header = (
        f"📡 Website Monitor\n"
        f"📅 {timestamp}\n"
        f"⏱️ Durasi: {duration:.2f} detik\n\n"
        f"✅ Aktif: {counters['success']}/{len(urls)}\n"
        f"❌ Bermasalah: {len(urls) - counters['success']}\n"
        f"  ⏰ Timeout: {counters['timeout']}\n"
        f"  ❓ ConnError: {counters['conn_error']}\n"
        f"  ⛔ Bot-block: {counters['bot_block']}\n"
        f"  🔁 Redirect: {counters['redirect_error']}\n"
        f"  ⚠️ Error lain: {counters['other_error'] + counters['error']}\n"
    )

    detail = "\n".join(results)
    message = f"{header}\n{detail[:4000]}"  # Telegram limit
    send_telegram(message)

# === RUN CODE ===
if __name__ == "__main__":
    main()

