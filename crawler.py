from collections import deque
import json
import requests
from collections import deque
from urllib.parse import urlparse

from parser import get_robots_rules


def is_allowed(url, rules):
    if rules is None:
        return False

    path = urlparse(url).path

    for disallowed_path in rules["disallow"]:

        if path.startswith(disallowed_path):
            return False

    return True

def readJSONrules(url):
    filename = "robots_rules.json"
    try:
        with open(filename, "r") as file:
            saved_rules = json.load(file)
    except (json.JSONDecodeError, OSError):
        saved_rules = {}
    
    if url in saved_rules:
        return saved_rules[url]
    else:
        get_robots_rules(url, "Junglejimcrawler")
        try:
            with open(filename, "r") as file:
                saved_rules = json.load(file)
        except (json.JSONDecodeError, OSError):
            saved_rules = {}
        if url in saved_rules:
            return saved_rules[url]
        return None

def crawl(seed_url, max_pages=1000):

    frontier = deque([seed_url])
    visited = set()

    headers = {
        "User-Agent": "Junglejimcrawler"
    }

    while frontier and len(visited) < max_pages:

        url = frontier.popleft()

        if url in visited:
            continue

        visited.add(url)

        rules = readJSONrules(url)
        if rules is None:
            print("No rules found for:", url)
            continue

        if not is_allowed(url, rules):
            print("BLOCKED:", url)
            continue

        # Print the URL we're about to crawl
        print("CRAWLING:", url)

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=10
            )

        except requests.RequestException as error:
            print("FAILED:", url, error)
            continue

        if response.status_code != 200:
            print("SKIPPED:", url, response.status_code)
            continue

        html = response.text

        print("DOWNLOADED:", url)