# Monitor Website

---- DESC ----
Untuk mengecek website mana yang aktif dan tidak. Jika tidak aktif akan mengirimkan notifikasi ke bot telegram.

Bahasa: python

---- Config ----
- Response 200 - 399 : Website aktif
- Response diluar itu dianggap ga aktif, bisa karena 403, bot blocked, timeout, connection error, 500 atau lainnya.
- Timeout : 10 sama 15
- Dibuat paralel dengan MAX_WORKERS=6

Hasil report berupa notifikasi ke telegram yang berisikan website mana saja yang down/error dan berapa jumlah website yang aktif. Jika yang error banyak maka akan dikirimkan dalam bentuk file txt.
