import os
import logging
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
CHAT_ID = os.environ.get("CHAT_ID", "").strip()

if not TELEGRAM_TOKEN or not CHAT_ID:
    raise ValueError("TELEGRAM_TOKEN и CHAT_ID должны быть заданы в Secrets!")

# Фильтры – пока вообще без ограничений, только регион и тип сделки
AREA = 5
DEAL_TYPE = "sale"

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
        "pageSize": 25,
        "page": 0,
        "sort": "date_desc",
    }
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
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

def main():
    tg_send_message("Запуск отладочного поиска (без фильтров)...")
    items = fetch_yad2_listings()
    if not items:
        tg_send_message("Объявлений не найдено.")
        return

    for item in items:
        title = item.get("title") or item.get("projectName") or item.get("HomeTypeText") or "Без названия"
        price = item.get("Price")
        if price is None or price == 0:
            price = "Цена не указана"
        else:
            price = f"{price} ₪"
        
        rooms = item.get("Rooms", "—")
        address = item.get("DisplayAddress") or item.get("CityNeighborhood", "")
        listing_id = str(item.get("listing_product_id") or item.get("id", ""))

        url = ""
        if "projectID" in item:
            url = f"https://www.yad2.co.il/realestate/project/{item['projectID']}"
        elif listing_id:
            url = f"https://www.yad2.co.il/realestate/item/{listing_id}"

        msg = f"{title}\nЦена: {price}\nКомнат: {rooms}\nАдрес: {address}\nСсылка: {url}"
        tg_send_message(msg)

    logger.info("Отправлено %d объявлений", len(items))

if __name__ == "__main__":
    main()
