import os
import pandas as pd
import argparse
from datetime import datetime, timedelta
import random

def generate_macro_news(start_date, end_date, articles_per_week=3, output_dir="data/rag_docs/macro_news"):
    os.makedirs(output_dir, exist_ok=True)
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    current_week_start = start - timedelta(days=start.weekday())
    
    news_templates = [
        {
            "title": "Central Bank Signals Potential Shift in Monetary Policy",
            "content": "The Central Bank's latest meeting minutes suggest a cautious approach toward further interest rate hikes. Policymakers are closely monitoring inflation data and labor market trends. Analysts expect a period of stabilization as global economic uncertainties persist.",
            "tags": ["monetary policy", "interest rates", "inflation"]
        },
        {
            "title": "Trade Balance Data Shows Surprising Resilience in Exports",
            "content": "Recent trade statistics reveal a stronger-than-expected performance in high-tech manufacturing exports. Despite geopolitical tensions, supply chain optimizations have allowed domestic firms to maintain market share in key international regions.",
            "tags": ["trade", "exports", "manufacturing"]
        },
        {
            "title": "Government Announces New Infrastructure Spending Package",
            "content": "A significant fiscal stimulus focused on green energy and digital infrastructure was unveiled today. The multi-billion dollar initiative aims to boost long-term productivity and accelerate the transition to a sustainable economy.",
            "tags": ["fiscal policy", "infrastructure", "green energy"]
        },
        {
            "title": "Energy Prices Face Volatility Amid Supply Chain Disruptions",
            "content": "Global energy markets are experiencing increased price swings due to maintenance at major extraction sites and logistical bottlenecks. Market participants are hedging against potential winter shortages.",
            "tags": ["energy", "commodities", "inflation"]
        },
        {
            "title": "Consumer Confidence Index Reaches Multi-Month High",
            "content": "Surveys indicate that household sentiment is improving as wage growth outpaces inflation. Retailers are preparing for a robust holiday season, though some remain cautious about debt levels.",
            "tags": ["consumer", "sentiment", "retail"]
        }
    ]
    
    total_articles = 0
    while current_week_start <= end:
        for i in range(articles_per_week):
            # Pick a random day in the week that is within the range
            offset = random.randint(0, 6)
            article_date = current_week_start + timedelta(days=offset)
            
            if article_date < start or article_date > end:
                continue
                
            template = random.choice(news_templates)
            title = template["title"]
            content = template["content"]
            tags = ", ".join(template["tags"])
            
            # Add some "time-specific" flavor to content
            flavor = f" On {article_date.strftime('%B %d, %Y')}, market analysts noted that "
            full_content = flavor + content.lower()
            
            file_name = f"macro_news_{article_date.strftime('%Y%m%d')}_{i}.md"
            with open(os.path.join(output_dir, file_name), "w", encoding="utf-8") as f:
                f.write(f"# {title}\n\n")
                f.write(f"**Date:** {article_date.strftime('%Y-%m-%d')}\n")
                f.write(f"**Category:** Macroeconomics\n")
                f.write(f"**Keywords:** {tags}\n\n")
                f.write(f"## Content\n\n{full_content}\n")
            
            total_articles += 1
            
        current_week_start += timedelta(days=7)
        
    print(f"Generated {total_articles} macro news articles in {output_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch or generate macro news articles.")
    parser.add_argument("--start", type=str, required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--count", type=int, default=3, help="Articles per week")
    args = parser.parse_args()
    
    generate_macro_news(args.start, args.end, args.count)
