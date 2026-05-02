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
SEARCH_FILTERS = {
    "area": "center",          # תל אביב והמרכז
    "max_price": 2_000_000,
    "min_rooms": 3,
    "max_rooms": 4,
    "property_type": "apartment",
    "deal_type": "sale",
}

SENT_IDS_FILE = "sent_ids.json"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    scraper = Yad2Scraper()

    logger.info("Запуск поиска объявлений...")
    try:
        listings = scraper.search(SEARCH_FILTERS)
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        return

    new_found = 0
    for listing in listings:
        listing_id = str(listing.get("id"))
        if listing_id in sent_ids:
            continue

        title = listing.get("title", "Без названия")
        price = listing.get("price", "—")
        rooms = listing.get("rooms", "—")
        address = listing.get("address", listing.get("city", {}).get("name", ""))
        url = listing.get("url", "")
        img = listing.get("image", "")

        message = (
            f"🏠 *{title}*\n"
            f"💰 Цена: {price} ₪\n"
            f"🚪 Комнат: {rooms}\n"
            f"📍 {address}\n"
            f"[Открыть объявление]({url})"
        )

        try:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
            if img:
                bot.send_photo(chat_id=CHAT_ID, photo=img)
            sent_ids.add(listing_id)
            new_found += 1
            time.sleep(1)
        except TelegramError as e:
            logger.error(f"Не удалось отправить {listing_id}: {e}")

    save_sent_ids(sent_ids)
    logger.info(f"Отправлено {new_found} новых объявлений")

if __name__ == "__main__":
    main()
