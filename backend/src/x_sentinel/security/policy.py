from __future__ import annotations


def assert_safe_runtime(*, demo_mode: bool, auth_mode: str, bind_host: str) -> None:
    if auth_mode == "none" and bind_host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        raise RuntimeError("unauthenticated network exposure requires an approved security decision")
    if not isinstance(demo_mode, bool):
        raise RuntimeError("demo mode must be explicit")
