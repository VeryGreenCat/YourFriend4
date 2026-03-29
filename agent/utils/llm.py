"""Simple LLM adapter supporting OpenAI and Ollama (HTTP) chat calls.

This module provides `chat_completion` which returns the assistant text content
for a given `model` and `messages` list (OpenAI-style messages). Ollama is
invoked via HTTP POST to `{ollama_url}/api/chat` when configured.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import requests

from .config import get_config


def _call_ollama(
    ollama_url: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    timeout: int = 60,
) -> str:
    url = ollama_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    j = resp.json()
    if isinstance(j, dict):
        # Ollama native format: {"message": {"role": "assistant", "content": "..."}}
        msg = j.get("message")
        if isinstance(msg, dict):
            return msg.get("content", "")
        # OpenAI-compatible format: {"choices": [{"message": {"content": "..."}}]}
        choices = j.get("choices")
        if choices and isinstance(choices, list) and isinstance(choices[0], dict):
            inner = choices[0].get("message")
            if isinstance(inner, dict):
                return inner.get("content", "")
    return resp.text


def _call_openai(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    timeout: int = 30,
) -> str:
    try:
        import openai
    except Exception as e:
        raise RuntimeError("openai package is required for OpenAI backend") from e
    cfg = get_config()
    client = openai.OpenAI(
        api_key=cfg.openai_api_key or None,
        timeout=timeout,
    )
    resp = client.chat.completions.create(
        model=model, messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content.strip()


def chat_completion(
    model: str, messages: List[Dict[str, str]], temperature: float = 0.0
) -> str:
    cfg = get_config()
    backend = (cfg.llm_backend or "openai").lower()
    if backend == "ollama":
        return _call_ollama(
            cfg.ollama_url,
            model,
            messages,
            temperature=temperature,
            timeout=cfg.ollama_timeout,
        )
    return _call_openai(model, messages, temperature=temperature)

def __init__():
    cfg = get_config()
    if cfg.llm_backend == "ollama":
        try:
            _call_ollama(cfg.ollama_url, "test-model", [], timeout=5)
        except Exception as e:
            print(f"Warning: Ollama backend configured but not responding: {e}")