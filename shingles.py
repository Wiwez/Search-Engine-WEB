"""Find near-duplicate pages using word shingles and Jaccard similarity."""

from bs4 import BeautifulSoup


def visible_text(html):
    """Extract page text while leaving out common navigation and hidden code."""
    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "nav", "footer", "aside", "form"]):
        element.decompose()
    content = soup.find("article") or soup.find("main") or soup
    return content.get_text(" ", strip=True)


def shingles(text, k=5):
    """Return a set of consecutive, case-insensitive k-word sequences."""
    words = text.casefold().split()
    return {tuple(words[i:i + k]) for i in range(len(words) - k + 1)}


def jaccard_similarity(doc1, doc2, k=5):
    """Return the Jaccard similarity of two documents, from 0 to 1."""
    first = shingles(doc1, k)
    second = shingles(doc2, k)
    if not first and not second:
        return 1.0
    return len(first & second) / len(first | second)


def find_near_duplicates(pages, threshold=0.85, k=5):
    """Compare (url, html) pages with earlier unique pages.

    Return one record per duplicate. A page with fewer than k words is ignored
    because it does not contain enough text for a meaningful comparison.
    """
    if not 0 < threshold <= 1:
        raise ValueError("threshold must be between 0 and 1")
    if k < 1:
        raise ValueError("k must be positive")

    unique_pages = []
    duplicates = []

    for url, html in pages:
        current = shingles(visible_text(html), k)
        if not current:
            continue

        for original_url, original in unique_pages:
            # Jaccard similarity cannot exceed the ratio of the set sizes.
            if min(len(current), len(original)) / max(len(current), len(original)) < threshold:
                continue

            similarity = len(current & original) / len(current | original)
            if similarity >= threshold:
                duplicates.append({
                    "url": url,
                    "duplicate_of": original_url,
                    "similarity": round(similarity, 4),
                })
                break
        else:
            unique_pages.append((url, current))

    return duplicates
