def shingles(text, k=3):
    """
    Convert a document into a set of k-word shingles.
    """
    words = text.lower().split()

    return {
        tuple(words[i:i + k])
        for i in range(len(words) - k + 1)
    }


def jaccard_similarity(doc1, doc2, k=3, threshold=0.5):
    """
    Compute Jaccard similarity between two documents.
    """
    s1 = shingles(doc1, k)
    s2 = shingles(doc2, k)

    if not s1 and not s2:
        return 1.0

    intersection = len(s1 & s2)
    union = len(s1 | s2)

    Similarity = intersection/union >= threshold
    print(Similarity)
    return intersection / union 




doc1 = "the quick brown fox jumps over the lazy dog"
doc2 = "the quick brown fox jumps over a lazy dog"

score = jaccard_similarity(doc1, doc2)

print("Similarity:", score)
