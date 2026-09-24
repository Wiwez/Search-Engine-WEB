import hashlib
import json
import os
import requests

from collections import deque
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from parser import get_robots_rules
from shingles import find_near_duplicates


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

    # Get the base URL/domain
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Try reading the existing JSON file
    try:
        with open(filename, "r") as file:
            saved_rules = json.load(file)

    except (json.JSONDecodeError, OSError):
        saved_rules = {}

    # If we already have rules for this domain, return them
    if base_url in saved_rules:
        return saved_rules[base_url]

    # Otherwise get robots.txt and save it
    get_robots_rules(url, "Junglejimcrawler")

    # Read the JSON again after get_robots_rules()
    try:
        with open(filename, "r") as file:
            saved_rules = json.load(file)

    except (json.JSONDecodeError, OSError):
        return None

    if base_url in saved_rules:
        return saved_rules[base_url]

    return None


def crawl(seed_url, max_pages=1000, near_duplicate_threshold=0.85):

    frontier = deque([seed_url])
    visited = set()
    downloaded_pages = []

    headers = {
        "User-Agent": "Junglejimcrawler"
    }

    # Only crawl the same domain as the seed
    seed_domain = urlparse(seed_url).netloc

    # Create pages folder
    os.makedirs("pages", exist_ok=True)

    while frontier and len(visited) < max_pages:

        # Get next URL from frontier
        url = frontier.popleft()

        # Skip if already visited
        if url in visited:
            continue

        visited.add(url)

        # --------------------------------
        # Check robots.txt
        # --------------------------------

        rules = readJSONrules(url)

        if rules is None:
            print("NO ROBOTS RULES:", url)
            continue

        if not is_allowed(url, rules):
            print("BLOCKED:", url)
            continue

        # --------------------------------
        # Crawl page
        # --------------------------------

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

        # Only work with HTML pages
        content_type = response.headers.get("Content-Type", "")

        if "text/html" not in content_type:
            print("NOT HTML:", url)
            continue

        html = response.text

        # --------------------------------
        # Save HTML
        # --------------------------------

        url_hash = hashlib.sha256(url.encode()).hexdigest()

        filename = f"pages/{url_hash}.html"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"<!-- URL: {url} -->\n")
            f.write(html)

        downloaded_pages.append((url, filename))

        print("DOWNLOADED:", url)

        # --------------------------------
        # Find links
        # --------------------------------

        soup = BeautifulSoup(html, "html.parser")

        for link in soup.find_all("a"):

            href = link.get("href")

            if href is None:
                continue

            # Convert relative URL to absolute URL
            new_url = urljoin(url, href)

            # --------------------------------
            # Only HTTP/HTTPS
            # --------------------------------

            parsed_new_url = urlparse(new_url)

            if parsed_new_url.scheme not in ["http", "https"]:
                continue

            # --------------------------------
            # Stay on seed domain
            # --------------------------------

            # if parsed_new_url.netloc != seed_domain:
            #     continue

            # --------------------------------
            # Add new URL to frontier
            # --------------------------------

            if new_url not in visited:
                frontier.append(new_url)

                print("FOUND:", new_url)

    # Compare downloaded pages after the crawl has finished.
    def saved_pages():
        for page_url, page_filename in downloaded_pages:
            with open(page_filename, "r", encoding="utf-8") as page_file:
                yield page_url, page_file.read()

    duplicates = find_near_duplicates(
        saved_pages(), threshold=near_duplicate_threshold
    )
    with open("near_duplicates.json", "w", encoding="utf-8") as report:
        json.dump(duplicates, report, indent=2)

    print(f"NEAR DUPLICATES: {len(duplicates)} (near_duplicates.json)")
