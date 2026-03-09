from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import requests

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
        print("ERROR: API Key not found")
        raise HTTPException(status_code=500, detail="API Key not configured")

    API_URL = "https://routerai.ru/api/v1/chat/completions"
    MODEL_NAME = "qwen/qwen-plus-2025-01-25"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    system_prompt = "Ты вежливый консультант сайта. Отвечай кратко, по делу, на русском языке."

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message}
        ],
        "temperature": 0.7
    }

    try:
        print(f"Sending request to {API_URL} with model {MODEL_NAME}")
        response = requests.post(API_URL, headers=headers, json=data, timeout=15)
        
        if response.status_code != 200:
            print(f"API Error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        result = response.json()
        reply = result["choices"][0]["message"]["content"]
        print(f"Success: {reply[:50]}...")
        return {"reply": reply}
        
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout")
    except Exception as e:
        print(f"Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))