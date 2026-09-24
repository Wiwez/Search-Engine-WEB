"""Build an inverted index of saved HTML and evaluate Boolean queries."""

import argparse  # Provides tools for handling command-line arguments.
import json  # Used to save/load Python data as JSON, e.g. {"version": 1} <-> JSON text.
from pathlib import Path  # Handles file paths, e.g. Path("pages") represents the pages directory.
import re  # Provides regular expressions, e.g. extracting words from "hello, world!".
import unicodedata  # Provides Unicode normalization, e.g. making equivalent Unicode characters consistent.

from bs4 import BeautifulSoup  # Parses HTML, e.g. "<title>News</title>" can be accessed as soup.title.
from shingles import visible_text  # Extracts readable page text, e.g. HTML tags are removed from the content.


def tokenize(text):
    """Case-fold Unicode words/numbers; punctuation separates terms."""

    text = unicodedata.normalize("NFKC", text).casefold()  # Normalizes/lowercases text, e.g. "Python CAFÉ" -> "python café".
    return re.findall(r"[^\W_]+", text, flags=re.UNICODE)  # Splits into terms, e.g. "hello, WORLD 123!" -> ["hello", "world", "123"].


class InvertedIndex:

    def __init__(self):
        self.documents = {}  # Stores document metadata, e.g. {"1.html": {"title": "News", "url": "https://example.com"}}.
        self.postings = {}  # Stores which documents contain each term, e.g. {"cat": {"1.html", "3.html"}}.

    def add_document(self, document_id, html, url="", path=""):

        if document_id in self.documents:  # Checks if the ID is already stored, e.g. adding "1.html" twice is rejected.
            raise ValueError(f"Duplicate document ID: {document_id}")  # Stops indexing instead of overwriting the existing document.

        soup = BeautifulSoup(html, "html.parser")  # Converts HTML text into a parsed object, e.g. "<title>News</title>" -> soup.title.
        title = soup.title.get_text(" ", strip=True) if soup.title else ""  # Extracts title text, e.g. "<title> BBC News </title>" -> "BBC News".

        self.documents[document_id] = {"url": url, "path": path, "title": title}  # Stores metadata, e.g. documents["1.html"] -> {"url": "...", "path": "...", "title": "News"}.

        for term in set(tokenize(title + " " + visible_text(html))):  # Converts page text into unique terms, e.g. "Cat cat DOG" -> {"cat", "dog"}.
            self.postings.setdefault(term, set()).add(document_id)  # Adds the document to that term, e.g. postings["cat"] -> {"1.html", "3.html"}.

    @classmethod
    def from_directory(cls, directory):

        directory = Path(directory)  # Converts a string into a Path object, e.g. "pages" -> Path("pages").

        if not directory.is_dir():  # Checks whether the path is an existing directory, e.g. missing "pages" -> False.
            raise ValueError(f"Page directory does not exist: {directory}")  # Stops because there is no directory to index.

        files = sorted(directory.glob("*.html"))  # Finds/sorts HTML files, e.g. pages/ -> ["1.html", "2.html", "3.html"].

        if not files:  # Checks whether any HTML files were found, e.g. [] means the directory contains no .html files.
            raise ValueError(f"No HTML pages found in {directory}; crawl or use examples/pages")  # Stops because there are no pages to index.

        index = cls()  # Creates a new empty index, e.g. documents={} and postings={}.

        for path in files:  # Goes through each HTML file one at a time, e.g. "1.html", then "2.html", then "3.html".
            html = path.read_text(encoding="utf-8")  # Loads the file into a string, e.g. 1.html -> "<html><title>News</title>...</html>".
            match = re.match(r"\s*<!-- URL:\s*(.*?)\s*-->", html)  # Extracts a saved URL, e.g. "<!-- URL: https://example.com -->" -> "https://example.com".
            index.add_document(path.name, html, match.group(1) if match else "", str(path))  # Adds the page, e.g. ID="1.html", URL="https://example.com", path="pages/1.html".

        return index  # Returns the finished index, e.g. an index containing all HTML documents and their terms.

    def save(self, path):

        data = {  # Creates the dictionary that will be written to JSON.
            "version": 1,  # Stores the index format version, e.g. version=1 lets load() know which format to expect.
            "documents": self.documents,  # Copies document metadata into the saved data, e.g. {"1.html": {"title": "News", ...}}.
            "postings": {term: sorted(ids) for term, ids in sorted(self.postings.items())},  # Converts sets to lists for JSON, e.g. {"cat": {"2","1"}} -> {"cat": ["1","2"]}.
        }

        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")  # Converts data to JSON and saves it, e.g. data -> index.json.

    @classmethod
    def load(cls, path):

        data = json.loads(Path(path).read_text(encoding="utf-8"))  # Reads/parses JSON, e.g. '{"version": 1}' -> {"version": 1}.

        if data.get("version") != 1:  # Checks the stored format version, e.g. version=2 would be rejected.
            raise ValueError("Unsupported index version; rebuild the index")  # Stops if the file format is incompatible.

        index = cls()  # Creates a new empty InvertedIndex before restoring the saved data.
        index.documents = data["documents"]  # Restores metadata, e.g. data["documents"] -> index.documents.
        index.postings = {term: set(ids) for term, ids in data["postings"].items()}  # Restores lists as sets, e.g. {"cat": ["1","2"]} -> {"cat": {"1","2"}}.

        return index  # Returns the fully restored index so it can be searched.

    def search(self, query):
        """Return sorted IDs. Precedence: NOT > AND > OR; explicit operators."""

        tokens = re.findall(r"\(|\)|[^\s()]+", query)  # Splits the query, e.g. "cat AND (dog OR fish)" -> ["cat","AND","(","dog","OR","fish",")"].
        position = 0  # Tracks the current token, e.g. position=0 means tokens[0] is being processed.
        universe = set(self.documents)  # Creates all document IDs, e.g. {"1.html", "2.html", "3.html"} for use with NOT.

        def take(token):

            nonlocal position  # Lets this function modify position from the outer search() function.

            if position < len(tokens) and tokens[position] == token:  # Checks current token, e.g. tokens[1]="AND" matches take("AND").
                position += 1  # Moves to the next token, e.g. position 1 -> 2.
                return True  # Reports that the expected token was found and consumed.

            return False  # Reports that the expected token was not at the current position.

        def primary():

            nonlocal position  # Lets primary() move through the shared token list.

            if take("NOT"):  # Detects NOT, e.g. "NOT cat".
                return universe - primary()  # Removes matching docs, e.g. {1,2,3} - cat:{1,3} -> {2}.

            if take("("):  # Detects the start of a grouped expression, e.g. "(cat OR dog)".
                result = disjunction()  # Evaluates the expression inside (), e.g. cat:{1} OR dog:{2} -> {1,2}.

                if not take(")"):  # Checks that the group ends correctly, e.g. "(cat OR dog" has no ")".
                    raise ValueError("Missing closing parenthesis")  # Rejects the malformed query.

                return result  # Returns the result of the grouped expression, e.g. "(cat OR dog)" -> {1,2}.

            if position == len(tokens) or tokens[position] in {"AND", "OR", ")"}:  # Detects when a term is missing, e.g. "cat AND AND dog".
                raise ValueError("Expected a search term, NOT, or opening parenthesis")  # Stops because the Boolean query is malformed.

            raw = tokens[position]  # Stores the current raw query term, e.g. tokens[0]="FOOTBALL" -> raw="FOOTBALL".
            position += 1  # Moves past that term, e.g. position 0 -> 1.
            terms = tokenize(raw)  # Normalizes the search term, e.g. "FOOTBALL" -> ["football"].

            if len(terms) != 1 or any(char in raw for char in '\\"\''):  # Rejects invalid terms, e.g. '"cat dog"' is not one plain word.
                raise ValueError(f"Expected one word or number: {raw!r}; use explicit AND/OR")  # Requires something like "cat AND dog" instead.

            return set(self.postings.get(terms[0], set()))  # Gets matching docs, e.g. postings["cat"] -> {"1.html", "3.html"}; unknown term -> set().

        def conjunction():

            result = primary()  # Gets the first result set, e.g. "cat" -> {1,2,3}.

            while take("AND"):  # Continues while AND operators exist, e.g. "cat AND dog AND fish".
                result &= primary()  # Keeps common documents, e.g. {1,2,3} AND {2,3,4} -> {2,3}.

            return result  # Returns the final AND result, e.g. "cat AND dog" -> {2,3}.

        def disjunction():

            result = conjunction()  # Evaluates AND first, e.g. "cat AND dog OR fish" calculates "cat AND dog" first.

            while take("OR"):  # Continues while OR operators exist, e.g. "cat OR dog OR fish".
                result |= conjunction()  # Combines matching docs, e.g. {1,2} OR {2,3} -> {1,2,3}.

            return result  # Returns the final OR result, e.g. "cat OR dog" -> {1,2,3}.

        if not tokens:  # Checks for an empty query, e.g. "" -> [].
            raise ValueError("Query must not be empty")  # Stops because there is nothing to search for.

        result = disjunction()  # Evaluates the full query, e.g. "cat AND dog OR fish" -> a set of matching document IDs.

        if position != len(tokens):  # Checks if unprocessed tokens remain, e.g. lowercase "and" may remain as unexpected syntax.
            raise ValueError(f"Unexpected token {tokens[position]!r}; use uppercase AND, OR, NOT")  # Explains that Boolean operators must be uppercase.

        return sorted(result)  # Converts/sorts the result, e.g. {"3.html","1.html"} -> ["1.html","3.html"].


