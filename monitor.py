import os
import requests
from datetime import datetime

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
FILENAME = "urls.txt"

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
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            status_code = response.status_code

            if status_code != 200:
                results.append(f"⚠️ {url} - Gagal Akses ({status_code})")
        except requests.exceptions.Timeout:
            results.append(f"❌ {url} - DOWN (Timeout)")
        except requests.exceptions.ConnectionError:
            results.append(f"❌ {url} - DOWN (Connection Error)")
        except requests.exceptions.TooManyRedirects:
            results.append(f"⚠️ {url} - Gagal Akses (Terlalu banyak redirect)")
        except requests.exceptions.RequestException as e:
            results.append(f"⚠️ {url} - Gagal Akses ({type(e).__name__})")

    if len(results) == 0:
        results.append("✅ Semua URL Berjalan/OK (200)")
    return results

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
 
    urls = load_urls_from_file()
    results = check_websites(urls)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    message = f"🌐 Website Monitoring Result\n🕒 {timestamp}\n\n" + "\n".join(results)
    send_telegram(message)


if __name__ == "__main__":
    main()

