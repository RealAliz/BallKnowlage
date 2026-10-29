"""One short run: fetch news + tweets, translate, post a few items, exit.
GitHub Actions starts this about once an hour."""
import calendar
import html
import random
import re
import time
import requests
from urllib.parse import urlparse

from common import (
    HEADERS,
    FOOTER,
    get_feed,
    is_top_football,
    load_state,
    make_tags,
    save_state,
    send_photo,
    send_text,
    send_video,
    to_persian,
)
from config import (
    IMAGE_PROBABILITY,
    MAX_VIDEO_MB,
    VIDEO_ENABLED,
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


VIDEO_WORDS = ("ویدیو", "ویدئو", "فیلم", "video", "watch")


def find_video(e):
    """Direct video file given by the feed itself (enclosure / media:content)."""
    for link in e.get("links", []):
        if link.get("rel") == "enclosure" and str(link.get("type", "")).startswith("video"):
            return link.get("href")
    for m in e.get("media_content", []) or []:
        url = m.get("url", "")
        if str(m.get("type", "")).startswith("video") or url.lower().split("?")[0].endswith((".mp4", ".m4v", ".mov")):
            return url
    return None


def looks_like_video(item):
    return any(w in item["title"].lower() for w in VIDEO_WORDS)


def scrape_video(page_url):
    """Look for a direct .mp4 on the article page (og:video or <video>/<source>)."""
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        page = r.text
    except Exception as ex:
        print(f"[warn] could not open article page for video: {ex}")
        return None
    patterns = [
        r'<meta[^>]+property=["\']og:video(?::secure_url|:url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:video(?::secure_url|:url)?["\']',
        r'<(?:video|source)[^>]+src=["\']([^"\']+\.mp4[^"\']*)',
        r'["\'](https?://[^"\' ]+\.mp4[^"\' ]*)["\']',
    ]
    for p in patterns:
        m = re.search(p, page, re.I)
        if m:
            url = html.unescape(m.group(1))
            if ".mp4" in url.lower() or "video" in p:
                return url
    return None


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
                    "video": find_video(e),
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
                    "video": None,
                    "filter": False,
                    "ts": entry_time(e),
                }
            )
    return items


# ---------- posting ----------
def build_message(item, with_summary=True):
    combined = item["title"] + (f"\n\n{item['summary']}" if item["summary"] else "")
    fa = to_persian(combined)
    if fa is None:
        return None
    parts = fa.split("\n\n", 1)
    title_fa = parts[0].strip()
    summary_fa = parts[1].strip() if len(parts) > 1 else ""

    tags = " ".join(make_tags(f'{item["title"]} {item["summary"]} {title_fa} {summary_fa}'))
    src = html.escape(item["source"])
    link = html.escape(item["link"], quote=True)

    if item["kind"] == "tweet":
        msg = f'🗣 <b>{src}</b>\n\n{html.escape(title_fa)}\n\n🔗 <a href="{link}">لینک توییت</a>'
    else:
        msg = f"📰 <b>{html.escape(title_fa)}</b>\n"
        if with_summary and summary_fa and summary_fa != title_fa:
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

    items = collect_news() + collect_tweets()
    items.sort(key=lambda i: i["ts"])  # oldest first
    new = [i for i in items if i["id"] not in state["seen"]]
    print(f"[summary] {len(items)} fresh items, {len(new)} not posted yet, first_run={first_run}")

    if not items:
        print("[error] nothing fetched from any source - check the [warn] lines above")
        save_state(state)
        raise SystemExit(1)  # makes the run show up red in the Actions tab

    now = time.time()
    if first_run:
        for i in new:
            state["seen"][i["id"]] = now
        print("No saved state: marked current items as seen, posting nothing.")
        save_state(state)
        return

    # Persian general sites: only keep top-league football
    keep = []
    for i in new:
        if i["filter"] and not is_top_football(f'{i["title"]} {i["summary"]}'):
            state["seen"][i["id"]] = now
        else:
            keep.append(i)

    # Don't post a stale backlog: keep only the newest items, skip older overflow
    if len(keep) > MAX_POSTS_PER_RUN:
        skipped = keep[:-MAX_POSTS_PER_RUN]
        for i in skipped:
            state["seen"][i["id"]] = now
        print(f"[info] skipping {len(skipped)} older items to avoid a backlog")
        keep = keep[-MAX_POSTS_PER_RUN:]

    posted = fails = 0
    for item in keep:
        if time.time() - start > RUN_BUDGET_SECONDS:
            break  # leftovers go out in the next run
        msg = build_message(item)
        if msg is None:
            fails += 1
            if fails >= 3:
                print("[error] translation keeps failing, stopping this run")
                break
            continue
        try:
            use_image = (
                item["image"]
                and item["kind"] == "news"
                and len(msg) <= 1024
                and random.random() < IMAGE_PROBABILITY
            )
            sent = False
            if VIDEO_ENABLED and item["kind"] == "news":
                video = item["video"] or (scrape_video(item["link"]) if looks_like_video(item) else None)
                if video:
                    caption = msg if len(msg) <= 1024 else build_message(item, with_summary=False)
                    try:
                        send_video(video, caption, MAX_VIDEO_MB)
                        sent = True
                        print("[info] sent as video")
                    except Exception as ex:
                        print(f"[warn] video failed, falling back to photo/text: {ex}")
            if not sent and use_image:
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
