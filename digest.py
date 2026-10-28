"""Morning digest: results of the last ~24h + today's schedule, in Persian.
Data: football-data.org (free API key in the FOOTBALL_DATA_KEY secret)."""
import html
import os
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from common import FOOTER, HEADERS, send_text, to_persian
from config import LEAGUES, TEAM_FA, TIMEZONE, TIMEZONE_LABEL

FD_KEY = os.environ.get("FOOTBALL_DATA_KEY", "")
TZ = ZoneInfo(TIMEZONE)
RLM = "\u200f"  # right-to-left mark so lines start on the right
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
_name_cache = {}


def fa_num(value):
    return str(value).translate(FA_DIGITS)


def team_fa(team):
    name = team.get("name") or ""
    short = team.get("shortName") or ""
    stripped = name.replace(" FC", "").replace("FC ", "").replace(" CF", "").strip()
    for key in (name, short, stripped):
        if key in TEAM_FA:
            return TEAM_FA[key]
    label = short or name
    if label not in _name_cache:
        _name_cache[label] = to_persian(label) or label
    return _name_cache[label]


def fetch_matches(codes, d_from, d_to):
    r = requests.get(
        "https://api.football-data.org/v4/matches",
        params={"dateFrom": d_from.isoformat(), "dateTo": d_to.isoformat(), "competitions": ",".join(codes)},
        headers={**HEADERS, "X-Auth-Token": FD_KEY},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("matches", [])


def parse(m):
    try:
        ft = (m.get("score") or {}).get("fullTime") or {}
        return {
            "code": m["competition"]["code"],
            "home": m["homeTeam"],
            "away": m["awayTeam"],
            "hs": ft.get("home"),
            "as": ft.get("away"),
            "kick": datetime.fromisoformat(m["utcDate"].replace("Z", "+00:00")).astimezone(TZ),
            "status": m.get("status"),
        }
    except Exception as ex:
        print(f"[warn] could not parse match: {ex}")
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
    if not FD_KEY:
        print("[error] FOOTBALL_DATA_KEY secret is missing (free key from football-data.org)")
        raise SystemExit(1)

    now = datetime.now(TZ)
    today = now.date()
    try:
        raw = fetch_matches([l[0] for l in LEAGUES], today - timedelta(days=1), today + timedelta(days=1))
    except Exception as ex:
        print(f"[error] could not fetch matches: {ex}")
        raise SystemExit(1)
    matches = [m for m in (parse(x) for x in raw) if m]
    print(f"[info] {len(matches)} matches fetched")

    result_blocks, schedule_blocks = [], []
    result_tags, schedule_tags = [], []

    for code, name, emoji, tag in LEAGUES:
        mine = [m for m in matches if m["code"] == code]
        done = [
            m for m in mine
            if m["status"] == "FINISHED" and m["hs"] is not None
            and timedelta(0) <= now - m["kick"] <= timedelta(hours=24)
        ]
        upcoming = [m for m in mine if m["status"] in ("SCHEDULED", "TIMED") and m["kick"].date() == today]

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
        msgs = chunk(["🏁 <b>نتایج بازی‌های دیشب</b>\n"] + result_blocks)
        msgs[-1] += "\n#نتایج " + " ".join(result_tags) + footer
        for m in msgs:
            send_text(m)
            time.sleep(3)
    else:
        print("[info] no results to post")

    if schedule_blocks:
        msgs = chunk([f"📅 <b>برنامه بازی‌های امروز</b>\n({html.escape(TIMEZONE_LABEL)})\n"] + schedule_blocks)
        msgs[-1] += "\n#برنامه_بازی_ها " + " ".join(schedule_tags) + footer
        for m in msgs:
            send_text(m)
            time.sleep(3)
    else:
        print("[info] no matches today")


if __name__ == "__main__":
    main()
