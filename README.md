# Football news -> Persian Telegram bot (GitHub Actions)

## What runs when
- `news.yml`: once an hour (minute 17 UTC). One short run: fetch, translate, post up to 8 items
  spaced 20-45 s apart, then exit (~2-5 min). Already-posted items are remembered on a `state` branch.
- `digest.yml`: every day 04:30 UTC (08:00 Tehran): last night's results, then today's schedule.

## Setup
1. Create a GitHub repo and upload all these files (keep the `.github/workflows` folder).
2. Repo > Settings > Secrets and variables > Actions > New repository secret:
   - `BOT_TOKEN` : token from @BotFather
   - `CHANNEL_ID`: your channel @username (e.g. `@mychannel`)
3. Add your bot as an admin of the channel (permission: post messages).
4. Actions tab > enable workflows > run "News" once manually (first run only records current news,
   posts nothing), then run "Morning digest" manually to test it.

## Keeping the account safe
- Keep runs short and infrequent (hourly is fine; don't go below 15-30 minutes).
- Never loop or sleep for hours inside a job; `timeout-minutes` is a safety net.
- One repo, one account. Don't create forks/accounts to get more minutes.
- Public repos: free unlimited minutes. Private repos: 2,000 free min/month, so run every 2 hours.
- GitHub may disable scheduled workflows after 60 days without repo activity; re-enable in the Actions tab.
- Schedules are in UTC and can start late.

## Local test
`pip install -r requirements.txt`, copy `.env.example` to `.env`, then `python news.py` or `python digest.py`.
