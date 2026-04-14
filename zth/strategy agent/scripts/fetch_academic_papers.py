import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import os
import ssl

def fetch_arxiv_papers(query, max_results=50, output_dir="data/rag_docs/academic"):
    os.makedirs(output_dir, exist_ok=True)
    
    # URL encode the query
    safe_query = urllib.parse.quote(query)
    url = f"http://export.arxiv.org/api/query?search_query=all:{safe_query}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=desc"
    
    print(f"Fetching papers for query: {query}...")
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        response = urllib.request.urlopen(url, context=ctx)
        data = response.read()
        root = ET.fromstring(data)
        
        # arXiv API uses the atom namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        count = 0
        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.replace('\n', ' ').strip()
            summary = entry.find('atom:summary', ns).text.replace('\n', ' ').strip()
            published = entry.find('atom:published', ns).text
            authors = [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)]
            link = entry.find('atom:id', ns).text
            year = published[:4]
            year_dir = os.path.join(output_dir, year)
            os.makedirs(year_dir, exist_ok=True)
            
            # Clean filename
            safe_title = "".join([c if c.isalnum() else "_" for c in title])[:50]
            filename = os.path.join(year_dir, f"{year}_{safe_title}.md")
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"Date: {published[:10]}\n")
                f.write("Category: academic\n")
                f.write("Region: global\n")
                f.write("Keywords: quantitative finance, factor, paper\n")
                f.write("Source: arxiv\n")
                f.write(f"Link: {link}\n")
                f.write(f"Authors: {', '.join(authors)}\n\n")
                f.write(f"## Abstract Summary\n\n{summary}\n")
            count += 1
            
        print(f"Successfully downloaded {count} paper abstracts to year-based folders under {output_dir}")
    except Exception as e:
        print(f"Failed to fetch papers: {e}")

if __name__ == "__main__":
    queries = [
        "quantitative finance alpha factor",
        "machine learning stock return prediction",
        "deep learning high frequency trading",
        "transformer market microstructure"
    ]
    for q in queries:
        fetch_arxiv_papers(q, max_results=20)
