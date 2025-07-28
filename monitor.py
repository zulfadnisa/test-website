import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FILENAME = "urls50.txt"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("✅ Notifikasi berhasil dikirim.", response.status_code, response.text)
    except Exception as e:
        print(f"❌ Gagal mengirim notifikasi ke Telegram: {e}")

def check_websites(urls):
    results = []
    total_success = 0

    headers = {
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

    for url in urls:
        try:
            response = requests.get(url,headers=headers, timeout=15) #30 detik kalau di uptimerobot
            status_code = response.status_code

            if 200 <= status_code < 400 :
                total_success+=1
            elif status_code == 403:
                if "cloudflare" in response.text.lower():
                    results.append(f"❌ {url} - Bot-blocked (403)")
                else:
                    results.append(f"❌ {url} - Akses ditolak (403)")
            else:
                results.append(f"❌ {url} - Error ({status_code})")
        except requests.exceptions.Timeout:
            results.append(f"❓ {url} - Timeout")
        except requests.exceptions.ConnectionError:
            results.append(f"❓ {url} - Connection Error")
        except requests.exceptions.TooManyRedirects:
            results.append(f"⚠️ {url} - Gagal Akses (Terlalu banyak redirect)")
        except requests.exceptions.RequestException as e:
            results.append(f"⚠️ {url} - Gagal Akses ({type(e).__name__})")

    return results,total_success

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

def main():
    if TELEGRAM_TOKEN is None or CHAT_ID is None:
        print("❌ TELEGRAM_TOKEN atau CHAT_ID tidak ditemukan.")
        return
    
    start_time = time.time()

    urls = load_urls_from_file()
    total_url = len(urls)

    results,total_success = check_websites(urls)
    result_msg = "\n".join(results)
    if len(results) == 0 and total_success == len(urls):
        result_msg = "\n ✅ Semua URL Berjalan/OK (200)"    

    end_time = time.time()
    duration = end_time - start_time
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    message = f"🌐 Website Monitoring Result\n🕒 {timestamp}\n" + f"⏱️ Durasi: {duration:.2f} detik\n"+f"Success: {total_success}/{total_url}\n\n" + result_msg
    send_telegram(message)


if __name__ == "__main__":
    main()

