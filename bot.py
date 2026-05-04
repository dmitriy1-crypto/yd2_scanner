import os
import json
import time
import logging
import requests

# ---------- НАСТРОЙКИ ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в Secrets!")

# ---------- ФИЛЬТРЫ ПОИСКА ----------
AREA = 5
MAX_PRICE = 1_510_000
MIN_ROOMS = 1
MAX_ROOMS = 4
PROPERTY_TYPE = "1,3,49,11,4"
DEAL_TYPE = "sale"
IMAGE_ONLY = 1
PRICE_ONLY = 1

SENT_IDS_FILE = "sent_ids.json"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def tg_send_message(text, parse_mode=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "disable_web_page_preview": True}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Сообщение отправлено: %s", text[:100])
    except Exception as e:
        logger.error("Ошибка отправки в Telegram: %s", e)

def tg_send_photo(photo_url):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    payload = {"chat_id": CHAT_ID, "photo": photo_url}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error("Ошибка отправки фото: %s", e)

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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.yad2.co.il",
        "Referer": "https://www.yad2.co.il/realestate/sale",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        items = data.get("items") or data.get("data") or []
        if isinstance(data, list):
            items = data
        if not items and "yad1Listing" in data:
            items = data["yad1Listing"]
        if not items and "yad1Ads" in data:
            items = data["yad1Ads"]

        logger.info("Получено %d объявлений", len(items) if isinstance(items, list) else 0)
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.error("Ошибка при запросе к Yad2: %s", e)
        return []

def load_sent_ids():
    try:
        with open(SENT_IDS_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_sent_ids(ids_set):
    with open(SENT_IDS_FILE, "w") as f:
        json.dump(list(ids_set), f)

def build_message(listing):
    """Формирует текст объявления для Telegram с правильной ссылкой."""
    title = listing.get("projectName") or listing.get("HomeTypeText") or listing.get("title") or "Без названия"
    price = listing.get("Price", "—")
    rooms = listing.get("Rooms", "—")
    address = listing.get("DisplayAddress") or listing.get("CityNeighborhood", "")

    # Уникальный ID и правильная ссылка
    listing_id = str(listing.get("listing_product_id") or listing.get("OrderID") or listing.get("id", ""))
    url = ""
    if listing_id:
        # Пробуем сначала прямую ссылку из данных
        url = listing.get("url") or listing.get("itemUrl") or ""
        if not url:
            # Генерируем ссылку по типу объявления
            if "projectID" in listing:  # это проект застройщика
                project_id = listing.get("projectID", "")
                url = f"https://www.yad2.co.il/realestate/project/{project_id}" if project_id else ""
            else:  # обычное объявление
                url = f"https://www.yad2.co.il/realestate/item/{listing_id}"

    image = None
    if "images" in listing and listing["images"]:
        image = listing["images"][0]

    message = f"🏠 *{title}*\n"
    message += f"💰 Цена: {price} ₪\n"
    message += f"🚪 Комнат: {rooms}\n"
    if address:
        message += f"📍 {address}\n"
    if url:
        message += f"[Открыть объявление]({url})"

    return message, image, listing_id

def main():
    tg_send_message("Запуск агента Yad2. Начинаю поиск..")
    
    sent_ids = load_sent_ids()
    items = fetch_yad2_listings()
    new_found = 0

    for item in items:
        # Временно не фильтруем новостройки, чтобы показать все объявления
        msg, image, listing_id = build_message(item)
        if not listing_id or listing_id in sent_ids:
            continue
        # Проверяем, что ссылка не пустая
        if "[Открыть объявление]()" in msg:
            continue

        tg_send_message(msg, parse_mode="Markdown")
        if image:
            tg_send_photo(image)
        sent_ids.add(listing_id)
        new_found += 1
        time.sleep(1.5)

    if new_found:
        save_sent_ids(sent_ids)
        logger.info("Отправлено %d новых объявлений", new_found)
    else:
        logger.info("Новых объявлений нет")

if __name__ == "__main__":
    main()
