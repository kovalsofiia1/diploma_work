import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

BASE_URL = "https://dou.ua/calendar/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8,ru;q=0.7'
}

def parse_main_page(url=BASE_URL, max_pages=None):
    events = []
    current_url = url
    pages_parsed = 0
    
    while current_url:
        if max_pages and pages_parsed >= max_pages:
            break
            
        print(f"Parsing {current_url}...")
        response = requests.get(current_url, headers=HEADERS)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = soup.find_all('article', class_='b-postcard')
        for article in articles:
            title_tag = article.find('h2', class_='title').find('a')
            if not title_tag:
                continue
                
            # Remove img from title text
            img_in_title = title_tag.find('img')
            if img_in_title:
                img_in_title.extract()
                
            title = title_tag.text.strip()
            link = title_tag['href']
            
            img_tag = article.find('img', class_='logo')
            image_url = img_tag['src'] if img_tag else None
            
            when_where = article.find('div', class_='when-and-where')
            date = ""
            location = ""
            price = ""
            
            if when_where:
                date_span = when_where.find('span', class_='date')
                date = date_span.text.strip() if date_span else ""
                if date_span:
                    date_span.extract()
                
                # Extracting location and price
                when_where_text = when_where.get_text(separator='|').split('|')
                when_where_parts = [p.strip() for p in when_where_text if p.strip()]
                
                if len(when_where_parts) > 0:
                    location = when_where_parts[0]
                if len(when_where_parts) > 1:
                    price = when_where_parts[1]
                
            desc_tag = article.find('p', class_='b-typo')
            description = desc_tag.text.strip() if desc_tag else ""
            
            more_div = article.find('div', class_='more')
            tags = [a.text for a in more_div.find_all('a')] if more_div else []
            
            events.append({
                'title': title,
                'link': link,
                'image_url': image_url,
                'date': date,
                'location': location,
                'price': price,
                'description': description,
                'tags': tags
            })
            
        # Pagination
        paging = soup.find('div', class_='b-paging')
        next_url = None
        if paging:
            current_page_span = paging.find('span', class_='sel')
            if current_page_span:
                next_page_span = current_page_span.find_next_sibling('span', class_='page')
                if next_page_span and next_page_span.find('a'):
                    next_url = urljoin(BASE_URL, next_page_span.find('a')['href'])
                    
        current_url = next_url
        pages_parsed += 1
        
    return events

if __name__ == "__main__":
    import json
    import importlib.util
    import sys
    import os
    
    # Load parcer-details.py
    spec = importlib.util.spec_from_file_location("parcer_details", os.path.join(os.path.dirname(__file__), "parcer-details.py"))
    parcer_details = importlib.util.module_from_spec(spec)
    sys.modules["parcer_details"] = parcer_details
    spec.loader.exec_module(parcer_details)
    
    print("Starting to parse all pages...")
    # Parse all pages
    events = parse_main_page(BASE_URL)
    print(f"Total events found: {len(events)}")
    
    print("Fetching details for all events...")
    for i, event in enumerate(events):
        try:
            print(f"[{i+1}/{len(events)}] Fetching details for: {event['title'].encode('utf-8', 'replace').decode('utf-8')}")
        except Exception:
            print(f"[{i+1}/{len(events)}] Fetching details...")
            
        try:
            details = parcer_details.parse_details_page(event['link'])
            event.update(details)
        except Exception as e:
            print(f"Error fetching details for {event['link']}: {e}")
        
    output_file = os.path.join(os.path.dirname(__file__), "events.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(events, f, ensure_ascii=False, indent=4)
        
    print(f"Successfully saved {len(events)} events to {output_file}")
