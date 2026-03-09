from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

app = FastAPI()

# Разрешаем запросы с любого сайта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MessageRequest(BaseModel):
    message: str

# Берём ключ из переменных окружения Vercel
API_KEY = os.getenv("ROUTER_API_KEY")

# ✅ API URL из документации RouterAI (без пробелов!)
API_URL = "https://routerai.ru/api/v1"

# ✅ Модель Qwen3.5-27B (как в документации)
MODEL_NAME = "qwen/qwen-plus-2025-01-25"

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
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        result = response.json()
        return {"reply": result["choices"][0]["message"]["content"]}
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout: модель отвечает слишком долго")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Ошибка запроса: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


