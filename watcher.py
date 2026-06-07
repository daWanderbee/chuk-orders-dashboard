#!/usr/bin/env python3
"""
CHUK order watcher.

Polls the WooCommerce store, compares each order against the last saved
snapshot (order_state.json) and emails on:
  - a brand-new order
  - a status change on an existing order

Designed to run on a schedule (GitHub Actions cron / any cron). State is
persisted to order_state.json so the next run knows what was already seen.

Config via environment variables (set as GitHub Actions secrets):
  WC_USER         WooCommerce REST API key  (consumer key)
  WC_APP_KEY      WooCommerce REST API secret (consumer secret)
  SMTP_HOST       e.g. smtp.gmail.com
  SMTP_PORT       e.g. 465 (SSL) or 587 (STARTTLS)
  SMTP_USER       SMTP login / from address
  SMTP_PASS       SMTP password / app password
  MAIL_TO         recipient (defaults to asmita@pakka.com)
  MAIL_FROM       from address (defaults to SMTP_USER)
"""
import os
import sys
import ssl
import json
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta

import requests
from requests.auth import HTTPBasicAuth

WC_BASE   = "https://chuk.in/wp-json/wc/v3"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "order_state.json")
DAYS_BACK = int(os.getenv("WATCH_DAYS_BACK", "30"))
TIMEOUT   = (10, 45)

WC_FIELDS = ",".join([
    "id", "number", "status", "date_created",
    "billing", "line_items", "total", "payment_method_title",
])

STATUS_EMOJI = {
    "pending": "🟡", "processing": "🔵", "on-hold": "🟣",
    "completed": "🟢", "cancelled": "🔴", "refunded": "🟠", "failed": "⚫",
}


def env(name, default=None, required=False):
    v = os.getenv(name, default)
    if required and not v:
        sys.exit(f"Missing required env var: {name}")
    return v


def fetch_orders():
    auth = HTTPBasicAuth(env("WC_USER", required=True), env("WC_APP_KEY", required=True))
    after = (datetime.now() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%dT00:00:00")
    # _cb busts chuk.in's LiteSpeed server-side REST cache so new/updated orders show
    params = {"per_page": 50, "orderby": "date", "order": "desc",
              "after": after, "_fields": WC_FIELDS, "_cb": int(time.time())}
    out, page = [], 1
    while page <= 20:
        params["page"] = page
        r = requests.get(f"{WC_BASE}/orders", params=params, auth=auth, timeout=TIMEOUT,
                         headers={"Cache-Control": "no-cache"})
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        out.extend(batch)
        if page >= int(r.headers.get("X-WP-TotalPages", 1)) or len(batch) < 50:
            break
        page += 1
    return out


def summarize(o):
    items = o.get("line_items", [])
    is_sample = bool(items) and all("sample kit" in i["name"].lower() for i in items)
    products = "; ".join(f"{i['name']} ×{i['quantity']}" for i in items)
    b = o.get("billing", {})
    return {
        "id":       o["id"],
        "number":   str(o["number"]),
        "status":   o["status"],
        "type":     "Sample Kit" if is_sample else "Website Order",
        "customer": f"{b.get('first_name','')} {b.get('last_name','')}".strip(),
        "email":    b.get("email", ""),
        "phone":    b.get("phone", ""),
        "city":     b.get("city", ""),
        "state":    b.get("state", ""),
        "products": products,
        "total":    float(o.get("total", 0) or 0),
        "payment":  o.get("payment_method_title", ""),
        "date":     o.get("date_created", ""),
    }


def load_state():
    if not os.path.exists(STATE_FILE):
        return None  # signals first run
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def send_mail(subject, body):
    host = env("SMTP_HOST", required=True)
    port = int(env("SMTP_PORT", "465"))
    user = env("SMTP_USER", required=True)
    pwd  = env("SMTP_PASS", required=True)
    to   = env("MAIL_TO", "asmita@pakka.com")
    frm  = env("MAIL_FROM", user)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = frm
    msg["To"] = to
    msg.set_content(body)

    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(user, pwd)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(user, pwd)
            s.send_message(msg)
    print(f"  mail sent → {to}: {subject}")


def order_block(s):
    em = STATUS_EMOJI.get(s["status"], "•")
    return (
        f"Order      : #{s['number']}  ({s['type']})\n"
        f"Status     : {em} {s['status'].upper()}\n"
        f"Customer   : {s['customer']}\n"
        f"Email      : {s['email']}\n"
        f"Phone      : {s['phone']}\n"
        f"Location   : {s['city']}, {s['state']}\n"
        f"Products   : {s['products']}\n"
        f"Total      : ₹{s['total']:,.0f}\n"
        f"Payment    : {s['payment']}\n"
        f"Placed     : {s['date']}\n"
    )


def main():
    print(f"[{datetime.now().isoformat(timespec='seconds')}] CHUK watcher run")
    orders = [summarize(o) for o in fetch_orders()]
    current = {str(s["id"]): s for s in orders}
    print(f"  fetched {len(current)} orders (last {DAYS_BACK}d)")

    prev = load_state()

    # First run: seed state silently, no mail flood.
    if prev is None:
        save_state(current)
        print(f"  first run — seeded {len(current)} orders, no mail sent")
        return

    new_count = changed_count = 0
    for oid, s in current.items():
        old = prev.get(oid)
        if old is None:
            send_mail(
                f"🆕 New CHUK order #{s['number']} — ₹{s['total']:,.0f} ({s['type']})",
                "A new order just came in:\n\n" + order_block(s),
            )
            new_count += 1
        elif old.get("status") != s["status"]:
            o_em = STATUS_EMOJI.get(old.get("status",""), "•")
            n_em = STATUS_EMOJI.get(s["status"], "•")
            send_mail(
                f"🔄 CHUK order #{s['number']} status: "
                f"{old.get('status','?')} → {s['status']}",
                f"Order status changed:\n\n"
                f"  {o_em} {old.get('status','?').upper()}  →  {n_em} {s['status'].upper()}\n\n"
                + order_block(s),
            )
            changed_count += 1

    save_state(current)
    print(f"  done — {new_count} new, {changed_count} status changes")


if __name__ == "__main__":
    main()
