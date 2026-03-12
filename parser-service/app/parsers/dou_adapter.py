import asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import List, Dict, Any, Optional
import httpx
from app.models import NormalizedEvent
from datetime import datetime
import re

BASE_URL = "https://dou.ua/calendar/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8,ru;q=0.7'
}

MONTHS_UKR = {
    'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4, 'травня': 5, 'червня': 6,
    'липня': 7, 'серпня': 8, 'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
}

def parse_dou_date(date_str: str, time_str: str = "") -> Optional[str]:
    """
    Parses DOU date strings like "12 березня (четвер)" or "13 — 14 березня"
    and time strings like "18:00" into ISO 8601 format.
    Assumes current year if not specified (DOU usually doesn't show year for current year events).
    """
    if not date_str:
        return None
        
    try:
        # Extract the first day and month
        # Example: "12 березня (четвер)" -> day=12, month="березня"
        # Example: "13 — 14 березня" -> day=13, month="березня"
        
        # Remove day of week in parentheses
        clean_date = re.sub(r'\(.*?\)', '', date_str).strip()
        
        # Handle ranges by taking the first date
        if '—' in clean_date or '-' in clean_date:
            parts = re.split(r'[—\-]', clean_date)
            first_part = parts[0].strip()
            # If first part is just a number (e.g., "13 - 14 березня"), we need to append the month from the second part
            if first_part.isdigit():
                month_match = re.search(r'[а-яіїє]+', parts[1].strip(), re.IGNORECASE)
                if month_match:
                    clean_date = f"{first_part} {month_match.group(0)}"
            else:
                clean_date = first_part
                
        # Extract day and month
        match = re.search(r'(\d+)\s+([а-яіїє]+)', clean_date, re.IGNORECASE)
        if not match:
            return None
            
        day = int(match.group(1))
        month_str = match.group(2).lower()
        
        month = MONTHS_UKR.get(month_str)
        if not month:
            return None
            
        # Default to current year
        year = datetime.now().year
        
        # Parse time if provided
        hour = 0
        minute = 0
        if time_str:
            time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if time_match:
                hour = int(time_match.group(1))
                minute = int(time_match.group(2))
                
        dt = datetime(year, month, day, hour, minute)
        
        # If the parsed date is more than 3 months in the past, it's likely for next year
        if (datetime.now() - dt).days > 90:
            dt = dt.replace(year=year + 1)
            
        # Return ISO format with UTC timezone indicator
        return dt.isoformat() + "Z"
    except Exception as e:
        print(f"Error parsing date '{date_str}' and time '{time_str}': {e}")
        return None

