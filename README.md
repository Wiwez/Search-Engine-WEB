# Search-Engine-WEB
Search Engine WEB

Install dependencies with `python -m pip install -r requirements.txt`.

Run `python main.py` to crawl `https://www.bt.dk` (up to 35 attempted URLs).
The crawler saves HTML in `pages/`. After the crawl, it compares the visible
text of downloaded pages using five-word shingles and Jaccard similarity.
Pages with a similarity of at least 0.85 are listed in `near_duplicates.json`:

```json
[
  {
    "url": "https://example.com/copy",
    "duplicate_of": "https://example.com/original",
    "similarity": 0.92
  }
]
```

Each duplicate is matched to the first similar unique page encountered. The
original HTML files are kept. The threshold can be changed with
`crawl(seed_url, max_pages=1000, near_duplicate_threshold=0.85)`.

## Indexing saved pages

Build an index after crawling, then query it without downloading pages again:

```sh
python indexing.py build --pages pages --output index.json
python indexing.py query 'sport AND NOT fodbold'
python indexing.py query '(danmark OR københavn) AND politik'
```

The builder reads `.html` files directly inside the selected directory. Each
filename becomes a document ID. The JSON index stores a dictionary from each
term to its sorted list of document IDs (its *posting list*), plus document
titles, local paths, and URLs extracted from the crawler's HTML comments.
Queries load these lists as sets: AND intersects, OR unions, and NOT subtracts
from the set of **all indexed documents**, including documents without terms.
Results show titles and URLs, ordered by document ID; they are not ranked.
Rebuild the index whenever the saved pages change.

Operators must be uppercase; use lowercase `and`, `or`, or `not` to search
those words themselves. Precedence is `NOT`, then `AND`, then `OR`.
Parentheses override precedence. Put shell queries in quotes. Adjacent words
require an explicit operator; phrase queries and quoted terms are unsupported.
Unknown words match no documents, so `NOT unknownword` matches every document
when that word is absent from the index.

## Small debugging example

`examples/pages/` contains three pages with these main texts:

| ID | Text |
| --- | --- |
| d1.html | Cat dog. København æble. |
| d2.html | Dog bird. KØBENHAVN. |
| d3.html | Cat fish. Århus. |

```sh
python indexing.py build --pages examples/pages --output /tmp/example-index.json
python indexing.py query 'cat AND dog' --index /tmp/example-index.json
python indexing.py query 'cat AND NOT dog' --index /tmp/example-index.json
python indexing.py query '(cat OR dog) AND bird' --index /tmp/example-index.json
python indexing.py query 'KØBENHAVN' --index /tmp/example-index.json
python -m unittest discover -v
```

Expected results in order: d1; d3; d2; d1 and d2. For comparison,
`cat OR dog AND bird` returns all three documents because AND binds first.
Replace these example pages with your exercise-session example if it differs.

## Exam discussion: decisions and corners cut

- **Text extraction:** Reuse the crawler's `visible_text` helper, removing
  scripts, styles, noscript, navigation, footers, sidebars, and forms. Prefer
  the first article, then the first main element, otherwise the full document.
  Also index the page title. This reduces boilerplate but can discard relevant
  text in other articles or sidebars. It does not render JavaScript or interpret
  CSS, so dynamically loaded content is absent and some hidden text may remain.
- **Normalization:** Decode HTML entities through BeautifulSoup; apply Unicode
  NFKC and case folding; extract Unicode letter/number sequences. Punctuation,
  hyphens, apostrophes, and underscores separate indexed terms. Apply the same
  tokenizer to query terms. This merges case and compatibility variants but
  loses punctuation distinctions (for example, C++ becomes c). Accents and
  Danish æ/ø/å remain distinct, so `arhus` does not match `århus`. In queries,
  write split terms explicitly, e.g. `well AND known` for `well-known`.
- **No stop-word removal:** Keep common words so Boolean queries can search
  them. This makes the index larger and common-word posting lists longer.
- **No stemming or lemmatization:** Avoid introducing language-specific rules
  for Danish and English. Inflected forms such as `dog` and `dogs` stay separate,
  reducing recall unless the user combines them with OR.
- **Presence only:** Store no term counts or word positions. Repeated words do
  not change Boolean results. There is no relevance ranking, phrase matching,
  proximity search, spelling correction, or wildcard expansion.
- **Small-corpus implementation:** Build and query in memory with Python sets,
  and persist readable JSON. Index construction processes each page's text;
  queries use posting lists instead of scanning HTML. JSON and sets have memory
  overhead, NOT can produce nearly the entire collection, and there is no
  compression, query optimization, incremental updating, or distributed index.
- **Duplicates:** Index every saved file, including near-duplicates reported by
  the crawler. This preserves the stored collection but can give repeated results.
- **Validation limits:** Automated tests cover known Boolean answers,
  precedence, parentheses, negation, Unicode normalization, extraction,
  malformed queries, and persistence. The example establishes correctness on
  a tiny corpus; it does not measure retrieval quality or large-corpus speed.
  The `pages/` directory was empty during implementation, so validation used
  the included example rather than last week's crawl.
