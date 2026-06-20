
from __future__ import annotations

import json
import os
import urllib.request


def chat(system: str, prompt: str, max_tokens: int = 512, timeout: int = 30) -> str:
    """Send a system + user message, return the assistant's text reply."""
    url = os.environ["LLM_API_URL"]
    key = os.environ["LLM_API_KEY"]
    model = os.environ.get("LLM_MODEL", "default")

    payload = json.dumps({
        "model": model,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read())

    return data["choices"][0]["message"]["content"].strip()
