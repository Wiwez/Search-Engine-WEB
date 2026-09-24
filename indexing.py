"""Build an inverted index of saved HTML and evaluate Boolean queries."""

import argparse
import json
from pathlib import Path
import re
import unicodedata

from bs4 import BeautifulSoup

from shingles import visible_text


def tokenize(text):
    """Case-fold Unicode words/numbers; punctuation separates terms."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)


class InvertedIndex:
    def __init__(self):
        self.documents = {}
        self.postings = {}

    def add_document(self, document_id, html, url="", path=""):
        if document_id in self.documents:
            raise ValueError(f"Duplicate document ID: {document_id}")
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        self.documents[document_id] = {"url": url, "path": path, "title": title}
        # Sets store each document once, regardless of term frequency.
        for term in set(tokenize(title + " " + visible_text(html))):
            self.postings.setdefault(term, set()).add(document_id)

    @classmethod
    def from_directory(cls, directory):
        directory = Path(directory)
        if not directory.is_dir():
            raise ValueError(f"Page directory does not exist: {directory}")
        files = sorted(directory.glob("*.html"))
        if not files:
            raise ValueError(f"No HTML pages found in {directory}; crawl or use examples/pages")
        index = cls()
        for path in files:
            html = path.read_text(encoding="utf-8")
            match = re.match(r"\s*<!-- URL:\s*(.*?)\s*-->", html)
            index.add_document(path.name, html, match.group(1) if match else "", str(path))
        return index

    def save(self, path):
        data = {
            "version": 1,
            "documents": self.documents,
            "postings": {term: sorted(ids) for term, ids in sorted(self.postings.items())},
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("Unsupported index version; rebuild the index")
        index = cls()
        index.documents = data["documents"]
        index.postings = {term: set(ids) for term, ids in data["postings"].items()}
        return index

    def search(self, query):
        """Return sorted IDs. Precedence: NOT > AND > OR; explicit operators."""
        tokens = re.findall(r"\(|\)|[^\s()]+", query)
        position = 0
        universe = set(self.documents)

        def take(token):
            nonlocal position
            if position < len(tokens) and tokens[position] == token:
                position += 1
                return True
            return False

        def primary():
            nonlocal position
            if take("NOT"):
                return universe - primary()
            if take("("):
                result = disjunction()
                if not take(")"):
                    raise ValueError("Missing closing parenthesis")
                return result
            if position == len(tokens) or tokens[position] in {"AND", "OR", ")"}:
                raise ValueError("Expected a search term, NOT, or opening parenthesis")
            raw = tokens[position]
            position += 1
            terms = tokenize(raw)
            if len(terms) != 1 or any(char in raw for char in '\"\''):
                raise ValueError(f"Expected one word or number: {raw!r}; use explicit AND/OR")
            return set(self.postings.get(terms[0], set()))

        def conjunction():
            result = primary()
            while take("AND"):
                result &= primary()
            return result

        def disjunction():
            result = conjunction()
            while take("OR"):
                result |= conjunction()
            return result

        if not tokens:
            raise ValueError("Query must not be empty")
        result = disjunction()
        if position != len(tokens):
            raise ValueError(f"Unexpected token {tokens[position]!r}; use uppercase AND, OR, NOT")
        return sorted(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build", help="Index an existing crawl without downloading pages")
    build.add_argument("--pages", default="pages")
    build.add_argument("--output", default="index.json")
    search = commands.add_parser("query", help="Search a saved index")
    search.add_argument("query", help='Example: "sport AND NOT fodbold"')
    search.add_argument("--index", default="index.json")
    args = parser.parse_args()
    try:
        if args.command == "build":
            index = InvertedIndex.from_directory(args.pages)
            index.save(args.output)
            print(f"Indexed {len(index.documents)} documents and {len(index.postings)} terms -> {args.output}")
        else:
            index = InvertedIndex.load(args.index)
            results = index.search(args.query)
            print(f"{len(results)} result(s)")
            for document_id in results:
                document = index.documents[document_id]
                print(f"{document['title'] or document_id}\t{document['url'] or document['path']}")
    except (OSError, ValueError, RecursionError) as error:
        parser.exit(2, f"Error: {error}\n")


if __name__ == "__main__":

    main()
