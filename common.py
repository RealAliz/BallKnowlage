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

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]  # e.g. @mychannel
FOOTER = os.environ.get("CHANNEL_FOOTER", "")  # e.g. @mychannel
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


def to_persian(text):
    """Returns Persian text, the same text if already Persian, or None on failure."""
    if not text:
        return ""
    if is_persian(text):
        return text
    for attempt in range(3):
        try:
            return _translator.translate(text[:4500])
        except Exception as ex:
            print(f"translate failed ({ex}), retry {attempt + 1}")
            time.sleep(2 * (attempt + 1))
    return None


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
