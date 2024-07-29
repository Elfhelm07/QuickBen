import logging
import requests
from bs4 import BeautifulSoup
from transformers import pipeline

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

def split_text(text, chunk_size):
    """Splits the text into chunks of specified size."""
    words = text.split()
    for i in range(0, len(words), chunk_size):
        yield ' '.join(words[i:i + chunk_size])

def scrape_resources(query, n=5):  # Add n parameter for number of articles
    model_name = "facebook/bart-large-cnn"
    summarizer = pipeline("summarization", model=model_name)
    output = []

    # Process Wikipedia separately
    if "Wikipedia" in direct_access_sites:
        wiki_info = direct_access_sites["Wikipedia"]
        search_url = f"{wiki_info['url']}{wiki_info['query_format'](query)}"
        logging.info(f"Searching Wikipedia URL: {search_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            return output

        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract article links from Wikipedia search results
        article_links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/wiki/') and ':' not in href:
                article_links.append(f"https://en.wikipedia.org{href}")

        # Limit to the first n article links
        article_links = article_links[:n]

        # Scrape each Wikipedia article
        for article_url in article_links:
            try:
                article_response = requests.get(article_url, headers=headers)
                article_response.raise_for_status()
                article_soup = BeautifulSoup(article_response.text, 'html.parser')

                # Extract relevant content from the article
                paragraphs = article_soup.find_all('p')
                full_text = " ".join([para.get_text(strip=True) for para in paragraphs])

                # Summarization logic here...
                if full_text:
                    chunk_size = 300
                    summaries = []
                    for chunk in split_text(full_text, chunk_size):
                        if len(chunk.split()) < 30:
                            continue
                        max_length = min(130, len(chunk) // 2) if len(chunk) > 30 else 30
                        # Adjusting max_length and min_length
                        chunk_summary = summarizer(chunk, max_length=max_length, min_length=10, do_sample=False)
                        summaries.append(chunk_summary[0]['summary_text'])
                    final_summary = " ".join(summaries)

                    # Compile final output
                    output.append({'site': "Wikipedia", 'url': article_url, 'summary': final_summary})

            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to retrieve article: {e}")

    # Process other direct access sites
    for site, info in traversal_sites.items():  # Change to traversal_sites
        search_url = f"{info['url']}{info['query_format'](query)}"
        logging.info(f"Searching URL: {search_url}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        try:
            response = requests.get(search_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            continue

        soup = BeautifulSoup(response.text, 'html.parser')

        # Step 2: Extract article links based on site structure
        article_links = []

        # Generic extraction logic for traversal sites
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Ensure that the correct links are being captured for each site
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

        # Limit to the first n article links
        article_links = article_links[:n]

        # Step 3: Scrape each article
        for article_url in article_links:
            try:
                article_response = requests.get(article_url, headers=headers)
                article_response.raise_for_status()
                article_soup = BeautifulSoup(article_response.text, 'html.parser')

                # Extract relevant content from the article
                paragraphs = article_soup.find_all('p')
                full_text = " ".join([para.get_text(strip=True) for para in paragraphs])

                # Summarization logic here...
                if full_text:
                    chunk_size = 300
                    summaries = []
                    for chunk in split_text(full_text, chunk_size):
                        if len(chunk.split()) < 30:
                            continue
                        max_length = min(130, len(chunk) // 2) if len(chunk) > 30 else 30
                        # Adjusting max_length and min_length
                        chunk_summary = summarizer(chunk, max_length=max_length, min_length=10, do_sample=False)
                        summaries.append(chunk_summary[0]['summary_text'])
                    final_summary = " ".join(summaries)

                    # Compile final output
                    output.append({'site': site, 'url': article_url, 'summary': final_summary})

            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to retrieve article: {e}")

    return output

# Example usage
if __name__ == "__main__":
    query = "Dynamic programming"
    resources = scrape_resources(query)
    
    # Write the summarized data and links to a text file with utf-8 encoding
    with open('summarized_resources.txt', 'w', encoding='utf-8') as f:
        for resource in resources:
            f.write(f"Site: {resource['site']}\n")
            f.write(f"URL: {resource['url']}\n")
            f.write(f"Summary: {resource['summary']}\n")
            f.write("\n")  # Add a newline for better readability