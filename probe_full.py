#!/usr/bin/env python3
# Сквозная проверка пути /model: переключение + сохранение + обычный запрос
import sys
sys.path.insert(0, "/root/.hermes/installs/8a4017c4cabfe15f/environments/8d4a7ba29ef841bf8c0f669b53fbcab4/workspace")

from hermes_cli.config import load_config
from hermes_cli.model_switch import switch_model, persist_model_selection

cfg = load_config()
user_providers = cfg.get("providers") or {}
mode = sys.argv[1] if len(sys.argv) > 1 else "free"

if mode == "free":
    raw, provider, model = "glm-5.3-flash-free", "wormsoft", "zai/glm-5.3-flash"
else:
    raw, provider, model = "zai/glm-5.3-flash", "wormsoft", "glm-5.3-flash-free"

r = switch_model(raw, current_provider=provider, current_model=model,
                 current_base_url="https://ai.wormsoft.ru/api/gpt/v1",
                 user_providers=user_providers, custom_providers=[])
print("switch success:", r.success, "->", r.new_model, "@", r.target_provider)
if r.success:
    persist_model_selection(r)
    print("сохранено в config")

# 2) что показывает /model-пикер
from hermes_cli.model_switch_providers import list_picker_providers
try:
    rows = list_picker_providers(current_provider=getattr(r, "target_provider", ""), user_providers=user_providers, custom_providers=[])
    for row in rows:
        name = getattr(row, "name", None) or (row.get("name") if isinstance(row, dict) else "?")
        mid = getattr(row, "provider_id", None) or getattr(row, "id", None) or (row.get("id") if isinstance(row, dict) else "?")
        if "opencode" in str(name).lower() or "opencode" in str(mid).lower() or "бесплат" in str(name).lower():
            print("пикер-строка:", name, "|", mid)
except Exception as e:
    print("пикер:", type(e).__name__, e)
