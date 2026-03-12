import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8,ru;q=0.7'
}

def parse_details_page(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
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
    # Get HTML content of the article
    content_html = str(article) if article else ""
    # Get plain text
    content_text = article.text.strip() if article else ""
    
    details['content_html'] = content_html
    details['content_text'] = content_text
    
    tags_div = soup.find('div', class_='b-post-tags')
    tags = [a.text for a in tags_div.find_all('a')] if tags_div else []
    details['tags'] = tags
    
    return details

if __name__ == "__main__":
    test_url = "https://dou.ua/calendar/56692/"
    details = parse_details_page(test_url)
    print("Parsed details:")
    for k, v in details.items():
        if k == 'content_html':
            print(f"{k}: <html content length: {len(v)}>")
        elif k == 'content_text':
            print(f"{k}: {v[:100]}...")
        else:
            print(f"{k}: {v}")
