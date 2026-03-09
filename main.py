from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Разрешаем запросы с любого сайта (для начала)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

# Ключ мы возьмем из настроек хостинга, не вшиваем в код!
API_KEY = os.getenv("ROUTER_API_KEY")
# Вставь сюда название модели из Шага 1
MODEL_NAME = "qwen-2.5-7b-instruct" 
# Вставь сюда базовый URL от RouterAI (обычно такой)
API_URL = "https://api.routerai.ru/v1/chat/completions"

@app.post("/chat")
async def chat(request: MessageRequest):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API Key not configured")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Системная инструкция (роль консультанта)
    system_prompt = "Ты вежливый консультант сайта. Отвечай кратко, по делу, на русском языке. Не используй эмодзи."

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.7
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        result = response.json()
        return {"reply": result["choices"][0]["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))