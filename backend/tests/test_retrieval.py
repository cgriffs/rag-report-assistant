from app.chunking import chunk_document
from app.retrieval import DocumentIndex


def build_index() -> DocumentIndex:
    index = DocumentIndex()
    index.add(
        chunk_document(
            "emissions.md",
            "Scope 1 emissions were 31,870 tonnes, driven mainly by natural "
            "gas combustion at the Port Alice generation station.",
        )
    )
    index.add(
        chunk_document(
            "operations.md",
            "First time fix rate reached 87 percent, the highest since the "
            "company began tracking it in 2024.",
        )
    )
    index.add(
        chunk_document(
            "picnic.md",
            "The staff picnic will be held at the lakeside park with a "
            "barbecue lunch and lawn games for everyone.",
        )
    )
    return index


def test_retrieval_ranks_relevant_document_first():
    results = build_index().search("What were the Scope 1 emissions?", top_k=3)
    assert results
    assert results[0].chunk.document_name == "emissions.md"
    assert results[0].score > 0


def test_retrieval_scores_descend():
    results = build_index().search("fix rate", top_k=3)
    scores = [item.score for item in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0].chunk.document_name == "operations.md"


def test_retrieval_no_match_returns_empty():
    results = build_index().search("quantum entanglement photon", top_k=3)
    assert results == []


def test_retrieval_empty_index():
    assert DocumentIndex().search("anything") == []
