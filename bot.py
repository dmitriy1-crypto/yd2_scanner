import os
import json
import logging
import requests

# ---------- НАСТРОЙКИ ----------
# В диагностическом режиме токен и chat_id не используются
AREA = "center"
MAX_PRICE = 2_000_000
MIN_ROOMS = 3
MAX_ROOMS = 4
PROPERTY_TYPE = "apartment"
DEAL_TYPE = "sale"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
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
        
        items = data.get("items") or data.get("data") or []
        if isinstance(data, list):
            items = data
        if not items and "yad1Listing" in data:
            items = data["yad1Listing"]
        if not items and "yad1Ads" in data:
            items = data["yad1Ads"]
        
        logger.info("Найдено объявлений: %d", len(items) if isinstance(items, list) else 0)
        if items and isinstance(items, list) and len(items) > 0:
            logger.info("Пример первого объявления: %s", json.dumps(items[0], ensure_ascii=False)[:500])
        return items if isinstance(items, list) else []
    except Exception as e:
        logger.error("Ошибка запроса к Yad2: %s", e)
        return []

def main():
    logger.info("Запуск диагностического поиска Yad2...")
    items = search_yad2()
    logger.info("Всего объявлений получено: %d", len(items))

if __name__ == "__main__":
    main()
