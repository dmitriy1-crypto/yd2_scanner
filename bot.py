import os
import json
import time
import logging
from yad2_scraper import Yad2Scraper
from telegram import Bot
from telegram.error import TelegramError

# ---------- НАСТРОЙКИ ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в переменных окружения!")

# ---------- ФИЛЬТРЫ ПОИСКА ----------
AREA = "center"
MAX_PRICE = 2_000_000
MIN_ROOMS = 3
MAX_ROOMS = 4
PROPERTY_TYPE = "apartment"
DEAL_TYPE = "sale"

SENT_IDS_FILE = "sent_ids.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_yad2():
    """Поиск объявлений через библиотеку yad2-scraper (метод get)."""
    scraper = Yad2Scraper()
    base_url = f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/{DEAL_TYPE}"
    params = {
        "area": AREA,
        "propertyType": PROPERTY_TYPE,
        "priceTo": MAX_PRICE,
        "roomsFrom": MIN_ROOMS,
        "roomsTo": MAX_ROOMS,
        "pageSize": 25,
        "page": 0,
        "sort": "date_desc",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    try:
        # Используем метод get библиотеки (он добавляет случайный User-Agent и обрабатывает ответ)
        resp_data = scraper.get(base_url, params=params, headers=headers)
        if isinstance(resp_data, list):
            return resp_data
        elif isinstance(resp_data, dict) and "items" in resp_data:
            return resp_data["items"]
        else:
            logger.warning("Неожиданная структура ответа: %s", str(resp_data)[:200])
            return []
    except Exception as e:
        logger.error("Ошибка при запросе к Yad2: %s", e)
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

        message = (
            f"🏠 *{title}*\n"
            f"💰 Цена: {price} ₪\n"
            f"🚪 Комнат: {rooms}\n"
            f"📍 {address}\n"
            f"[Открыть объявление]({url})"
        )

        try:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
            if image:
                bot.send_photo(chat_id=CHAT_ID, photo=image)
            sent_ids.add(listing_id)
            new_found += 1
            time.sleep(1)
        except TelegramError as e:
            logger.error("Не удалось отправить %s: %s", listing_id, e)

    save_sent_ids(sent_ids)
    logger.info("Отправлено %d новых объявлений", new_found)

if __name__ == "__main__":
    main()