def startIndexing():

    print("Starting indexing...")  # Prints a message showing that the program has started.
    print("Do you wanna build an index or search an existing index?")  # Tells the user which two actions are available.

    answer = input("Type 'build' to build an index or 'query' to search an existing index: ").strip().lower()  # Cleans input, e.g. "  BUILD " -> "build".

    if answer == "build":  # Runs this section when the cleaned input is "build".

        index = InvertedIndex.from_directory("pages")  # Builds an index from pages/, e.g. 10 HTML files -> 10 indexed documents.
        index.save("index.json")  # Stores the completed index in index.json so it can be loaded later.
        print(f"Indexed {len(index.documents)} documents and {len(index.postings)} terms -> index.json")  # Shows totals, e.g. "Indexed 10 documents and 534 terms".

    elif answer == "query":  # Runs this section when the cleaned input is "query".

        index = InvertedIndex.load("index.json")  # Restores the saved index, e.g. index.json -> InvertedIndex object.
        query = input("Enter your query (e.g., 'sport AND NOT fodbold'): ").strip()  # Stores user input, e.g. "cat AND dog".
        results = index.search(query)  # Evaluates the query, e.g. "cat AND dog" -> ["1.html", "4.html"].

        print(f"{len(results)} result(s)")  # Prints the result count, e.g. 2 matches -> "2 result(s)".

        for document_id in results:  # Loops through each matching ID, e.g. ["1.html","4.html"] one at a time.
            document = index.documents[document_id]  # Gets its metadata, e.g. "1.html" -> {"title": "News", "url": "https://...", ...}.
            print(f"{document['title'] or document_id}\t{document['url'] or document['path']}")  # Prints title + location, using ID/path as fallbacks if title/URL are empty.

    else:  # Runs when the user enters something other than "build" or "query".
        print("Invalid option. Please type 'build' or 'query'.")  # Tells the user which values are accepted.