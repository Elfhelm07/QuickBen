import requests
from bs4 import BeautifulSoup

def scrape_medium(url):
    print(f"Fetching URL: {url}")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    response = requests.get(url, headers=headers)
    
    print(f"Response status code: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Construct a more precise CSS selector
        selector = (
            "body > div.a.b.c > div.l.c > div.ca.cb.l > div.ab.cc.cd > "
            "main.ce.cf.ch.ci.l.ck > div.cl.ab.cm > div.ab.cn > "
            "div.co.bg.cq.cr.cs > div.l > article > div.nd.l > div.bg.cl > "
            "div.l > div.bg.l > div[role='link']"
        )
        
        links = soup.select(selector)
        
        print(f"Number of link elements found: {len(links)}")
        
        for link in links:
            href = link.get('data-href')
            if href:
                print(href)
            else:
                print("No data-href attribute found for this element")
        
        if not links:
            print("\nNo links found. Printing the first 1000 characters of HTML for debugging:")
            print(soup.prettify()[:1000])
    else:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")

url = "https://medium.com/search?q=dynamic+programming"
scrape_medium(url)