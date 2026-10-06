from ragbase.generation.citation import validate_citations


def test_valid_citations_and_unknown_ids():
    assert validate_citations("Ten sick days. [S1]", ["S1"]).valid
    invalid = validate_citations("A claim. [S99]", ["S1"])
    assert not invalid.valid
    assert invalid.invalid_ids == ["S99"]


def test_duplicate_citations_are_deduplicated_and_missing_is_detected():
    result = validate_citations("First. [S1] Second. [S1]", ["S1"])
    assert result.valid
    assert result.cited_ids == ["S1"]
    assert result.duplicate_count == 1
    assert validate_citations("No source given.", ["S1"]).missing
    assert not validate_citations("No source given.", ["S1"]).valid
