import random
import time
import requests
from bs4 import BeautifulSoup
import re

# List of User-Agent strings for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:55.0) Gecko/20100101 Firefox/55.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0',
]

# Function to improve search accuracy, now including an address filter
def enhance_query(query):
    lower_q = query.lower()
    if "address" in lower_q:
        # For address-related queries, append sites that commonly list addresses
        return query + " site:justdial.com OR site:yellowpages.com OR site:zoominfo.com"
    if "owner" in lower_q or "ceo" in lower_q:
        return query + " site:linkedin.com OR site:crunchbase.com"
    if "highest t20 run" in lower_q:
        return "Highest individual T20 score site:espncricinfo.com"
    if "prime minister" in lower_q:
        return query + " site:wikipedia.org OR site:pmindia.gov.in"
    return query

# Detect if Bing is blocking our bot
def detect_blocked_request(response):
    if "form id=\"b_captcha\"" in response.text:
        print("Bing detected bot activity (CAPTCHA required).")
        return True
    if "our systems have detected unusual traffic" in response.text:
        print("Bing detected unusual traffic from your network.")
        return True
    return False

# Modified safe_request function with retries and longer delay on DNS errors
def safe_request(url, headers, max_retries=5):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            if detect_blocked_request(response):
                time.sleep(2)  # Wait before retrying
                continue

            return response

        except requests.exceptions.RequestException as e:
            print(f"Network error (attempt {attempt+1}): {e}")
            # If DNS resolution fails, wait a bit longer
            if "getaddrinfo failed" in str(e):
                time.sleep(5)
            else:
                time.sleep(3)
    return None  # Return None if all retries fail

# Main Bing Search Function
def bing_search(query):
    query = enhance_query(query)  # Improve query
    url = f"https://www.bing.com/search?q={query}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = safe_request(url, headers)
    if response is None:
        return "Error: Unable to connect to Bing. Check your internet or firewall settings."

    soup = BeautifulSoup(response.text, "html.parser")

    # Modified snippet extraction: gather all valid snippets and select the longest one.
    valid_snippets = []
    for result in soup.find_all("li", class_="b_algo"):
        title = result.find("h2")
        snippet = result.find("p")
        if title and snippet:
            title_text = title.text.strip()
            snippet_text = snippet.text.strip()
            if "List of" not in title_text and len(snippet_text) > 15:
                valid_snippets.append(snippet_text)
    
    if valid_snippets:
        best_snippet = max(valid_snippets, key=len)
        return best_snippet

    return "No precise answer found, please refine your question."

# Interactive chatbot interface
if __name__ == "__main__":
    while True:
        question = input("Enter your question: ")
        if question.lower() in ["exit", "quit"]:
            break
        answer = bing_search(question)
        print(f"\nAnswer: {answer}\n")
