import requests


def parse_robots_txt(text, crawler_name="MyCrawler"):
    rules = {}
    current_agent = None

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
            current_agent = value

            if current_agent not in rules:
                rules[current_agent] = {
                    "allow": [],
                    "disallow": [],
                    "crawl_delay": None
                }

        elif current_agent is not None:

            if key == "allow":
                rules[current_agent]["allow"].append(value)

            elif key == "disallow":
                rules[current_agent]["disallow"].append(value)

            elif key == "crawl-delay":
                try:
                    rules[current_agent]["crawl_delay"] = float(value)
                except ValueError:
                    pass

    # Return rules that apply to our crawler
    if crawler_name in rules:
        return rules[crawler_name]

    if "*" in rules:
        return rules["*"]

    return {
        "allow": [],
        "disallow": [],
        "crawl_delay": None
    }


# ---------------------------------
# Get robots.txt from a URL
# ---------------------------------

robots_url = "https://www.linkedin.com/robots.txt"

response = requests.get(robots_url, timeout=1000)

robots_text = response.text

restrictions = parse_robots_txt(robots_text)

print(restrictions)