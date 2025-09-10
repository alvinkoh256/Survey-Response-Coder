import os
import json
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_KEY  = os.getenv("AIBOTS_API_KEY")
BASE_URL = os.getenv("AIBOTS_BASE_URL", "https://api.uat.aibots.gov.sg")
VERSION  = os.getenv("AIBOTS_VERSION", "v1.0")
HEADERS  = {"X-ATLAS-Key": API_KEY}
VERIFY   = os.getenv("AIBOTS_VERIFY", "false").lower() in ("1", "true", "yes")

def create_chat(model: str = "azure~openai.gpt-4o-mini", name: str = "") -> str:
    url = f"{BASE_URL}/{VERSION}/api/chats"
    payload = {
        "name": name,
        "agents": [],
        "params": {},
        "properties": {},
        "model": model,
        "pinned": False,
    }
    r = requests.post(
        url,
        headers={**HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=30,
        verify=VERIFY,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Create chat failed: {r.status_code} {r.text}")
    chat_id = r.json().get("id")
    if not chat_id:
        raise RuntimeError(f"No chat id returned: {r.text}")
    return chat_id

def send_message(
    chat_id: str,
    text: str,
    *,
    streaming: bool = False,
    cloak: bool = True,
    pipeline: str | None = None,
    params: dict | None = None,
    properties: dict | None = None,
) -> dict:
    url = f"{BASE_URL}/{VERSION}/api/chats/{chat_id}/messages"
    qp  = {"streaming": str(streaming).lower(), "cloak": str(cloak).lower()}
    if pipeline:
        qp["pipeline"] = pipeline

    body = {"content": text}
    if params is not None:
        body["params"] = params
    if properties is not None:
        body["properties"] = properties

    r = requests.post(
        url,
        headers={**HEADERS, "Content-Type": "application/json"},
        json=body,
        timeout=60,
        verify=VERIFY,
        params=qp,
    )
    if r.status_code in (200, 201):
        return r.json()

    # Fallback to multipart
    files = {"content": (None, text)}
    if params is not None:
        files["params"] = (None, json.dumps(params, ensure_ascii=True, separators=(",", ":")))
    if properties is not None:
        files["properties"] = (None, json.dumps(properties, ensure_ascii=True, separators=(",", ":")))

    r = requests.post(url, headers=HEADERS, files=files, timeout=60, verify=VERIFY, params=qp)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"Send message failed: {r.status_code} {r.text}")
    return r.json()
