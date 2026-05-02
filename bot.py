import json
import os
import time
import logging
import requests
from telegram import Bot

# ---------- НАСТРОЙКИ (замени на свои) ----------
TELEGRAM_TOKEN = "8729304576:AAGbNUeaWw9byg1w1Nu1AGCMraOXL6VN-Mk"    # токен бота недвижимости
CHAT_ID = "5242236154"                 # числовой или строка

# Фильтры поиска (можно менять)
AREA = "center"          # center, north, south, haifa, jerusalem, sharon, shfela
MAX_PRICE = 2_000_000    # до 2 млн шекелей
MIN_ROOMS = 3
MAX_ROOMS = 4
DEAL_TYPE = "sale"       # sale или rent
PROPERTY_TYPE = "apartment"  # apartment, penthouse, duplex и т.д.
PAGE_SIZE = 25           # сколько объявлений запрашивать за раз

# Файл для сохранения уже отправленных ID
SENT_IDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sent_ids.json")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- API Yad2 ----------
def search_yad2():
    """Поиск объявлений на Yad2 через публичный API."""
    url = "https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/" + DEAL_TYPE
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://www.yad2.co.il",
        "Referer": "https://www.yad2.co.il/realestate/" + DEAL_TYPE,
    }
    # Параметры фильтра
    payload = {
        "area": AREA,
        "propertyType": PROPERTY_TYPE,
        "priceFrom": 0,
        "priceTo": MAX_PRICE,
        "roomsFrom": MIN_ROOMS,
        "roomsTo": MAX_ROOMS,
        "pageSize": PAGE_SIZE,
        "page": 0,
        "sort": "date_desc",   # сначала новые
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        # Структура ответа может отличаться, обычно список объявлений в data["items"]
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        elif isinstance(data, list):
            return data
        else:
            logger.warning("Неожиданная структура ответа Yad2: %s", json.dumps(data, ensure_ascii=False)[:200])
            return []
    except Exception as e:
        logger.error("Ошибка при запросе к Yad2: %s", e)
        return []

# ---------- Telegram ----------
def load_sent_ids():
    if not os.path.exists(SENT_IDS_FILE):
        return set()
    with open(SENT_IDS_FILE, "r") as f:
        return set(json.load(f))

def save_sent_ids(ids_set):
    with open(SENT_IDS_FILE, "w") as f:
        json.dump(list(ids_set), f)

def main():
    sent_ids = load_sent_ids()
    bot = Bot(token=TELEGRAM_TOKEN)
    logger.info("Ищем объявления на Yad2...")
    items = search_yad2()
    new_found = 0

    for item in items:
        # Извлекаем ID (обычно item["id"] или item["post_id"])
        listing_id = str(item.get("id") or item.get("post_id") or "")
        if not listing_id or listing_id in sent_ids:
            continue

        # Поля могут различаться; подстроимся под возможные имена
        title = item.get("title") or item.get("mainTitle") or "Без названия"
        price = item.get("price") or item.get("priceValue") or "—"
        rooms = item.get("rooms") or item.get("numberOfRooms") or "—"
        # Адрес может быть вложен в объект
        address_obj = item.get("address") or item.get("neighborhood") or {}
        if isinstance(address_obj, dict):
            address = address_obj.get("name", "")
        else:
            address = str(address_obj)
        # Ссылка на объявление
        url = item.get("url") or item.get("itemUrl") or ""
        if not url and listing_id:
            url = f"https://www.yad2.co.il/realestate/item/{listing_id}/"

        message = (
            f"🏠 *{title}*\n"
            f"💰 Цена: {price} ₪\n"
            f"🚪 Комнат: {rooms}\n"
            f"📍 {address}\n"
            f"[Открыть объявление]({url})"
        )

        try:
            bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
            # Если есть фото, отправляем первое
            if "images" in item and item["images"]:
                bot.send_photo(chat_id=CHAT_ID, photo=item["images"][0])
            sent_ids.add(listing_id)
            new_found += 1
            time.sleep(1)   # небольшая пауза, чтобы не упереться в лимиты Telegram
        except Exception as e:
            logger.error("Не удалось отправить объявление %s: %s", listing_id, e)

    if new_found:
        logger.info("Отправлено %d новых объявлений", new_found)
        save_sent_ids(sent_ids)
    else:
        logger.info("Новых объявлений нет")

if __name__ == "__main__":
    main()