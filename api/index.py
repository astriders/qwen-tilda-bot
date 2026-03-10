from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: MessageRequest):
    API_KEY = os.getenv("ROUTER_API_KEY")
    
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")

    API_URL = "https://routerai.ru/api/v1/chat/completions"
    MODEL_NAME = "qwen/qwen-plus"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 📚 СИСТЕМНЫЙ ПРОМПТ С БАЗОЙ ЗНАНИЙ
    system_prompt = """
Ты — онлайн-консультант магазина напольных покрытий AlixFloor.
Твоя задача: помогать клиентам выбирать товары, отвечать на вопросы о доставке, оплате, гарантиях.

📦 КАТАЛОГ ТОВАРОВ:
1. Ламинат 33 класс (12 мм) — Natural Line, City Line — от 2450 ₽/м²
2. Ламинат 32 класс (8-10 мм) — Vitality Line — от 2190 ₽/м²
3. SPC (кварцвинил) 43 класс (5 мм) — Natural Line, City Line, Stone Line — от 2070 ₽/м²
4. Паркетная доска (14 мм) — дуб, ясень — от 6500 ₽/м²
5. Инженерная доска (15 мм) — ёлка, палуба — от 7590 ₽/м²

🚚 ДОСТАВКА:
• Москва: от 50 000 ₽ — 700 ₽, до 50 000 ₽ — 2000 ₽ (1-3 дня)
• Санкт-Петербург: от 50 000 ₽ — 700 ₽, до 50 000 ₽ — 2000 ₽ (2-4 дня)
• Россия: ТК на выбор, до терминала Москвы — 700 ₽
• Самовывоз: бесплатно (Москва, Мосрентген)
• За МКАД: +45 ₽/км

💳 ОПЛАТА:
• Не принимается на сайте! Менеджер связывается после заказа.
• Физлица: онлайн-ссылка, QR-код, наличные при получении (Москва/МО)
• Юрлица: счёт с НДС/без НДС
• Шоурум: Москва, Самара

📞 КОНТАКТЫ:
• Телефон: +7 (495) 308-90-53
• Email: info@alixgroup.ru
• Время: Пн-Пт 10:00-18:00 МСК

📄 ГАРАНТИИ И СЕРТИФИКАТЫ:
• Вся продукция сертифицирована
• Гарантийный срок зависит от коллекции (25-50 лет)
• Подробнее: https://alixfloor.ru/sertificates

🏢 О КОМПАНИИ:
• Бренд AlixFloor, владелец ООО «АЛИКС ГРУПП»
• 18 лет на рынке, 5 заводов-производителей в РФ
• Сделано в России

❗ ВАЖНО:
• Если вопрос о гарантии, возврате, сотрудничестве, дизайнерам — предлагай связаться с менеджером
• Если товара нет в базе — предлагай посмотреть на сайте или заказать звонок
• Всегда давай прямые ссылки на товары (формат: https://alixfloor.ru/catalog/...)
• Отвечай кратко, по делу, на русском языке
• Не используй эмодзи в ответах
"""

    # 🔍 ПОИСК ТОВАРОВ В ЗАПРОСЕ
    user_message = request.message.lower()
    
    # Ключевые слова для поиска товаров
    product_keywords = {
        "дуб": "laminat/dub",
        "ламинат": "laminat",
        "spc": "spc",
        "кварцвинил": "spc",
        "паркет": "parketnaya-doska",
        "инженер": "injenernaya-doska",
        "ёлка": "french-elka",
        "палуба": "paluba",
        "33 класс": "laminat-33",
        "43 класс": "spc",
        "натуральный": "natural-line",
        "city": "city-line",
        "vitality": "vitality-line",
        "regista": "regista"
    }
    
    # Ищем совпадения
    found_categories = []
    for keyword, category in product_keywords.items():
        if keyword in user_message:
            found_categories.append(category)
    
    # Если нашли категории — добавляем подсказку в промпт
    if found_categories:
        system_prompt += f"\n\n🔍 КЛИЕНТ ИНТЕРЕСУЕТСЯ: {', '.join(found_categories)}"
        system_prompt += "\nПредложи 2-3 товара из этих категорий с ценами и ссылками."

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        return {"reply": result["choices"][0]["message"]["content"]}
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Сервер отвечает слишком долго. Попробуйте позже.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
