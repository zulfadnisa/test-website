import requests
import os

# === KONFIGURASI ===
URLS = [
    "https://bappeda.cirebonkab.go.id/",
    "https://distan.cirebonkab.go.id/",
    "https://dev.kab.cirebonkab.go.id/",
    "https://adik.cirebonkab.go.id/",
    "https://socakaton.cirebonkab.go.id"
]

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Gagal kirim notifikasi: {e}")

def check_websites():
    for url in URLS:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                send_telegram(f"⚠️ Website DOWN: {url} (Status {response.status_code})")
        except Exception as e:
            send_telegram(f"🚨 Gagal akses {url}: {e}")

check_websites()

