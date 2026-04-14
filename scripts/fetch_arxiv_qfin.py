import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import os
import ssl
import time


def fetch_arxiv_papers(output_dir="data/rag_docs/academic/arxiv_recent"):
    os.makedirs(output_dir, exist_ok=True)

    # Query: quantitative finance category (q-fin), focusing on relevant keywords
    # Note: arXiv API does not support sorting by citation count directly.
    # We will fetch the most recent relevant papers (sorting by submittedDate).
    query = "cat:q-fin.TR OR cat:q-fin.PM OR cat:q-fin.ST OR cat:q-fin.CP"
    safe_query = urllib.parse.quote(query)

    # Fetch 100 papers
    url = f"http://export.arxiv.org/api/query?search_query={safe_query}&start=0&max_results=100&sortBy=submittedDate&sortOrder=desc"

    print("Fetching recent quantitative finance papers from arXiv...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        # Add a delay and User-Agent to avoid 429 Too Many Requests
        time.sleep(2)
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        response = urllib.request.urlopen(req, context=ctx)
        data = response.read()
        root = ET.fromstring(data)

        ns = {"atom": "http://www.w3.org/2005/Atom"}

        count = 0
        for entry in root.findall("atom:entry", ns):
            title = entry.find("atom:title", ns).text.replace("\n", " ").strip()
            summary = entry.find("atom:summary", ns).text.replace("\n", " ").strip()
            published = entry.find("atom:published", ns).text

            authors = [
                author.find("atom:name", ns).text
                for author in entry.findall("atom:author", ns)
            ]
            link = entry.find("atom:id", ns).text

            safe_title = "".join([c if c.isalnum() else "_" for c in title])[:80]
            filename = os.path.join(output_dir, f"{safe_title}.md")

            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"**Authors:** {', '.join(authors)}\n")
                f.write(f"**Published:** {published}\n")
                f.write(f"**Link:** {link}\n\n")
                f.write(f"## Abstract\n\n{summary}\n")
            count += 1

        print(f"Successfully downloaded {count} recent papers to {output_dir}")
    except Exception as e:
        print(f"Failed to fetch papers: {e}")


if __name__ == "__main__":
    fetch_arxiv_papers()
