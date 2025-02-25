import random
import time
import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
from flask import Flask, request, jsonify

# List of User-Agent strings for rotation (Expanded)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:98.0) Gecko/20100101 Firefox/98.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36",
]

def get_random_headers():
    """Generate randomized headers to evade bot detection."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.bing.com/",
        "DNT": "1",  # Do Not Track request
        "Upgrade-Insecure-Requests": "1",
    }

def detect_bot_block(response):
    """Detect if Bing is blocking the bot or showing CAPTCHA."""
    if response is None or response.status_code != 200:
        return True

    text = response.text.lower()
    blocked_patterns = [
        "our systems have detected unusual traffic",
        "form id=\"b_captcha\"",
        "click to verify",
        "verify you are human",
        "complete the captcha",
        "check the box to proceed",
    ]

    if any(pattern in text for pattern in blocked_patterns):
        return True

    return False

def safe_request(url, max_retries=5):
    """Handle retries with exponential backoff and session persistence."""
    session = requests.Session()  # Maintain cookies across requests
    for attempt in range(max_retries):
        try:
            headers = get_random_headers()
            response = session.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            if detect_bot_block(response):
                wait_time = random.uniform(3, 6) * (2 ** attempt)  # Exponential backoff
                time.sleep(wait_time)
                continue  # Retry with a new User-Agent

            return response  # Successful response

        except requests.exceptions.RequestException:
            time.sleep(random.uniform(3, 6) * (2 ** attempt))

    return None

def extract_search_results(response):
    """Extract a two-line response from Bing dynamically."""
    if response is None:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    # Focus on the first <li> element with the class "b_algo" for the first result
    result = soup.find("li", class_=re.compile(r"\b(b_algo)\b"))
    if result:
        title_tag = result.find("h2")
        snippet_tag = result.find("p")
        if title_tag:
            title = title_tag.get_text(strip=True)
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            return f"{title}\n{snippet}"

    return None

def bing_search(query):
    """Perform a Bing search and return the best answer."""
    # Properly encode the query to handle spaces and special characters
    encoded_query = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded_query}"
    response = safe_request(url)

    if response is None or detect_bot_block(response):
        return "Bot detection triggered or no response. Try again later."

    result = extract_search_results(response)
    if not result:
        return "No relevant search results found."

    return result

# Flask application setup
app = Flask(__name__)

@app.route("/bing_search", methods=["POST"])
def search():
    data = request.json
    if not data or "query" not in data:
        return jsonify({"error": "Missing 'query' in request body."}), 400

    query = data["query"]
    result = bing_search(query)

    if isinstance(result, str) and result.startswith("Bot detection"):
        return jsonify({"error": result}), 500

    return jsonify({"query": query, "response": result})

if __name__ == "__main__":
    app.run(debug=True)
