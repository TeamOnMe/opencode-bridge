#!/usr/bin/env python3
# Какие формы ввода модели резолвятся в провайдера "opencode" (мост)?
import sys
sys.path.insert(0, "/root/.hermes/installs/8a4017c4cabfe15f/environments/8d4a7ba29ef841bf8c0f669b53fbcab4/workspace")

from hermes_cli.config import load_config
from hermes_cli.model_switch import switch_model

cfg = load_config()
user_providers = cfg.get("providers") or {}

for raw in ("glm-5.3-flash-free", "opencode/glm-5.3-flash-free", "big-pickle"):
    r = switch_model(raw, current_provider="wormsoft", current_model="zai/glm-5.3-flash",
                     current_base_url="https://ai.wormsoft.ru/api/gpt/v1",
                     user_providers=user_providers, custom_providers=[])
    ok = getattr(r, "ok", None) or getattr(r, "success", "?")
    print(f"--- {raw!r}: ok={ok}")
    for attr in ("new_model", "target_provider", "base_url", "api_mode", "error", "message", "resolved_alias"):
        v = getattr(r, attr, None)
        if v:
            print(f"    {attr}: {v}")
