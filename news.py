"""One short run: fetch news + tweets, translate, post a few items, exit.
GitHub Actions starts this about once an hour."""
import calendar
import html
import random
import re
import time
from urllib.parse import urlparse

from common import (
    FOOTER,
    get_feed,
    is_top_football,
    load_state,
    make_tags,
    save_state,
    send_photo,
    send_text,
    to_persian,
)
from config import (
    IMAGE_PROBABILITY,
    MAX_AGE_HOURS,
    MAX_POSTS_PER_RUN,
    POST_ON_FIRST_RUN,
    NEWS_FEEDS,
    NITTER_INSTANCES,
    POST_GAP_SECONDS,
    RUN_BUDGET_SECONDS,
    X_ACCOUNTS,
)


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def entry_time(e):
    t = e.get("published_parsed") or e.get("updated_parsed")
    return calendar.timegm(t) if t else time.time()


def is_fresh(e):
    return time.time() - entry_time(e) < MAX_AGE_HOURS * 3600


def find_image(e):
    for key in ("media_content", "media_thumbnail"):
        for m in e.get(key, []) or []:
            if m.get("url"):
                return m["url"]
    for link in e.get("links", []):
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("image"):
            return link.get("href")
    m = re.search(r'<img[^>]+src="([^"]+)"', e.get("summary", "") or "")
    return m.group(1) if m else None


# ---------- collecting ----------
def collect_news():
    items = []
    for feed in NEWS_FEEDS:
        try:
            parsed = get_feed(feed["url"])
        except Exception as ex:
            print(f"[warn] feed {feed['name']} failed: {ex}")
            continue
        fresh = [e for e in parsed.entries if is_fresh(e)]
        print(f"[feed] {feed['name']}: {len(parsed.entries)} entries, {len(fresh)} fresh")
        for e in fresh:
            link = e.get("link", "")
            items.append(
                {
                    "id": e.get("id") or link,
                    "kind": "news",
                    "source": feed["name"],
                    "title": clean(e.get("title", "")),
                    "summary": clean(e.get("summary", ""))[:400],
                    "link": link,
                    "image": find_image(e),
                    "filter": feed.get("filter", False),
                    "ts": entry_time(e),
                }
            )
    return items


def collect_tweets():
    items = []
    for user in X_ACCOUNTS:
        entries, host = [], None
        for base in NITTER_INSTANCES:
            try:
                parsed = get_feed(f"{base}/{user}/rss")
            except Exception:
                continue
            if parsed.entries:
                entries, host = parsed.entries, urlparse(base).netloc
                break
        if not entries:
            print(f"[warn] no tweets for @{user} (all Nitter instances failed)")
            continue
        for e in entries:
            title = clean(e.get("title", ""))
            if title.startswith(("RT by", "R to")) or not is_fresh(e):
                continue
            link = (e.get("link", "") or "").replace(host, "x.com").split("#")[0]
            link = link.replace("http://", "https://")
            items.append(
                {
                    "id": f"x:{user}:{link}",
                    "kind": "tweet",
                    "source": f"@{user}",
                    "title": title,
                    "summary": "",
                    "link": link,
                    "image": None,
                    "filter": False,
                    "ts": entry_time(e),
                }
            )
    return items


# ---------- posting ----------
def build_message(item):
    title_fa = to_persian(item["title"])
    if title_fa is None:
        return None
    summary_fa = to_persian(item["summary"]) if item["summary"] else ""
    summary_fa = summary_fa or ""

    tags = " ".join(make_tags(f'{item["title"]} {item["summary"]} {title_fa} {summary_fa}'))
    src = html.escape(item["source"])
    link = html.escape(item["link"], quote=True)

    if item["kind"] == "tweet":
        msg = f'🗣 <b>{src}</b>\n\n{html.escape(title_fa)}\n\n🔗 <a href="{link}">لینک توییت</a>'
    else:
        msg = f"📰 <b>{html.escape(title_fa)}</b>\n"
        if summary_fa and summary_fa != title_fa:
            msg += f"\n{html.escape(summary_fa)}\n"
        msg += f'\n📌 منبع: <a href="{link}">{src}</a>'
    if tags:
        msg += f"\n\n{tags}"
    if FOOTER:
        msg += f"\n{html.escape(FOOTER)}"
    return msg


def main():
    start = time.time()
    state = load_state()
    first_run = not state["seen"] and not POST_ON_FIRST_RUN
    if first_run:
        print("No saved state: marking current items as seen, posting nothing.")

    items = collect_news() + collect_tweets()
    items.sort(key=lambda i: i["ts"])  # oldest first
    posted = 0
    new_count = sum(1 for i in items if i["id"] not in state["seen"])
    print(f"[summary] {len(items)} fresh items, {new_count} not posted yet, first_run={first_run}")
    if not items:
        print("[error] nothing fetched from any source - check the [warn] lines above")
        save_state(state)
        raise SystemExit(1)  # makes the run show up red in the Actions tab

    for item in items:
        if item["id"] in state["seen"]:
            continue
        if first_run:
            state["seen"][item["id"]] = time.time()
            continue
        if posted >= MAX_POSTS_PER_RUN or time.time() - start > RUN_BUDGET_SECONDS:
            break  # leftovers go out in the next run

        # Persian general sites: only keep top-league football
        if item["filter"] and not is_top_football(f'{item["title"]} {item["summary"]}'):
            state["seen"][item["id"]] = time.time()
            continue

        msg = build_message(item)
        if msg is None:
            continue  # translation failed, try again next run
        try:
            use_image = (
                item["image"]
                and item["kind"] == "news"
                and len(msg) <= 1024
                and random.random() < IMAGE_PROBABILITY
            )
            sent = False
            if use_image:
                try:
                    send_photo(item["image"], msg)
                    sent = True
                except Exception as ex:
                    print(f"[warn] photo failed, sending text instead: {ex}")
            if not sent:
                send_text(msg)
            state["seen"][item["id"]] = time.time()
            posted += 1
            print(f"posted: {item['title'][:70]}")
            time.sleep(random.randint(*POST_GAP_SECONDS))
        except Exception as ex:
            print(f"[error] send failed: {ex}")

    save_state(state)
    print(f"done, posted {posted} item(s) in {int(time.time() - start)}s")


if __name__ == "__main__":
    main()
