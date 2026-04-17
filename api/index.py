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
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        products_path = os.path.join(base_path, 'products.json')
        
        with open(products_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading products: {e}")
        return {}

# 🔍 ПОИСК ТОВАРОВ ПО ЗАПРОСУ (исправленная версия — без дублей)
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

# 🏙️ ЗАГРУЗКА БАЗЫ ГОРОДОВ
def load_cities():
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cities_path = os.path.join(base_path, 'cities.json')
        with open(cities_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading cities: {e}")
        return {"cities": []}

# 🔍 ПОИСК ГОРОДА ПО ЗАПРОСУ
def search_city(query, cities_db):
    query = query.lower()
    results = []
    
    for city in cities_db.get('cities', []):
        city_name = city.get('name', '').lower()
        # Ищем совпадения по названию города
        if city_name in query or query in city_name:
            results.append(city)
        # Ищем по региону
        region = city.get('region', '').lower()
        if region and region in query:
            results.append(city)
    
    # Убираем дубликаты и возвращаем топ-3
    seen = set()
    unique_results = []
    for city in results:
        if city['name'] not in seen:
            seen.add(city['name'])
            unique_results.append(city)
    
    return unique_results[:3]

@app.post("/chat")
async def chat(request: MessageRequest):
    # 📊 АНОНИМНОЕ ЛОГИРОВАНИЕ (без ПДн, только текст вопроса)
    question_preview = request.message[:200] if len(request.message) > 200 else request.message
    print(f"🔍 [ALIXFLOOR] Вопрос: {question_preview}")
    
    API_KEY = os.getenv("ROUTER_API_KEY")
    if not API_KEY:
        print("❌ [ALIXFLOOR] API Key not configured")
        raise HTTPException(status_code=500, detail="API Key not configured")
    
    # ✅ API_URL без пробелов!
    API_URL = "https://routerai.ru/api/v1/chat/completions"
    MODEL_NAME = "openai/gpt-4o-mini"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # 📚 ЗАГРУЖАЕМ БАЗЫ
    products_db = load_products()
    articles_db = load_articles()
    cities_db = load_cities()
    
    # 🔍 ИЩЕМ ТОВАРЫ И СТАТЬИ
    found_products = search_products(request.message, products_db)
    found_articles = search_articles(request.message, articles_db)
    found_cities = search_city(request.message, cities_db)
    
    # 📝 ФОРМИРУЕМ БАЗУ ЗНАНИЙ
    system_prompt = """
Ты — онлайн-консультант и эксперт по напольным покрытиям AlixFloor.
Твоя задача: помогать клиентам выбирать товары, отвечать на вопросы о доставке, оплате, гарантиях.
Тебя зовут Данил.
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
• ССЫЛКИ НА ТОВАРЫ БЕРИ ТОЛЬКО ИЗ ПОЛЯ "url" В РАЗДЕЛЕ "НАЙДЕННЫЕ ТОВАРЫ" НИЖЕ
• НИКОГДА не конструируй, не генерируй и не «угадывай» ссылки самостоятельно
• Если в ответе нужно дать ссылку на товар — используй ТОЛЬКО значение из поля "url" найденного товара
• Если товар не найден в базе — НЕ давай ссылку, а предложи:
  - «Посмотреть все товары категории в каталоге: https://alixfloor.ru/catalog/{category}/»
  - «Воспользоваться поиском на сайте: https://alixfloor.ru/catalog/»
  - «Связаться с менеджером: [📞 Заказать звонок]»
• ССЫЛКИ НА СТАТЬИ — только из поля "url" в "НАЙДЕННЫЕ СТАТЬИ"
• Все внешние ссылки должны быть полными: https://alixfloor.ru/...
• НИКОГДА не запрашивай и не принимай номер телефона, email или имя пользователя в чате
• Если клиент хочет, чтобы с ним связались — предложи Заказать звонок
• Отвечай кратко, по делу, на русском языке
• Не используй эмодзи в ответах
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
• Чтобы заказать звонок: нажмите  на одноименную кнопку в шапке сайта
• Телефон: +7 (495) 308-90-53
• Шоу-рум в Москве, м. Румянцево Москва, 22-ой км Киевского шоссе, домовладение 4, Бизнес Парк "Румянцево", корпус "А", офисный вход № 8, офис 726 А,  Время работы: Пн-Пт 10:00-18:00 МСК, Телефон: +7 (495) 308-90-53
• Шоу-рум в Самаре, Самара, улица Ново-Вокзальная, дом 27, 1 этаж, Время работы: Пн-Пт с 10:00 до 20:00. Сб с 11:00 до 18:00, Телефон: +7 (495) 308-90-53
• Не оставляйте номер телефона в чате — используйте форму заказа звонка
❗ ЛОГИКА ССЫЛОК НА ГОРОДА:
• 🏙️ Если клиент спрашивает "где купить в [городе]" — используй ссылки из раздела "ГДЕ КУПИТЬ В ВАШЕМ ГОРОДЕ"
• Не выдумывай адреса магазинов — направляй на страницу города
• На страницах городов представлены  точки продаж ( адреса магазинов, в которых можно купить продукцию AlixFloor )
  1. Сначала проверь список известных городов (см. базу ниже)
  2. Если город есть — дай прямую ссылку: https://alixfloor.ru{slug}
  3. Если города нет в списке — предложи ссылку на федеральный округ, в котором он находится, или общую страницу: /where-to-buy-alixfloor
• Примеры:
  "где купить в Казани" → /kazan
  "Как заказать в Саратов" → /saratov  +  /delivery
  "доставка в Омск" → /privolzskiy-okrug (или /where-to-buy-alixfloor) + /delivery
  "А где можно посмотреть в Смоленске" → /smolensk
• Не выдумывай slug для городов, которых нет в базе.
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
    
    # ➕ ДОБАВЛЯЕМ НАЙДЕННЫЕ СТАТЬИ В ПРОМПТ
    if found_articles:
        system_prompt += "\n\n📖 ПОЛЕЗНЫЕ СТАТЬИ ПО ТЕМЕ:"
        for article in found_articles:
            system_prompt += f"\n• {article.get('title', '')} — {article.get('url', '')}"
        system_prompt += "\n\nПредложи клиенту прочитать эти статьи для подробной информации."

    # ➕ ДОБАВЛЯЕМ НАЙДЕННЫЕ ГОРОДА В ПРОМПТ (← Новый блок)
    if found_cities:
        system_prompt += "\n\n🏙️ ГДЕ КУПИТЬ В ВАШЕМ ГОРОДЕ:"
        for city in found_cities:
            system_prompt += f"\n    • {city.get('name', '')} — {city.get('url', '')}"
        system_prompt += "\n\nЕсли клиент спрашивает про наличие в городе — дай ссылку на страницу города."
    
    
    # 📤 ФОРМИРУЕМ ЗАПРОС К МОДЕЛИ
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.7
    }
    
    try:
        print(f"📤 [ALIXFLOOR] Отправка запроса к модели: {MODEL_NAME}")
        response = requests.post(API_URL, headers=headers, json=data, timeout=60)
        
        if response.status_code != 200:
            print(f"❌ [ALIXFLOOR] Ошибка API: {response.status_code} - {response.text[:200]}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        print(f"✅ [ALIXFLOOR] Ответ получен, длина: {len(reply)} симв.")
        return {"reply": reply}
        
    except requests.exceptions.Timeout:
        print("❌ [ALIXFLOOR] Timeout при запросе к API")
        raise HTTPException(status_code=504, detail="Сервер отвечает слишком долго. Попробуйте позже.")
    except Exception as e:
        print(f"❌ [ALIXFLOOR] Исключение: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))





