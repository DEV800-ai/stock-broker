from broker.data.edgar import classify_filing, format_filings_for_prompt, score_filings


def test_classify_filing_material_event():
    assert classify_filing({"form": "8-K"}) == ("material_event", 0.7)


def test_classify_filing_earnings_report():
    assert classify_filing({"form": "10-Q"}) == ("earnings_report", 0.6)


def test_classify_filing_annual_report():
    assert classify_filing({"form": "10-K"}) == ("annual_report", 0.6)


def test_classify_filing_dilution():
    for form in ("S-1", "S-3", "424B5"):
        event_type, weight = classify_filing({"form": form})
        assert event_type == "dilution"
        assert weight < 0


def test_classify_filing_ownership():
    assert classify_filing({"form": "SC 13D"}) == ("ownership_activist", 0.5)
    assert classify_filing({"form": "SC 13G"}) == ("ownership_passive", 0.2)


def test_classify_filing_insider():
    assert classify_filing({"form": "4"}) == ("insider", 0.3)


def test_classify_filing_proxy():
    assert classify_filing({"form": "DEF 14A"}) == ("proxy", 0.1)


def test_classify_filing_unknown_form():
    assert classify_filing({"form": "NT 10-K"}) == (None, 0.0)


def test_score_filings_empty():
    assert score_filings([]) == 0.0


def test_score_filings_range():
    filings = [{"form": "8-K"}, {"form": "10-Q"}, {"form": "S-1"}]
    score = score_filings(filings)
    assert 0.0 <= score <= 1.0


def test_format_filings_for_prompt_empty():
    assert format_filings_for_prompt([]) == ""


def test_format_filings_for_prompt_includes_form_and_tag():
    filings = [{"form": "8-K", "filingDate": "2026-08-01", "url": "https://example.com/x"}]
    text = format_filings_for_prompt(filings)
    assert "8-K" in text
    assert "[material_event]" in text
    assert "2026-08-01" in text


def test_format_filings_for_prompt_respects_max_items():
    filings = [{"form": "8-K", "filingDate": f"2026-08-{i:02d}", "url": "u"} for i in range(1, 8)]
    text = format_filings_for_prompt(filings, max_items=3)
    assert len(text.splitlines()) == 3
