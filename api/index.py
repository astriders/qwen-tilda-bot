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

# 📚 ЗАГРУЗКА БАЗЫ ТОВАРОВ
def load_products():
    try:
        # Путь к файлу products.json (лежит в корне репозитория)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        products_path = os.path.join(base_path, 'products.json')
        
        with open(products_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading products: {e}")
        return {}

# 🔍 ПОИСК ТОВАРОВ ПО ЗАПРОСУ
def search_products(query, products_db):
    query = query.lower()
    results = []
    
    category_keywords = {
        'ламинат': 'laminat',
        'spc': 'spc',
        'кварцвинил': 'spc',
        'паркет': 'parket',
        'инженер': 'injenernaya',
        'ёлка': 'injenernaya',
        'палуба': 'injenernaya',
        'подложка': 'accessories',
        'плёнка': 'accessories'
    }
    
    color_keywords = {
        'дуб': ['дуб', 'oak'],
        'серый': ['сер', 'grey', 'серый'],
        'светлый': ['светл', 'light', 'бел', 'беж'],
        'тёмный': ['тёмн', 'dark', 'корич'],
        'белый': ['бел', 'white'],
        'золотой': ['золот', 'gold'],
        'песочный': ['песоч', 'sand'],
        'бежевый': ['беж', 'beige']
    }
    
    target_category = None
    for keyword, category in category_keywords.items():
        if keyword in query:
            target_category = category
            break
    
    if target_category and target_category in products_db:
        category_data = products_db[target_category]
        for product in category_data.get('products', []):
            score = 0
            searchable_text = f"{product.get('name', '')} {product.get('color', '')} {product.get('collection', '')}".lower()
            
            for color_key, color_terms in color_keywords.items():
                if color_key in query:
                    for term in color_terms:
                        if term in searchable_text:
                            score += 2
                            break
            
            for term in query.split():
                if len(term) > 3 and term in searchable_text:
                    score += 1
            
            if score > 0:
                results.append((score, product))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [prod for score, prod in results[:3]]
    
    # Определяем категорию по запросу
    target_category = None
    for keyword, category in category_keywords.items():
        if keyword in query:
            target_category = category
            break
    
    # Ищем товары по названию и характеристикам
    if target_category and target_category in products_db:
        category_data = products_db[target_category]
        for product in category_data.get('products', []):
            # Ищем совпадения в названии, цвете, коллекции
            searchable_text = f"{product.get('name', '')} {product.get('color', '')} {product.get('collection', '')}".lower()
            
            # Ключевые слова для поиска внутри категории
            search_terms = ['дуб', 'серый', 'светлый', 'тёмный', 'белый', 'золотой', 'песочный', 'бежевый', 'натуральный']
            
            for term in search_terms:
                if term in query and term in searchable_text:
                    results.append(product)
                    break
    
    return results[:3]  # Возвращаем максимум 3 товара

# 📚 ЗАГРУЗКА БАЗЫ СТАТЕЙ
def load_articles():
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        articles_path = os.path.join(base_path, 'articles.json')
        
        with open(articles_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading articles: {e}")
        return {}

# 🔍 ПОИСК СТАТЕЙ ПО ЗАПРОСУ
def search_articles(query, articles_db):
    query = query.lower()
    results = []
    
    topic_keywords = {
        'уклад': 'укладка',
        'монтаж': 'укладка',
        'тёплый пол': 'тёплый пол',
        'подлож': 'подложка',
        'фаск': 'фаска',
        'сравн': 'сравнение',
        'расчёт': 'расчёт',
        'уход': 'уход',
        'влаг': 'влагостойкость',
        'класс': 'класс износостойкости',
        'гаранти': 'гарантия',
        'достав': 'доставка',
        'оплат': 'оплата'
    }
    
    for article in articles_db.get('articles', []):
        score = 0
        for short, full in topic_keywords.items():
            if short in query and full in ' '.join(article.get('topics', [])):
                score += 2
        
        if any(word in article.get('title', '').lower() for word in query.split()):
            score += 1
        
        if any(word in article.get('summary', '').lower() for word in query.split()):
            score += 1
        
        if score > 0:
            results.append((score, article))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [art for score, art in results[:3]]

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
    
    # 📖 ЗАГРУЖАЕМ ТОВАРЫ
    products_db = load_products()
    
    # 🔍 ИЩЕМ ТОВАРЫ ПО ЗАПРОСУ
    found_products = search_products(request.message, products_db)

        # ➕ ДОБАВЛЯЕМ НАЙДЕННЫЕ ТОВАРЫ В ПРОМПТ
    if found_products:
        system_prompt += "\n\n🔍 ПОДХОДЯЩИЕ ТОВАРЫ ПО ЗАПРОСУ КЛИЕНТА:"
        for product in found_products:
            system_prompt += f"""
• {product.get('name', '')}
  Цена: {product.get('price', '')}
  Артикул: {product.get('sku', '')}
  Ссылка: {product.get('url', '')}
  Описание: {product.get('description', '')}
"""
        system_prompt += "\n\nПредложи эти товары клиенту с кратким описанием и ссылками."

        # 📚 ЗАГРУЖАЕМ СТАТЬИ
    articles_db = load_articles()
    
    # 🔍 ИЩЕМ СТАТЬИ ПО ЗАПРОСУ
    found_articles = search_articles(request.message, articles_db)
    
    # ➕ ДОБАВЛЯЕМ НАЙДЕННЫЕ СТАТЬИ В ПРОМПТ
    if found_articles:
        system_prompt += "\n\n📖 ПОЛЕЗНЫЕ СТАТЬИ ПО ТЕМЕ:"
        for article in found_articles:
            system_prompt += f"\n• {article.get('title', '')} — {article.get('url', '')}"
        system_prompt += "\n\nПредложи клиенту прочитать эти статьи для подробной информации."
    
    # 📝 ФОРМИРУЕМ БАЗУ ЗНАНИЙ
    system_prompt = """
Ты — онлайн-консультант магазина напольных покрытий AlixFloor.
Твоя задача: помогать клиентам выбирать товары, отвечать на вопросы о доставке, оплате, гарантиях.

🎓 ЭКСПЕРТИЗА (из статей на сайте):

**Ламинат:**
• 33 класс (12 мм) — для жилых помещений с высокой нагрузкой (гостиная, коридор, кухня)
• 32 класс (8-10 мм) — для спален, кабинетов, помещений со средней нагрузкой
• Влагостойкость ≠ водостойкость. Ламинат выдерживает влажную уборку, но не потоп
• Фаска (4V) скрывает стыки и продлевает срок службы
• Замок Uniclic (Бельгия) — надёжнее AquaOut, проще в укладке

**SPC (кварцвинил):**
• 43 класс — коммерческая износостойкость, подходит для любых помещений
• 100% влагостойкий — можно в ванную, кухню, балкон
• 5 мм с подложкой — лучше звукоизоляция, комфортнее ходьба
• 4 мм без подложки — дешевле, но нужна отдельная подложка

**Паркетная доска:**
• 14 мм, 3,5 мм рабочий слой — можно шлифовать 1-2 раза
• Матовый лак — практичнее, меньше видно царапин
• Масло — натуральнее, но требует ухода раз в 1-2 года
• Проfiloc 2G — замок для быстрой укладки без клея

**Инженерная доска:**
• 15 мм, 4 мм рабочий слой — стабильнее паркетной, меньше реагирует на влажность
• Французская ёлка — премиум-укладка, расход +15-20%
• Английская ёлка — классика, расход +10-15%
• Палуба — экономичнее, расход +5%

**Укладка:**
• Тёплый пол: макс. +27°C, только электрический или водяной с терморегулятором
• Подложка обязательна: 2 мм для ламината, 1 мм для SPC с подложкой
• Пароизоляция (плёнка) обязательна на бетонное основание
• Акклиматизация: 48 часов в помещении перед укладкой

**Уход:**
• Ламинат: влажная уборка, избегать избытка воды, не использовать абразивы
• SPC: можно мыть, устойчив к бытовой химии
• Паркет/инженер: спецсредства для деревянных полов, избегать царапин

❗ КРИТИЧЕСКИ ВАЖНО:
• ССЫЛКИ НА ТОВАРЫ БЕРИ ТОЛЬКО ИЗ РАЗДЕЛА "НАЙДЕННЫЕ ТОВАРЫ" НИЖЕ
• НЕ ВЫДУМЫВАЙ И НЕ ГЕНЕРИРУЙ ССЫЛКИ САМОСТОЯТЕЛЬНО
• Если товара нет в списке "НАЙДЕННЫЕ ТОВАРЫ" — не давай ссылку, а предложи посмотреть на сайте
• Используй ТОЛЬКО полные URL формата: https://alixfloor.ru/catalog/...

📦 ОСНОВНЫЕ КАТЕГОРИИ (общая информация, БЕЗ ССЫЛОК):
• Ламинат 33 класс (12 мм) — Natural Line, City Line — от 2450 ₽/м²
• Ламинат 32 класс (8-10 мм) — Vitality Line, Regista — от 1490 ₽/м²
• SPC (кварцвинил) 43 класс (5 мм) — от 2070 ₽/м²
• Паркетная доска (14 мм) — от 6500 ₽/м²
• Инженерная доска (15 мм) — Ёлка, Палуба — от 7590 ₽/м²

🚚 ДОСТАВКА:
• Москва: от 50 000 ₽ — 700 ₽, до 50 000 ₽ — 2000 ₽ (1-3 дня)
• Санкт-Петербург: от 50 000 ₽ — 700 ₽, до 50 000 ₽ — 2000 ₽ (2-4 дня)
• Россия: ТК на выбор, до терминала Москвы — 700 ₽
• Самовывоз: бесплатно (Москва, Мосрентген)
• За МКАД: +45 ₽/км

💳 ОПЛАТА:
• Оплата НЕ на сайте! Менеджер связывается после заказа.
• Физлица: онлайн-ссылка, QR-код, наличные при получении (Москва/МО)
• Юрлица: счёт с НДС/без НДС
• Шоурум: Москва, Самара

📞 КОНТАКТЫ:
• Телефон: +7 (495) 308-90-53
• Email: info@alixgroup.ru
• Время: Пн-Пт 10:00-18:00 МСК

📄 ГАРАНТИИ:
• Вся продукция сертифицирована
• Гарантийный срок: 25-50 лет (зависит от коллекции)
• Подробнее: https://alixfloor.ru/sertificates

❗ ВАЖНО:
• Если вопрос о гарантии, возврате, сотрудничестве, дизайнерам — предлагай связаться с менеджером
• Если товара нет в базе — предлагай посмотреть на сайте или заказать звонок
• Отвечай кратко, по делу, на русском языке
• Не используй эмодзи в ответах
"""

    # ➕ ДОБАВЛЯЕМ НАЙДЕННЫЕ ТОВАРЫ В ПРОМПТ
    if found_products:
        system_prompt += "\n\n🔍 ПОДХОДЯЩИЕ ТОВАРЫ ПО ЗАПРОСУ КЛИЕНТА:"
        for product in found_products:
            system_prompt += f"""
• {product.get('name', '')}
  Цена: {product.get('price', '')}
  Артикул: {product.get('sku', '')}
  Ссылка: {product.get('url', '')}
  Описание: {product.get('description', '')}
"""
        system_prompt += "\n\nПредложи эти товары клиенту с кратким описанием и ссылками."

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
