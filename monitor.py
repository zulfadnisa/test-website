import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import time

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
# URLS = [
#     "https://bappeda.cirebonkab.go.id/",
#     "https://distan.cirebonkab.go.id/",
#     "https://dev.kab.cirebonkab.go.id/",
#     "https://adik.cirebonkab.go.id/",
#     "https://socakaton.cirebonkab.go.id"
# ]
FILENAME = "urls10.txt"

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

    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            status_code = response.status_code

            if status_code == 200 :
                total_success+=1
            else:
                results.append(f"⚠️ {url} - Gagal Akses ({status_code})")
        except requests.exceptions.Timeout:
            results.append(f"❌ {url} - DOWN (Timeout)")
        except requests.exceptions.ConnectionError:
            results.append(f"❌ {url} - DOWN (Connection Error)")
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
    print('TESTING TOTAL URL:', total_url)

    results,total_success = check_websites(urls)
    now = datetime.now(ZoneInfo("Asia/Jakarta"))
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    result_msg = "\n".join(results)
    if len(results) == 0 and total_success == len(urls):
        result_msg = "\n ✅ Semua URL Berjalan/OK (200)"
    
    end_time = time.time()
    duration = end_time - start_time

    message = f"🌐 Website Monitoring Result\n🕒 {timestamp}\n" + f"⏱️ Durasi: {duration:.2f} detik\n"+f"\n Success: {total_success}/{total_url}\n\n" + result_msg

    print('TESTING TOTAL SUCCESS:', total_success)
    print('TESTING TOTAL ERROR:', len(results))
    print('TESTING DURATION:', duration)
    send_telegram(message)


if __name__ == "__main__":
    main()

