import json
import os
import tempfile
import unittest
from unittest.mock import patch

from crawler import crawl
from shingles import find_near_duplicates, jaccard_similarity, visible_text


class NearDuplicateTests(unittest.TestCase):
    def test_visible_text_excludes_navigation_and_scripts(self):
        html = "<nav>Menu words here</nav><main>Article words here</main><script>hidden()</script>"
        self.assertEqual(visible_text(html), "Article words here")

    def test_near_duplicates_match_content_and_ignore_short_pages(self):
        article = "one two three four five six seven eight nine ten"
        pages = [
            ("https://example.com/first", f"<main>{article}</main>"),
            ("https://example.com/short", "<p>one two</p>"),
            ("https://example.com/copy", f"<nav>Different menu</nav><main>{article}</main>"),
            ("https://example.com/other", "<main>alpha beta gamma delta epsilon zeta eta theta</main>"),
        ]
        self.assertEqual(find_near_duplicates(pages), [{
            "url": "https://example.com/copy",
            "duplicate_of": "https://example.com/first",
            "similarity": 1.0,
        }])
        self.assertEqual(jaccard_similarity(article, article), 1.0)

    def test_crawl_writes_report_after_downloads(self):
        article = "one two three four five six seven eight nine ten"
        first = f'<main>{article}</main><a href="/copy">Copy</a>'
        second = f"<main>{article}</main>"

        class Response:
            status_code = 200
            headers = {"Content-Type": "text/html; charset=utf-8"}

            def __init__(self, text):
                self.text = text

        with tempfile.TemporaryDirectory() as directory:
            original_directory = os.getcwd()
            try:
                os.chdir(directory)
                with patch("crawler.readJSONrules", return_value={"disallow": []}), \
                     patch("crawler.requests.get", side_effect=[Response(first), Response(second)]):
                    crawl("https://example.com/", max_pages=2)

                with open("near_duplicates.json", encoding="utf-8") as report:
                    self.assertEqual(json.load(report), [{
                        "url": "https://example.com/copy",
                        "duplicate_of": "https://example.com/",
                        "similarity": 1.0,
                    }])
                self.assertEqual(len(os.listdir("pages")), 2)
            finally:
                os.chdir(original_directory)


if __name__ == "__main__":
    unittest.main()
