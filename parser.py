import requests
import json
import os
from urllib.parse import urlparse


def parse_robots_txt(text, crawler_name="MyCrawler"):
    rules = {}

    current_agents = []
    reading_rules = False

    for raw_line in text.splitlines():
        line = raw_line.strip()

        # Ignore empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Remove inline comments
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        if ":" not in line:
            continue

        key, value = line.split(":", 1)

        key = key.strip().lower()
        value = value.strip()

        if key == "user-agent":

            # A user-agent after rules means a new group
            if reading_rules:
                current_agents = []
                reading_rules = False

            agent = value.lower()
            current_agents.append(agent)

            if agent not in rules:
                rules[agent] = {
                    "allow": [],
                    "disallow": [],
                    "crawl_delay": None
                }

        elif current_agents:

            reading_rules = True

            if key == "allow":

                # Empty Allow does nothing
                if value:
                    for agent in current_agents:
                        rules[agent]["allow"].append(value)

            elif key == "disallow":

                # Empty Disallow means nothing is disallowed
                if value:
                    for agent in current_agents:
                        rules[agent]["disallow"].append(value)

            elif key == "crawl-delay":
                try:
                    delay = float(value)

                    for agent in current_agents:
                        rules[agent]["crawl_delay"] = delay

                except ValueError:
                    pass

    # User-agent matching should not depend on capitalization
    crawler_name = crawler_name.lower()

    # Prefer rules specifically for our crawler
    if crawler_name in rules:
        return rules[crawler_name]

    # Otherwise use wildcard rules
    if "*" in rules:
        return rules["*"]

    # No applicable rules
    return {
        "allow": [],
        "disallow": [],
        "crawl_delay": None
    }


def get_robots_rules(url, crawler_name="MyCrawler"):
    filename = "robots_rules.json"

   
    parsed_url = urlparse(url)

    if not parsed_url.scheme or not parsed_url.netloc:
        print("Invalid URL:", url)
        return None

    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = base_url + "/robots.txt"

    print("Getting robots.txt rules for:", base_url)

    # --------------------------------
    # Load JSON cache
    # --------------------------------

    if os.path.exists(filename):
        try:
            with open(filename, "r") as file:
                saved_rules = json.load(file)

        except (json.JSONDecodeError, OSError):
            saved_rules = {}

    else:
        saved_rules = {}


    if base_url in saved_rules:
        print("Using saved robots.txt rules for:", base_url)
        return saved_rules[base_url]

    print("Downloading:", robots_url)

    try:
        response = requests.get(
            robots_url,
            headers={
                "User-Agent": crawler_name
            },
            timeout=10
        )

    except requests.RequestException as error:
        print("Could not connect to:", robots_url)
        print(error)
        return None

    if response.status_code != 200:
        print(
            "Could not get robots.txt:",
            response.status_code
        )
        return None

    restrictions = parse_robots_txt(
        response.text,
        crawler_name
    )

    saved_rules[base_url] = restrictions

    with open(filename, "w") as file:
        json.dump(saved_rules, file, indent=4)

    return restrictions