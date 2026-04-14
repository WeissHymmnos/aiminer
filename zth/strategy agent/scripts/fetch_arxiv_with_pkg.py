import arxiv
import os
import re

def fetch_arxiv_papers():
    output_dir = "data/rag_docs/academic/arxiv_recent"
    os.makedirs(output_dir, exist_ok=True)
    
    # We will search for Portfolio Management (q-fin.PM) or Statistical Finance (q-fin.ST) or Trading (q-fin.TR)
    # The arxiv package makes this much easier
    query = "cat:q-fin.PM OR cat:q-fin.ST OR cat:q-fin.TR"
    
    print(f"Querying arXiv for: {query}")
    
    # Construct the client
    client = arxiv.Client()
    
    # Define the search
    search = arxiv.Search(
        query=query,
        max_results=50,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    count = 0
    for result in client.results(search):
        title = result.title.replace('\n', ' ').strip()
        summary = result.summary.replace('\n', ' ').strip()
        published = result.published.strftime("%Y-%m-%d")
        authors = [author.name for author in result.authors]
        link = result.entry_id
        
        # Clean title for filename
        safe_title = re.sub(r'[^A-Za-z0-9]+', '_', title)[:80]
        filename = os.path.join(output_dir, f"{safe_title}.md")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"**Authors:** {', '.join(authors)}\n")
            f.write(f"**Published:** {published}\n")
            f.write(f"**Link:** {link}\n\n")
            f.write(f"## Abstract\n\n{summary}\n")
            
        count += 1
        print(f"Downloaded: {title[:50]}...")
        
    print(f"Successfully saved {count} recent papers to {output_dir}")

if __name__ == "__main__":
    try:
        fetch_arxiv_papers()
    except Exception as e:
        print(f"Error: {e}")
