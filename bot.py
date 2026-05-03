import os
import json
import logging
import requests

# ---------- НАСТРОЙКИ ----------
# Токен и chat_id пока не используются, но оставим для будущего
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()

AREA = "center"
MAX_PRICE = 2_000_000
MIN_ROOMS = 3
MAX_ROOMS = 4
PROPERTY_TYPE = "apartment"
DEAL_TYPE = "sale"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def search_yad2():
    """Прямой GET-запрос к API Yad2, разбор ответа."""
    url = f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/{DEAL_TYPE}"
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.yad2.co.il",
        "Referer": "https://www.yad2.co.il/realestate/sale",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("✅ Yad2 ответ получен. Ключи верхнего уровня: %s", list(data.keys()))
        
        # Пробуем разные поля, где могут быть объявления
        items = data.get("items") or data.get("data") or []
        if isinstance(data, list):
            items = data
        # Новые поля из последних ответов
        if not items and "yad1Listing" in data:
            items = data["yad1Listing"]
        if not items and "yad1Ads" in data:
            items = data["yad1Ads"]
        
        logger.info("Найдено объявлений: %d", len(items) if isinstance(items, list) else 0)
        if items and isinstance(items, list) and len(items) > 0:
            # Показываем первое объявление для диагностики
            logger.info("Пример первого объявления: %s", json.dumps(items[0], ensure_ascii=False)[:500])
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.error("Ошибка запроса к Yad2: %s", e)
        return []

def main():
    logger.info("Запуск диагностического поиска Yad2...")
    items = search_yad2()
    logger.info("Всего объявлений получено: %d", len(items))
    # Временно не отправляем в Telegram, только смотрим логи

if __name__ == "__main__":
    main()import os
import json
import time
import logging
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в переменных окружения!")

AREA = "center"
MAX_PRICE = 2_000_000
MIN_ROOMS = 3
MAX_ROOMS = 4
PROPERTY_TYPE = "apartment"
DEAL_TYPE = "sale"

SENT_IDS_FILE = "sent_ids.json"
logging.basicConfig(level=logging.INFO)
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

def search_yad2():
    url = f"https://www.yad2.co.il/api/pre-load/getFeedIndex/realestate/{DEAL_TYPE}"
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Origin": "https://www.yad2.co.il",
        "Referer": "https://www.yad2.co.il/realestate/sale",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logger.info("Ответ Yad2 получен, ключи: %s", list(data.keys())[:5])
        items = data.get("items") or data.get("data") or []
        if isinstance(data, list):
            items = data
        return items
    except Exception as e:
        logger.error("Ошибка запроса к Yad2: %s", e)
        return []

def load_sent_ids():
    try:
        with open(SENT_IDS_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_sent_ids(ids_set):
    with open(SENT_IDS_FILE, "w") as f:
        json.dump(list(ids_set), f)

def main():
    # Тестовое сообщение
    tg_send_message("✅ Тестовое сообщение. Бот работает!")
    
    sent_ids = load_sent_ids()
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
        tg_send_message(message, parse_mode="Markdown")
        if image:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": CHAT_ID, "photo": image})
        sent_ids.add(listing_id)
        new_found += 1
        time.sleep(1)

    save_sent_ids(sent_ids)
    logger.info("Отправлено %d новых объявлений", new_found)

if __name__ == "__main__":
    main()
