import os
from typing import List, Dict
from openai import AsyncOpenAI
import anthropic

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")

_openai_client = None
_anth_client = None
_chat_history: List[Dict[str, str]] = []

def llm_status() -> str:
    has_oai = bool(os.getenv("OPENAI_API_KEY"))
    has_an = bool(os.getenv("ANTHROPIC_API_KEY"))
    prov = LLM_PROVIDER
    return ("🤖 LLM:\n"
            f"• provider: {prov}\n"
            f"• openai: {'✅' if has_oai else '❌'} (model: {OPENAI_MODEL})\n"
            f"• anthropic: {'✅' if has_an else '❌'} (model: {ANTHROPIC_MODEL})")

async def _ensure_clients():
    global _openai_client, _anth_client
    if _openai_client is None and os.getenv("OPENAI_API_KEY"):
        _openai_client = AsyncOpenAI()
    if _anth_client is None and os.getenv("ANTHROPIC_API_KEY"):
        _anth_client = anthropic.AsyncAnthropic()

async def ask_once(prompt: str) -> str:
    await _ensure_clients()
    if LLM_PROVIDER == "anthropic" and _anth_client:
        resp = await _anth_client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=800, temperature=0.3,
            messages=[{"role":"user","content":prompt}]
        )
        return "".join(getattr(block, "text", "") for block in resp.content)
    elif LLM_PROVIDER == "openai" and _openai_client:
        resp = await _openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role":"system","content":"Ты краткий, точный помощник."},
                      {"role":"user","content":prompt}],
            temperature=0.3, max_tokens=800
        )
        return resp.choices[0].message.content.strip()
    else:
        return "LLM не настроен: проверь ключи и LLM_PROVIDER."

async def chat_reply(user_msg: str) -> str:
    await _ensure_clients()
    _chat_history.append({"role":"user","content":user_msg})
    if len(_chat_history) > 24:
        del _chat_history[:len(_chat_history)-24]

    if LLM_PROVIDER == "anthropic" and _anth_client:
        resp = await _anth_client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=900, temperature=0.6,
            messages=[{"role":m["role"], "content":m["content"]} for m in _chat_history]
        )
        text = "".join(getattr(block, "text", "") for block in resp.content)
    elif LLM_PROVIDER == "openai" and _openai_client:
        msgs = [{"role":"system","content":"Ты диалоговый ассистент. Отвечай по делу."}] + _chat_history
        resp = await _openai_client.chat.completions.create(
            model=OPENAI_MODEL, messages=msgs, temperature=0.6, max_tokens=900
        )
        text = resp.choices[0].message.content.strip()
    else:
        text = "LLM не настроен: проверь ключи и LLM_PROVIDER."
    _chat_history.append({"role":"assistant","content":text})
    return text

def reset_chat():
    _chat_history.clear()
