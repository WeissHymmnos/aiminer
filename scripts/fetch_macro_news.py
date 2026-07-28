import os
import argparse
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from html import unescape
import re
from urllib.parse import quote
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


DEFAULT_MARKET_WINDOW_DAYS = 365
DEFAULT_MARKET_LOOKBACK_DAYS = 365
DEFAULT_NEWS_LIMIT = 24
DEFAULT_OUTPUT_DIR = "data/rag_docs/macro_news"
NEWS_QUERIES = [
    ("中国 央行 利率 通胀", "monetary_policy"),
    ("中国 PMI 出口 贸易", "trade_activity"),
    ("A股 市场 波动 成交量", "equity_market"),
    ("中国 财政 政策 基建 消费", "fiscal_demand"),
]


def resolve_market_window(start_date=None, end_date=None, default_days=DEFAULT_MARKET_WINDOW_DAYS):
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else (end_dt - timedelta(days=default_days))
    if start_dt > end_dt:
        raise ValueError("market start date must be earlier than or equal to market end date")
    return start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")


def _strip_html(text):
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _build_google_news_url(query, start_date, end_date):
    end_plus_one = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    search_query = f"{query} after:{start_date} before:{end_plus_one}"
    return (
        "https://news.google.com/rss/search?"
        f"q={quote(search_query)}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    )


def _fetch_google_news(query, start_date, end_date):
    request = Request(
        _build_google_news_url(query, start_date, end_date),
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
            )
        },
    )

    with urlopen(request, timeout=20) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    channel = root.find("channel")
    if channel is None:
        return []

    start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    items = []

    for item in channel.findall("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_raw = (item.findtext("pubDate") or "").strip()
        summary = _strip_html(item.findtext("description") or "")
        source = (item.findtext("source") or "Google News").strip()

        try:
            published_at = parsedate_to_datetime(pub_raw)
            published_date = published_at.date()
        except (TypeError, ValueError, IndexError):
            published_date = None

        if published_date and not (start_dt <= published_date <= end_dt):
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "published_date": published_date.isoformat() if published_date else "",
                "published_at": pub_raw,
                "source": source,
                "summary": summary,
                "query": query,
            }
        )

    return items


def fetch_and_persist_macro_news(start_date, end_date, max_articles=DEFAULT_NEWS_LIMIT, output_dir=DEFAULT_OUTPUT_DIR):
    os.makedirs(output_dir, exist_ok=True)

    articles = []
    seen_keys = set()
    for query, topic in NEWS_QUERIES:
        for item in _fetch_google_news(query, start_date, end_date):
            key = (item["title"], item["link"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            item["topic"] = topic
            articles.append(item)

    articles.sort(key=lambda item: item.get("published_date", ""), reverse=True)
    articles = articles[:max_articles]

    for index, item in enumerate(articles):
        published_date = item["published_date"] or datetime.now().strftime("%Y-%m-%d")
        year = published_date[:4]
        year_dir = os.path.join(output_dir, year)
        os.makedirs(year_dir, exist_ok=True)
        file_name = f"{published_date}_{item['topic']}_{index:02d}.md"
        with open(os.path.join(year_dir, file_name), "w", encoding="utf-8") as file_obj:
            file_obj.write(f"# {item['title']}\n\n")
            file_obj.write(f"Date: {published_date}\n")
            file_obj.write("Category: macro_news\n")
            file_obj.write("Region: CN\n")
            file_obj.write(f"Keywords: {item['topic']}, macro, policy, news\n")
            file_obj.write(f"Source: {item['source']}\n")
            file_obj.write(f"Query: {item['query']}\n")
            file_obj.write(f"Link: {item['link']}\n\n")
            file_obj.write("## Summary\n\n")
            file_obj.write(f"{item['summary'] or 'No summary provided by feed.'}\n")

    print(f"Fetched {len(articles)} real macro news articles in year-based folders under {output_dir}")
    return len(articles)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch real macro news articles.")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD). Defaults to one year before end date.")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--count", type=int, default=DEFAULT_NEWS_LIMIT, help="Maximum number of articles to persist.")
    args = parser.parse_args()

    start_date, end_date = resolve_market_window(args.start, args.end)
    fetch_and_persist_macro_news(start_date, end_date, max_articles=args.count)
