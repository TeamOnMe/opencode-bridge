#!/usr/bin/env python3
# Разведка API opencode serve: что возвращает POST /session/{id}/message
import json, urllib.request, time

BASE = "http://127.0.0.1:4096"

def post(path, body, timeout=120):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode()
        print(f"POST {path} -> {r.status}, {len(raw)} bytes, content-type={r.headers.get('content-type')}")
        return raw

# 1. создаём сессию
raw = post("/session", {})
sid = json.loads(raw)["id"]
print("session:", sid)

# 2. шлём сообщение с бесплатной моделью
t0 = time.time()
raw = post(f"/session/{sid}/message", {
    "model": {"providerID": "opencode", "modelID": "glm-5.3-flash-free"},
    "parts": [{"type": "text", "text": "Скажи ровно: ЗОНД-ОК"}],
})
print(f"ответ за {time.time()-t0:.1f}с")
print("--- сырой ответ (первые 3000 символов) ---")
print(raw[:3000])
