import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote

import feedparser
import pandas as pd
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

KEYWORDS = [
    "battery","lithium","CATL","LG Energy Solution","LGES","Samsung SDI",
    "SK On","Panasonic Energy","Tesla battery","BYD battery","ESS","BESS"
]

HEADERS = {"User-Agent": "Mozilla/5.0"}

KST = timezone(timedelta(hours=9))
TODAY = datetime.now(KST).date()

def is_today(date_str):
    try:
        d = parsedate_to_datetime(date_str)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(KST).date() == TODAY
    except:
        return False

def get_real_url(url):
    try:
        return requests.get(url, headers=HEADERS, timeout=5).url
    except:
        return url

def score(title):
    t = title.lower()
    s = 0
    for w in ["plant","factory","capacity","deal","order","earnings","policy","investment"]:
        if w in t:
            s += 3
    return s

def summary(title):
    t = title.lower()

    if "plant" in t or "capacity" in t:
        return "생산능력 확대 → 공급 증가 영향"
    if "deal" in t or "order" in t:
        return "수주/계약 → 매출 가시성 증가"
    if "earnings" in t or "profit" in t:
        return "실적 관련 → 주가 변동성 영향"
    if "policy" in t or "tariff" in t:
        return "정책 영향 → 업황 방향성 변화 가능"
    if "ess" in t or "storage" in t:
        return "ESS 수요 관련 뉴스"
    if "lithium" in t:
        return "리튬 가격/공급 영향"

    return "배터리 업황 참고 뉴스"

def send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    })

rows = []

for kw in KEYWORDS:
    url = f"https://news.google.com/rss/search?q={quote(kw)}&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(requests.get(url, headers=HEADERS).text)

    for e in feed.entries:
        title = e.get("title","")
        link = e.get("link","")
        date = e.get("published","")

        if ("Reuters" not in title) and ("Bloomberg" not in title):
            continue
        if not is_today(date):
            continue

        rows.append({
            "title": title,
            "link": get_real_url(link),
            "score": score(title),
            "summary": summary(title)
        })

    time.sleep(1)

# 중복 제거
unique = {}
for r in rows:
    unique[r["title"]] = r

data = list(unique.values())
data.sort(key=lambda x: x["score"], reverse=True)

send_list = data[:7]

if len(send_list) == 0:
    send("오늘 배터리 뉴스 없음")
else:
    msg = "📌 오늘 배터리 중요 뉴스\n\n"

    for i, r in enumerate(send_list,1):
        msg += f"{i}. {r['title']}\n👉 {r['summary']}\n{r['link']}\n\n"

    send(msg)

print("완료")
