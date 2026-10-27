"""Morning digest: results of the last ~24h + today's schedule, in Persian.
Data: ESPN's public scoreboard endpoint (no API key)."""
import html
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from common import FOOTER, HEADERS, send_text, to_persian
from config import LEAGUES, TEAM_FA, TIMEZONE, TIMEZONE_LABEL

TZ = ZoneInfo(TIMEZONE)
RLM = "\u200f"  # right-to-left mark so lines start on the right
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_name_cache = {}


def fa_num(value):
    return str(value).translate(FA_DIGITS)


def team_fa(name):
    if name in TEAM_FA:
        return TEAM_FA[name]
    if name not in _name_cache:
        _name_cache[name] = to_persian(name) or name
    return _name_cache[name]


def fetch_events(code, dates):
    events = {}
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{code}/scoreboard"
    for d in dates:
        try:
            r = requests.get(url, params={"dates": d.strftime("%Y%m%d")}, headers=HEADERS, timeout=20)
            r.raise_for_status()
            for ev in r.json().get("events", []):
                events[ev["id"]] = ev
        except Exception as ex:
            print(f"[warn] {code} {d}: {ex}")
    return list(events.values())


def parse(ev):
    try:
        comp = ev["competitions"][0]
        home = next(c for c in comp["competitors"] if c["homeAway"] == "home")
        away = next(c for c in comp["competitors"] if c["homeAway"] == "away")
        kick = datetime.fromisoformat(ev["date"].replace("Z", "+00:00")).astimezone(TZ)
        st = ev["status"]["type"]
        return {
            "home": home["team"]["displayName"],
            "away": away["team"]["displayName"],
            "hs": home.get("score", "0"),
            "as": away.get("score", "0"),
            "kick": kick,
            "state": st.get("state"),
            "completed": bool(st.get("completed")),
        }
    except Exception as ex:
        print(f"[warn] could not parse event: {ex}")
        return None


def chunk(blocks, limit=3800):
    """Group blocks of text into messages under Telegram's length limit."""
    messages, current = [], ""
    for b in blocks:
        if current and len(current) + len(b) > limit:
            messages.append(current)
            current = ""
        current += b
    if current:
        messages.append(current)
    return messages


def main():
    now = datetime.now(TZ)
    today = now.date()
    dates = [today - timedelta(days=1), today, today + timedelta(days=1)]

    result_blocks, schedule_blocks = [], []
    result_tags, schedule_tags = [], []

    for code, name, emoji, tag in LEAGUES:
        matches = [m for m in (parse(e) for e in fetch_events(code, dates)) if m]

        done = [m for m in matches if m["completed"] and timedelta(0) <= now - m["kick"] <= timedelta(hours=24)]
        upcoming = [m for m in matches if m["state"] == "pre" and m["kick"].date() == today]

        if done:
            lines = [f"\n{emoji} <b>{html.escape(name)}</b>"]
            for m in sorted(done, key=lambda x: x["kick"]):
                lines.append(
                    f"{RLM}{html.escape(team_fa(m['home']))} {fa_num(m['hs'])} - {fa_num(m['as'])} {html.escape(team_fa(m['away']))}"
                )
            result_blocks.append("\n".join(lines) + "\n")
            result_tags.append(tag)

        if upcoming:
            lines = [f"\n{emoji} <b>{html.escape(name)}</b>"]
            for m in sorted(upcoming, key=lambda x: x["kick"]):
                lines.append(
                    f"{RLM}⏰ {fa_num(m['kick'].strftime('%H:%M'))}  {html.escape(team_fa(m['home']))} - {html.escape(team_fa(m['away']))}"
                )
            schedule_blocks.append("\n".join(lines) + "\n")
            schedule_tags.append(tag)

    footer = f"\n{html.escape(FOOTER)}" if FOOTER else ""

    if result_blocks:
        header = ["🏁 <b>نتایج بازی‌های دیشب</b>\n"]
        msgs = chunk(header + result_blocks)
        msgs[-1] += "\n#نتایج " + " ".join(result_tags) + footer
        for m in msgs:
            send_text(m)
            time.sleep(3)
    else:
        print("no results to post")

    if schedule_blocks:
        header = [f"📅 <b>برنامه بازی‌های امروز</b>\n({html.escape(TIMEZONE_LABEL)})\n"]
        msgs = chunk(header + schedule_blocks)
        msgs[-1] += "\n#برنامه_بازی_ها " + " ".join(schedule_tags) + footer
        for m in msgs:
            send_text(m)
            time.sleep(3)
    else:
        print("no matches today")


if __name__ == "__main__":
    main()
