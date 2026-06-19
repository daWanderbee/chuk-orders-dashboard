# CHUK Orders Dashboard

Next.js (App Router, TypeScript) dashboard for chuk.in WooCommerce orders,
deployed on **Vercel**. Replaces the old Streamlit app.

## Architecture

- `app/api/orders` — serverless route, server-side WooCommerce fetch (holds the
  REST keys, never exposed to the browser). Paginated, with the LiteSpeed
  cache-buster + retry logic ported from the Streamlit `fetch_orders`.
- `app/api/orders/[id]` — `PUT` to flip an order between `completed`/`processing`
  (the ✓ Done tick).
- `middleware.ts` + `app/api/login` — password gate via httpOnly cookie. Unset
  `APP_PASSWORD` → dashboard is fully open.
- `components/Dashboard.tsx` — client UI: theme (dark/light), filters, KPIs,
  Website/Sample tabs, searchable order table, CSV export, Recharts analytics.
- `watcher.py` + `.github/workflows/order-watcher.yml` — **unchanged.** The email
  watcher still runs as a GitHub Actions cron, independent of the dashboard host.

## Local dev

```bash
npm install
cp .env.example .env.local   # fill in WC_USER, WC_APP_KEY, APP_PASSWORD
npm run dev                  # http://localhost:3000
```

## Deploy to Vercel

1. Import the repo at vercel.com (framework auto-detected as Next.js).
2. Add Environment Variables (Production + Preview):
   - `WC_USER` — WooCommerce consumer key (`ck_…`)
   - `WC_APP_KEY` — WooCommerce consumer secret (`cs_…`)
   - `APP_PASSWORD` — dashboard password (omit to leave open)
3. Deploy. No keep-awake cron needed — Vercel functions don't sleep.

## Env vars

| Var | Purpose |
| --- | --- |
| `WC_USER` | WooCommerce REST consumer key |
| `WC_APP_KEY` | WooCommerce REST consumer secret |
| `APP_PASSWORD` | Dashboard login password (optional) |
