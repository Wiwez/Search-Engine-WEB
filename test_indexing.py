from pathlib import Path
import tempfile
import unittest

from indexing import InvertedIndex, tokenize


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.index = InvertedIndex.from_directory(Path(__file__).parent / "examples/pages")

    def test_normalization(self):
        self.assertEqual(tokenize("KØBENHAVN Æble A\u030arhus ＣＡＴ 2026 cat-dog"),
                         ["københavn", "æble", "århus", "cat", "2026", "cat", "dog"])
        self.assertEqual(self.index.search("KØBENHAVN"), ["d1.html", "d2.html"])

    def test_boolean_truth_table(self):
        cases = {
            "cat": ["d1.html", "d3.html"],
            "cat AND dog": ["d1.html"],
            "cat OR dog": ["d1.html", "d2.html", "d3.html"],
            "cat AND NOT dog": ["d3.html"],
            "NOT cat": ["d2.html"],
            "cat OR dog AND bird": ["d1.html", "d2.html", "d3.html"],
            "(cat OR dog) AND bird": ["d2.html"],
            "NOT (cat OR dog)": [],
            "NOT NOT cat": ["d1.html", "d3.html"],
            "unknown": [],
            "NOT unknown": ["d1.html", "d2.html", "d3.html"],
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                self.assertEqual(self.index.search(query), expected)

    def test_invalid_queries(self):
        for query in ["", "cat dog", "cat and dog", "cat AND", "OR cat", "()",
                      "(cat", "cat)", "NOT", "cat OR OR dog", '"cat dog"', "cat-dog"]:
            with self.subTest(query=query), self.assertRaises(ValueError):
                self.index.search(query)

    def test_content_selection_and_document_membership(self):
        self.assertNotIn("menu", self.index.postings)
        self.assertNotIn("hidden", self.index.postings)
        self.assertNotIn("https", self.index.postings)
        self.index.add_document("extra", "<title>Unique</title><main>cat cat &amp; dog</main>")
        self.assertEqual(self.index.search("unique"), ["extra"])
        self.assertEqual(self.index.postings["cat"], {"d1.html", "d3.html", "extra"})
        self.index.add_document("empty", "")
        self.assertIn("empty", self.index.search("NOT cat"))
        with self.assertRaises(ValueError):
            self.index.add_document("extra", "replacement")

    def test_save_load(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json"
            self.index.save(path)
            loaded = InvertedIndex.load(path)
            self.assertEqual(loaded.documents, self.index.documents)
            self.assertEqual(loaded.postings, self.index.postings)
            self.assertEqual(loaded.search("cat AND NOT dog"), ["d3.html"])
        self.assertEqual(self.index.documents["d1.html"]["url"], "https://example.com/d1")

    def test_empty_and_missing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                InvertedIndex.from_directory(directory)
            with self.assertRaises(ValueError):
                InvertedIndex.from_directory(Path(directory) / "missing")


if __name__ == "__main__":
    unittest.main()