class DouParser:
    def __init__(self, city_index=None):
        self.city_index = city_index

    async def fetch_text(self, client: httpx.AsyncClient, url: str) -> str:
        r = await client.get(url, headers=HEADERS, follow_redirects=True)
        r.raise_for_status()
        return r.text

    def parse_main_page(self, html: str) -> tuple[List[Dict[str, Any]], Optional[str]]:
        soup = BeautifulSoup(html, 'html.parser')
        events = []
        
        articles = soup.find_all('article', class_='b-postcard')
        for article in articles:
            title_tag = article.find('h2', class_='title').find('a')
            if not title_tag:
                continue
                
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
            
        paging = soup.find('div', class_='b-paging')
        next_url = None
        if paging:
            current_page_span = paging.find('span', class_='sel')
            if current_page_span:
                next_page_span = current_page_span.find_next_sibling('span', class_='page')
                if next_page_span and next_page_span.find('a'):
                    next_url = urljoin(BASE_URL, next_page_span.find('a')['href'])
                    
        return events, next_url

    def parse_details_page(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        
        title_tag = soup.find('div', class_='page-head')
        title = title_tag.find('h1').text.strip() if title_tag and title_tag.find('h1') else ""
        
        event_info = soup.find('div', class_='event-info')
        
        image_url = None
        if event_info:
            img_tag = event_info.find('img', class_='event-info-logo')
            if img_tag:
                image_url = img_tag['src']
                
        details = {
            'title': title,
            'image_url': image_url,
            'date': '',
            'time': '',
            'location': '',
            'price': ''
        }
        
        if event_info:
            rows = event_info.find_all('div', class_='event-info-row')
            for row in rows:
                dt = row.find('div', class_='dt')
                dd = row.find('div', class_='dd')
                if dt and dd:
                    dt_text = dt.text.strip().lower()
                    dd_text = dd.text.strip()
                    
                    if 'відбудеться' in dt_text or 'відбулось' in dt_text:
                        details['date'] = dd_text
                    elif 'час' in dt_text or 'початок' in dt_text:
                        details['time'] = dd_text
                    elif 'місце' in dt_text:
                        details['location'] = dd_text
                    elif 'вартість' in dt_text:
                        details['price'] = dd_text
                        
        article = soup.find('article', class_='b-typo')
        content_html = str(article) if article else ""
        content_text = article.text.strip() if article else ""
        
        details['content_html'] = content_html
        details['content_text'] = content_text
        
        tags_div = soup.find('div', class_='b-post-tags')
        tags = [a.text for a in tags_div.find_all('a')] if tags_div else []
        details['tags'] = tags
        
        return details

    async def scrape_all_events(self, max_pages: Optional[int] = None, concurrency: int = 5) -> List[NormalizedEvent]:
        async with httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=concurrency)) as client:
            current_url = BASE_URL
            pages_parsed = 0
            all_raw_events = []
            
            # 1. Fetch all listing pages sequentially (since we need the next URL)
            while current_url:
                if max_pages and pages_parsed >= max_pages:
                    break
                    
                print(f"Fetching DOU page: {current_url}")
                html = await self.fetch_text(client, current_url)
                events, next_url = self.parse_main_page(html)
                all_raw_events.extend(events)
                
                current_url = next_url
                pages_parsed += 1

            # 2. Fetch details concurrently
            sem = asyncio.Semaphore(concurrency)
            normalized_events = []
            
            async def fetch_and_parse_detail(raw_event: Dict[str, Any]):
                async with sem:
                    try:
                        html = await self.fetch_text(client, raw_event['link'])
                        details = self.parse_details_page(html)
                        
                        # Merge and normalize
                        name = details.get('title') or raw_event.get('title')
                        image = details.get('image_url') or raw_event.get('image_url')
                        location = details.get('location') or raw_event.get('location')
                        
                        # Parse city from location using CityIndex if available
                        city = None
                        if location:
                            loc_lower = location.lower()
                            if 'online' in loc_lower or 'онлайн' in loc_lower:
                                city = 'online'
                            elif self.city_index:
                                # Try to find a matching Karabas city in the location string
                                # Sort cities by length descending to match longer names first (e.g. "Івано-Франківськ" before "Іванів")
                                sorted_cities = sorted(self.city_index._karabas_by_key.items(), key=lambda x: len(x[0]), reverse=True)
                                for city_key, karabas_city in sorted_cities:
                                    # Use regex to match whole words to avoid partial matches
                                    if re.search(r'\b' + re.escape(city_key) + r'\b', loc_lower):
                                        city = karabas_city.name
                                        break
                        
                        price = details.get('price') or raw_event.get('price')
                        desc = details.get('content_text') or raw_event.get('description')
                        
                        # Simple date string mapping
                        date_str = details.get('date') or raw_event.get('date')
                        time_str = details.get('time') or ""
                        iso_date = parse_dou_date(date_str, time_str)
                        
                        normalized_events.append(NormalizedEvent(
                            name=name,
                            url=raw_event['link'],
                            startDate=iso_date,
                            location_name=location,
                            city=city,
                            price_low=price,
                            image=image,
                            description=desc,
                            source="dou.ua"
                        ))
                    except Exception as e:
                        print(f"Error fetching detail for {raw_event['link']}: {e}")
                        # Add basic info if detail fetch fails
                        date_str = raw_event.get('date')
                        iso_date = parse_dou_date(date_str) if date_str else None
                        
                        location = raw_event.get('location')
                        city = None
                        if location:
                            loc_lower = location.lower()
                            if 'online' in loc_lower or 'онлайн' in loc_lower:
                                city = 'online'
                            elif self.city_index:
                                sorted_cities = sorted(self.city_index._karabas_by_key.items(), key=lambda x: len(x[0]), reverse=True)
                                for city_key, karabas_city in sorted_cities:
                                    if re.search(r'\b' + re.escape(city_key) + r'\b', loc_lower):
                                        city = karabas_city.name
                                        break
                        
                        normalized_events.append(NormalizedEvent(
                            name=raw_event.get('title'),
                            url=raw_event['link'],
                            startDate=iso_date,
                            location_name=location,
                            city=city,
                            price_low=raw_event.get('price'),
                            image=raw_event.get('image_url'),
                            description=raw_event.get('description'),
                            source="dou.ua"
                        ))

            tasks = [asyncio.create_task(fetch_and_parse_detail(ev)) for ev in all_raw_events]
            await asyncio.gather(*tasks)
            
            return normalized_events
