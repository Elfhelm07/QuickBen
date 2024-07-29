import logging
import requests
from bs4 import BeautifulSoup
from transformers import pipeline
from concurrent.futures import ThreadPoolExecutor
import random

# Configure logging
logging.basicConfig(filename='error_log.txt', level=logging.ERROR,
                    format='%(asctime)s:%(levelname)s:%(message)s')

# Lists of sites based on scraping method
direct_access_sites = {
    "Wikipedia": {
        "url": "https://en.wikipedia.org/w/index.php?search=",
        "query_format": lambda query: query.replace(" ", "+")
    },
}

# Sites that require traversal to top n articles
traversal_sites = {
    "Medium": {
        "url": "https://medium.com/search?q=",
        "query_format": lambda query: query
    },
    "Dev.to": {
        "url": "https://dev.to/search?q=",
        "query_format": lambda query: query
    },
    "GeeksforGeeks": {
        "url": "https://www.geeksforgeeks.org/search/?q=",
        "query_format": lambda query: query
    },
    "Tutorialspoint": {
        "url": "https://www.tutorialspoint.com/search/index.htm?q=",
        "query_format": lambda query: query
    },
    "Stack Overflow": {
        "url": "https://stackoverflow.com/search?q=",
        "query_format": lambda query: query
    },
    "W3Schools": {
        "url": "https://www.w3schools.com/#gsc.tab=0&gsc.q=",
        "query_format": lambda query: query.replace(" ", "+")
    },
}

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0",
]

def get_random_user_agent():
    return random.choice(user_agents)

def split_text(text, chunk_size):
    """Splits the text into chunks of specified size."""
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i + chunk_size])

def fetch_url(url):
    headers = {"User-Agent": get_random_user_agent()}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None

def summarize_text(text, summarizer, chunk_size=300):
    summaries = []
    for chunk in split_text(text, chunk_size):
        if len(chunk.split()) < 30:
            continue
        max_length = min(130, len(chunk) // 2) if len(chunk) > 30 else 30
        chunk_summary = summarizer(chunk, max_length=max_length, min_length=30, do_sample=False)
        summaries.append(chunk_summary[0]['summary_text'])
    return " ".join(summaries)

def process_wikipedia(query, summarizer, n=5):
    wiki_info = direct_access_sites["Wikipedia"]
    search_url = f"{wiki_info['url']}{wiki_info['query_format'](query)}"
    logging.info(f"Searching Wikipedia URL: {search_url}")

    page_content = fetch_url(search_url)
    if not page_content:
        return []

    soup = BeautifulSoup(page_content, 'html.parser')
    article_links = [f"https://en.wikipedia.org{link['href']}" for link in soup.find_all('a', href=True) if link['href'].startswith('/wiki/') and ':' not in link['href']]
    article_links = article_links[:n]

    output = []
    for article_url in article_links:
        article_content = fetch_url(article_url)
        if not article_content:
            continue

        article_soup = BeautifulSoup(article_content, 'html.parser')
        paragraphs = article_soup.find_all('p')
        full_text = " ".join([para.get_text(strip=True) for para in paragraphs])

        if full_text:
            final_summary = summarize_text(full_text, summarizer)
            output.append({'site': "Wikipedia", 'url': article_url, 'summary': final_summary})

    return output

def process_traversal_site(site, info, query, summarizer, n=5):
    search_url = f"{info['url']}{info['query_format'](query)}"
    logging.info(f"Searching URL: {search_url}")

    page_content = fetch_url(search_url)
    if not page_content:
        return []

    soup = BeautifulSoup(page_content, 'html.parser')
    article_links = []

    for link in soup.find_all('a', href=True):
        href = link['href']
        if site == "Medium" and href.startswith('https://medium.com/'):
            article_links.append(href)
        elif site == "Dev.to" and href.startswith('https://dev.to/'):
            article_links.append(href)
        elif site == "GeeksforGeeks" and (href.startswith('/articles/') or href.startswith('/geeks/')):
            article_links.append(f"https://www.geeksforgeeks.org{href}")
        elif site == "Tutorialspoint" and (href.startswith('/tutorials/') or href.startswith('https://www.tutorialspoint.com/')):
            article_links.append(f"https://www.tutorialspoint.com{href}")
        elif site == "Stack Overflow" and (href.startswith('/questions/') or href.startswith('https://stackoverflow.com/questions/')):
            article_links.append(f"https://stackoverflow.com{href}")

    article_links = article_links[:n]

    output = []
    for article_url in article_links:
        article_content = fetch_url(article_url)
        if not article_content:
            continue

        article_soup = BeautifulSoup(article_content, 'html.parser')
        paragraphs = article_soup.find_all('p')
        full_text = " ".join([para.get_text(strip=True) for para in paragraphs])

        if full_text:
            final_summary = summarize_text(full_text, summarizer)
            output.append({'site': site, 'url': article_url, 'summary': final_summary})

    return output

def scrape_resources(query, n=5):
    model_name = "facebook/bart-large-cnn"
    summarizer = pipeline("summarization", model=model_name)
    output = []

    output.extend(process_wikipedia(query, summarizer, n))

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(process_traversal_site, site, info, query, summarizer, n)
            for site, info in traversal_sites.items()
        ]
        for future in futures:
            result = future.result()
            if result:
                output.extend(result)

    return output

# Example usage
if __name__ == "__main__":
    query = "Dynamic programming"
    resources = scrape_resources(query)

    with open('summarized_resources.txt', 'w', encoding='utf-8') as f:
        for resource in resources:
            f.write(f"Site: {resource['site']}\n")
            f.write(f"URL: {resource['url']}\n")
            f.write(f"Summary: {resource['summary']}\n")
            f.write("\n")
