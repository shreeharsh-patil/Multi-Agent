from src.api.routes._chat_quality import _grounding_search_queries


def test_entity_query_variants_preserve_qualifier_and_quote_acronym():
    queries = _grounding_search_queries("Where is Pcce goa?")
    assert queries[0] == "Where is Pcce goa?"
    assert "Pcce goa" in queries
    assert '"Pcce" goa' in queries
    assert any(query.endswith("official") for query in queries)


def test_entity_query_variants_do_not_invent_acronym_expansion():
    queries = _grounding_search_queries("Where is ABCD Pune?")
    joined = " ".join(queries).lower()
    assert "abcd" in joined
    assert "pune" in joined
    assert "college" not in joined
    assert "university" not in joined


def test_non_location_request_still_stays_bounded():
    queries = _grounding_search_queries("Tell me about OpenAI")
    assert 1 <= len(queries) <= 4
    assert queries[0] == "Tell me about OpenAI"
