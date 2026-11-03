#!/usr/bin/env python3
# Мост: OpenAI-совместимый API поверх opencode serve (бесплатные модели OpenCode Zen).
# Слушает 127.0.0.1:4100. Hermes шлёт обычные chat-запросы сюда, мост пересылает их
# в работающую программу OpenCode и возвращает ответ в привычном формате.
import json, re, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

OC_BASE = "http://127.0.0.1:4096"   # opencode serve (systemd: opencode-serve.service)
HOST, PORT = "127.0.0.1", 4100
MAX_TOKENS_DEFAULT = 4096

FREE_MODELS = [
    "glm-5.3-flash-free", "deepseek-v4.1-flash-free", "big-pickle", "flint-40b-free",
    "mimo-v2.6-flash-free", "nemotron-3.5-lightning-free", "nemotron-3.5-super-vl-free",
    "beam-free",
]

FINAL_INSTRUCTION = (
    "\n\n=== ЗАДАЧА ===\n"
    "Ответь на последнее сообщение пользователя из диалога выше. "
    "Ты отвечаешь простым текстом в чате: не вызывай инструменты, не пиши вызовы функций — "
    "просто дай ответ текстом. Отвечай на языке пользователя."
)


def oc_post(path, body, timeout=600):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        OC_BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def content_text(content):
    """Строка из поля content (строка или список блоков)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") in ("text", "input_text"):
                parts.append(b.get("text", ""))
        return " ".join(p for p in parts if p)
    return ""


def fold_messages(messages):
    """Складываем историю диалога в одну задачу для opencode (1 запрос к модели)."""
    system_parts, turns = [], []
    for m in messages or []:
        role = (m.get("role") or "").strip()
        text = content_text(m.get("content"))
        if not text and not m.get("tool_calls"):
            continue
        if role == "system":
            system_parts.append(text)
        elif role == "user":
            turns.append("Пользователь: " + text)
        elif role == "assistant":
            turns.append("Ассистент: " + text)
    # инструкции об инструментах Hermes не нужны — оставляем только смысл системного блока
    header = "\n\n".join(s for s in system_parts if s.strip())
    body = "\n\n".join(turns) or "Пользователь: привет"
    return (header + "\n\n" if header else "") + "=== ДИАЛОГ ===\n" + body + FINAL_INSTRUCTION


def chat_completion(payload):
    model_raw = (payload.get("model") or "glm-5.3-flash-free").strip()
    model = model_raw.split("/", 1)[1] if model_raw.startswith("opencode/") else model_raw
    prompt = fold_messages(payload.get("messages"))
    t0 = time.time()
    created = oc_post("/session", {})
    sid = created["id"]
    resp = oc_post(f"/session/{sid}/message", {
        "model": {"providerID": "opencode", "modelID": model},
        "parts": [{"type": "text", "text": prompt}],
    })
    info = resp.get("info") or {}
    texts = [p.get("text", "") for p in resp.get("parts", [])
             if p.get("type") == "text" and p.get("text")]
    content = "\n".join(t for t in texts if t).strip()
    if not content:
        content = "(модель не вернула текст)"
    tok = info.get("tokens") or {}
    return {
        "id": "chatcmpl-" + sid.replace("ses_", "")[:24],
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": tok.get("input", 0),
            "completion_tokens": tok.get("output", 0),
            "total_tokens": tok.get("total", 0),
        },
        "bridge": {"session": sid, "seconds": round(time.time() - t0, 1)},
    }


def sse_line(obj):
    return ("data: " + json.dumps(obj, ensure_ascii=False) + "\n\n").encode()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), fmt % args), flush=True)

    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/v1/models") or self.path.startswith("/models"):
            now = int(time.time())
            data = {"object": "list", "data": [
                {"id": m, "object": "model", "created": now, "owned_by": "opencode"}
                for m in FREE_MODELS]}
            self._send(200, json.dumps(data, ensure_ascii=False).encode())
        elif self.path.startswith("/health"):
            self._send(200, b'{"ok": true}')
        else:
            self._send(404, b'{"error": "not found"}')

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            self._send(404, b'{"error": "not found"}')
            return
        try:
            n = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(n).decode() or "{}")
        except Exception as e:
            self._send(400, json.dumps({"error": str(e)}).encode())
            return
        try:
            result = chat_completion(payload)
        except Exception as e:
            self.log_message("bridge error: %s", e)
            self._send(502, json.dumps({"error": {"message": str(e)}}).encode())
            return

        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            model = result["model"]
            base = {"id": result["id"], "object": "chat.completion.chunk",
                    "created": result["created"], "model": model}
            self.wfile.write(sse_line({**base, "choices": [
                {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]}))
            text = result["choices"][0]["message"]["content"]
            self.wfile.write(sse_line({**base, "choices": [
                {"index": 0, "delta": {"content": text}, "finish_reason": None}]}))
            self.wfile.write(sse_line({**base, "choices": [
                {"index": 0, "delta": {}, "finish_reason": "stop"}]}))
            self.wfile.write(b"data: [DONE]\n\n")
        else:
            self._send(200, json.dumps(result, ensure_ascii=False).encode())


if __name__ == "__main__":
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"opencode-bridge слушает http://{HOST}:{PORT}", flush=True)
    srv.serve_forever()
