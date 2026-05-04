import os
import time
import logging
import requests

# ---------- НАСТРОЙКИ ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в Secrets!")

AREA = 5
MAX_PRICE = 1_510_000
MIN_ROOMS = 1
MAX_ROOMS = 4
PROPERTY_TYPE = "1,3,49,11,4"
DEAL_TYPE = "sale"
IMAGE_ONLY = 1
PRICE_ONLY = 1

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def tg_send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error("Ошибка отправки в Telegram: %s", e)

def fetch_yad2_listings():
    url = f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/{DEAL_TYPE}"
    params = {
        "area": AREA,
        "property": PROPERTY_TYPE,
        "priceTo": MAX_PRICE,
        "roomsFrom": MIN_ROOMS,
        "roomsTo": MAX_ROOMS,
        "pageSize": 25,
        "page": 0,
        "sort": "date_desc",
        "imageOnly": IMAGE_ONLY,
        "priceOnly": PRICE_ONLY,
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Origin": "https://www.yad2.co.il",
        "Referer": "https://www.yad2.co.il/realestate/sale",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items") or data.get("data") or []
        if not items and "yad1Listing" in data:
            items = data["yad1Listing"]
        if not items and "yad1Ads" in data:
            items = data["yad1Ads"]
        if isinstance(data, list):
            items = data
        logger.info("Получено %d объявлений", len(items) if isinstance(items, list) else 0)
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.error("Ошибка при запросе к Yad2: %s", e)
        return []

def build_message(listing):
    title = listing.get("projectName") or listing.get("HomeTypeText") or listing.get("title") or "Без названия"
    price = listing.get("Price", "—")
    rooms = listing.get("Rooms", "—")
    address = listing.get("DisplayAddress") or listing.get("CityNeighborhood", "")
    listing_id = str(listing.get("listing_product_id") or listing.get("OrderID") or listing.get("id", ""))
    
    # Правильная ссылка
    url = listing.get("url") or listing.get("itemUrl") or ""
    if not url and listing_id:
        if "projectID" in listing:
            project_id = listing.get("projectID", "")
            url = f"https://www.yad2.co.il/realestate/project/{project_id}" if project_id else ""
        else:
            url = f"https://www.yad2.co.il/realestate/item/{listing_id}"

    message = f"{title}\n"
    message += f"Цена: {price} ₪\n"
    message += f"Комнат: {rooms}\n"
    if address:
        message += f"Адрес: {address}\n"
    if url:
        message += f"Ссылка: {url}"

    return message

def main():
    tg_send_message("Запуск агента Yad2. Начинаю поиск...")
    items = fetch_yad2_listings()
    if not items:
        tg_send_message("Объявлений не найдено.")
        return

    sent = 0
    for item in items:
        msg = build_message(item)
        tg_send_message(msg)
        sent += 1
        time.sleep(1.5)

    logger.info("Отправлено %d объявлений", sent)

if __name__ == "__main__":
    main()
