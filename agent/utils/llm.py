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


def _call_ollama(ollama_url: str, model: str, messages: List[Dict[str, str]], temperature: float = 0.0, timeout: int = 30) -> str:
    url = ollama_url.rstrip("/") + "/api/chat"
    payload = {"model": model, "messages": messages, "temperature": temperature}
    resp = requests.post(url, json=payload, timeout=timeout)
    # Ollama may return streaming or json — attempt to parse JSON first
    try:
        j = resp.json()
        # Typical shape: {'choices': [{'message': {'content': '...'}}]}
        if isinstance(j, dict):
            choices = j.get("choices")
            if choices and isinstance(choices, list):
                msg = choices[0].get("message") if isinstance(choices[0], dict) else None
                if msg and isinstance(msg, dict):
                    return msg.get("content", "")
            # fallback: sometimes ollama returns {'text': '...'}
            if "text" in j:
                return str(j["text"]) or ""
        # fallback to raw text
    except Exception:
        pass
    return resp.text


def _call_openai(model: str, messages: List[Dict[str, str]], temperature: float = 0.0, timeout: int = 30) -> str:
    try:
        import openai
    except Exception as e:
        raise RuntimeError("openai package is required for OpenAI backend") from e
    # Use global OpenAI api_key if configured (openai lib reads env var)
    resp = openai.ChatCompletion.create(model=model, messages=messages, temperature=temperature)
    content = resp["choices"][0]["message"]["content"].strip()
    return content


def chat_completion(model: str, messages: List[Dict[str, str]], temperature: float = 0.0) -> str:
    cfg = get_config()
    backend = (cfg.llm_backend or "openai").lower()
    if backend == "ollama":
        return _call_ollama(cfg.ollama_url, model, messages, temperature=temperature)
    return _call_openai(model, messages, temperature=temperature)
