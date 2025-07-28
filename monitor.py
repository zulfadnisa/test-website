import os
import requests

# === KONFIGURASI ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
URLS = [
    "https://bappeda.cirebonkab.go.id/",
    "https://distan.cirebonkab.go.id/",
    "https://dev.kab.cirebonkab.go.id/",
    "https://adik.cirebonkab.go.id/",
    "https://socakaton.cirebonkab.go.id"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print("Telegram Response:", response.status_code, response.text)
    except Exception as e:
        print(f"Gagal kirim notifikasi: {e}")

def check_websites():
    print("TELEGRAM_TOKEN:", TELEGRAM_TOKEN)
    print("CHAT_ID:", CHAT_ID)
    
    for url in URLS:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                send_telegram(f"⚠️ Website DOWN: {url} (Status {response.status_code})")
        except Exception as e:
            send_telegram(f"🚨 Gagal akses {url}: {e}")

check_websites()

