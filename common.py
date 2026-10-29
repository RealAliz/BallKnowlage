import json
import os
import re
import time

import feedparser
import requests
from deep_translator import GoogleTranslator

from config import LEAGUE_TAGS, TEAM_TAGS, TOPIC_TAGS

try:  # optional, only for running locally with a .env file
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BOT_TOKEN = os.environ["BOT_TOKEN"].strip()
CHANNEL_ID = os.environ["CHANNEL_ID"].strip()  # e.g. @mychannel
FOOTER = os.environ.get("CHANNEL_FOOTER", "").strip()  # e.g. @mychannel
# Optional: better, more reliable translation with the Claude API (secret ANTHROPIC_API_KEY)
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
TRANSLATE_MODEL = os.environ.get("TRANSLATE_MODEL", "claude-haiku-5-5").strip()
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FootballNewsBot/1.0)"}
STATE_FILE = "state.json"

_translator = GoogleTranslator(source="auto", target="fa")


# ---------- state (remembers what was already posted) ----------
def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        state.setdefault("seen", {})
        return state
    except Exception:
        return {"seen": {}}


def save_state(state):
    cutoff = time.time() - 3 * 86400
    state["seen"] = {k: v for k, v in state["seen"].items() if v > cutoff}
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


# ---------- feeds ----------
def get_feed(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return feedparser.parse(r.content)


# ---------- translation ----------
def is_persian(text):
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return False
    fa = sum(1 for c in letters if "\u0600" <= c <= "\u06ff")
    return fa / len(letters) > 0.5


_google_blocked = False


def _google(text):
    """Free Google Translate. From GitHub's shared servers it is often rate-limited."""
    global _google_blocked
    if _google_blocked:
        return None
    for attempt in range(2):
        try:
            time.sleep(0.7)  # stay under Google's 5 requests/second
            return _translator.translate(text[:4500])
        except Exception as ex:
            if "too many requests" in str(ex).lower() or "429" in str(ex):
                print("[warn] Google Translate is rate-limiting this server; no more translations this run")
                _google_blocked = True
                return None
            print(f"[warn] google translate failed ({ex})")
            time.sleep(2)
    return None


def _claude(text):
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": TRANSLATE_MODEL,
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Translate this football news text into natural, fluent Persian (Farsi), "
                            "in the style of a sports news channel. Use the common Persian forms of "
                            "club, player and competition names. Keep the blank line between title and "
                            "summary if there is one. Output only the translation.\n\n" + text
                        ),
                    }
                ],
            },
            timeout=60,
        )
        if not r.ok:
            print(f"[warn] Claude translate failed: {r.status_code} {r.text[:200]}")
            return None
        return r.json()["content"][0]["text"].strip()
    except Exception as ex:
        print(f"[warn] Claude translate failed: {ex}")
        return None


def to_persian(text):
    """Persian text, the same text if already Persian, or None if translation failed."""
    if not text:
        return ""
    if is_persian(text):
        return text
    if ANTHROPIC_KEY:
        out = _claude(text)
        if out:
            return out
    return _google(text)


# ---------- hashtags ----------
def _match(rules, text):
    return [tag for pattern, tag in rules if re.search(pattern, text, re.I)]


def is_top_football(text):
    """True if text mentions a known top-league club/player/league."""
    return bool(_match(TEAM_TAGS, text) or _match(LEAGUE_TAGS, text))


def make_tags(text):
    tags = _match(TEAM_TAGS, text)[:2] + _match(LEAGUE_TAGS, text)[:1] + _match(TOPIC_TAGS, text)[:1]
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# ---------- Telegram ----------
def tg(method, payload):
    for _ in range(3):
        r = requests.post(f"{API}/{method}", json=payload, timeout=30)
        if not r.ok:
            print(f"[telegram] {r.status_code}: {r.text[:300]}")
        if r.status_code == 429:
            wait = r.json().get("parameters", {}).get("retry_after", 5) + 1
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Telegram rate limit")


def send_text(text):
    tg(
        "sendMessage",
        {
            "chat_id": CHANNEL_ID,
            "text": text[:4096],
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        },
    )


def send_photo(url, caption):
    tg(
        "sendPhoto",
        {"chat_id": CHANNEL_ID, "photo": url, "caption": caption, "parse_mode": "HTML"},
    )


def send_video(url, caption, max_mb=45):
    """Send a video: first let Telegram fetch the URL, else download and upload it ourselves."""
    try:
        tg(
            "sendVideo",
            {
                "chat_id": CHANNEL_ID,
                "video": url,
                "caption": caption,
                "parse_mode": "HTML",
                "supports_streaming": True,
            },
        )
        return
    except Exception as ex:
        print(f"[info] sendVideo by URL failed ({ex}); trying download + upload")
    limit = max_mb * 1024 * 1024
    r = requests.get(url, headers=HEADERS, stream=True, timeout=60)
    r.raise_for_status()
    if int(r.headers.get("Content-Length") or 0) > limit:
        raise RuntimeError("video too large")
    data = bytearray()
    for part in r.iter_content(1 << 20):
        data += part
        if len(data) > limit:
            raise RuntimeError("video too large")
    resp = requests.post(
        f"{API}/sendVideo",
        data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML", "supports_streaming": "true"},
        files={"video": ("video.mp4", bytes(data), "video/mp4")},
        timeout=300,
    )
    if not resp.ok:
        print(f"[telegram] {resp.status_code}: {resp.text[:300]}")
    resp.raise_for_status()
