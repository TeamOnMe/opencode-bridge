#!/usr/bin/env python3
# Проверка: как Hermes резолвит имя провайдера "opencode" и модель "glm-5.3-flash-free"
import sys
sys.path.insert(0, "/root/.hermes/installs/8a4017c4cabfe15f/environments/8d4a7ba29ef841bf8c0f669b53fbcab4/workspace")

from hermes_cli import runtime_provider_custom as rpc

print("1) _shadowed_by_builtin('opencode'):", rpc._shadowed_by_builtin("opencode"))
print("2) _get_named_custom_provider('opencode'):", rpc._get_named_custom_provider("opencode"))

try:
    from hermes_cli.runtime_provider import resolve_runtime_provider
    rt = resolve_runtime_provider(requested="opencode", target_model="glm-5.3-flash-free")
    print("3) runtime:", {k: v for k, v in rt.items() if k in ("provider", "base_url", "api_mode", "api_key", "requested_provider")})
except Exception as e:
    print("3) resolve_runtime_provider FAILED:", type(e).__name__, e)
