import os
import json
import time
import logging
import requests
from telegram import Bot
from telegram.error import TelegramError

# ---------- НАСТРОЙКИ ----------
# Важно: Токен и ID чата мы будем передавать через Секреты GitHub
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в переменных окружения!")

# ---------- ФИЛЬТРЫ ПОИСКА ----------
SEARCH_FILTERS = {
    "area": "center",
    "max_price": 2_000_000,
    "min_rooms": 3,
    "max_rooms": 4,
    "property_type": "apartment",
    "deal_type": "sale",
}

SENT_IDS_FILE = "sent_ids.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_yad2():
    logger.info("Запуск поиска объявлений...")
    url = f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/{SEARCH_FILTERS['deal_type']}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.yad2.co.il",
        "Referer": f"https://www.yad2.co.il/realestate/{SEARCH_FILTERS['deal_type']}",
    }
    payload = {
        "area": SEARCH_FILTERS["area"],
        "propertyType": SEARCH_FILTERS["property_type"],
        "priceTo": SEARCH_FILTERS["max_price"],
        "roomsFrom": SEARCH_FILTERS["min_rooms"],
        "roomsTo": SEARCH_FILTERS["max_rooms"],
        "pageSize": 25,
        "page": 0,
        "sort": "date_desc",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return data.get("items", data if isinstance(data, list) else [])
    except Exception as e:
        logger.error(f"Ошибка при запросе к Yad2: {e}")
        return []

def load_sent_ids():
    try:
        with open(SENT_IDS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

def save_sent_ids(ids_set):
    with open(SENT_IDS_FILE, "w") as f:
        json.dump(list(ids_set), f)

def main():
    sent_ids = load_sent_ids()
    bot = Bot(token=TELEGRAM_TOKEN)
    items = search_yad2()
    new_found = 0

    for item in items:
        listing_id = str(item.get("id", ""))
        if not listing_id or listing_id in sent_ids:
            continue

        title = item.get("title", "Без названия")
        price = item.get("price", "—")
        rooms = item.get("rooms", "—")
        address_obj = item.get("address", item.get("neighborhood", {}))
        address = address_obj.get("name", "") if isinstance(address_obj, dict) else str(address_obj)
        url = item.get("url", f"https://www.yad2.co.il/realestate/item/{listing_id}/")
        image = (item.get("images") or [None])[0]

        message = f"🏠 *{title}*\n💰 Цена: {price} ₪\n🚪 Комнат: {rooms}\n📍 {address}\n[Открыть объявление]({url})"

        try:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
            if image:
                bot.send_photo(chat_id=CHAT_ID, photo=image)
            sent_ids.add(listing_id)
            new_found += 1
            time.sleep(1)
        except TelegramError as e:
            logger.error(f"Не удалось отправить {listing_id}: {e}")

    save_sent_ids(sent_ids)
    logger.info(f"Отправлено {new_found} новых объявлений")

if __name__ == "__main__":
    main()
