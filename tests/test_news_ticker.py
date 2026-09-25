from visat import config
from visat.news_ticker import (
    NewsItem,
    _extract_alert_colour,
    _extract_districts,
    _matches_any,
    _parse_rss,
    group_confirmations,
    normalise_malayalam,
)

ATOMIC_ALERT = "എറണാകുളത്ത് യെല്ലോ അലർട്ട്"  # atomic chillu rr (U+0D7C)
DECOMPOSED_ALERT = "എറണാകുളത്ത് യെല്ലോ അലര്‍ട്ട്"  # ra + virama + ZWJ


def test_chillu_variants_normalise_to_the_same_string():
    assert normalise_malayalam(ATOMIC_ALERT) == normalise_malayalam(DECOMPOSED_ALERT)


def test_decomposed_variant_still_matches_atomic_keyword():
    # config keywords are written with the atomic chillu form; a headline
    # using the decomposed + ZWJ spelling must still match.
    assert _matches_any(DECOMPOSED_ALERT, config.NEWS_ALERT_COLOUR_KEYWORDS)


def test_heat_keyword_detection():
    assert _matches_any("കേരളത്തിൽ ചൂട് കൂടുന്നു", config.NEWS_HEAT_KEYWORDS)
    assert not _matches_any("ദുബായിൽ മഴ പെയ്തു", config.NEWS_HEAT_KEYWORDS)


def test_district_extraction():
    assert "എറണാകുളം" in _extract_districts("എറണാകുളത്ത് ചൂട് കൂടുന്നു")


def test_district_extraction_handles_inflected_locative_form():
    # "എറണാകുളത്ത്" = "in Ernakulam" (locative case) — not a substring of
    # the nominative "എറണാകുളം", the form the keyword list uses.
    assert "എറണാകുളം" in _extract_districts("എറണാകുളത്തെ ചൂട് ജാഗ്രത")


def test_alert_colour_extraction():
    assert _extract_alert_colour(ATOMIC_ALERT) == "yellow"
    assert _extract_alert_colour("സാധാരണ വാർത്ത") is None


def test_parse_rss_extracts_items():
    xml = """<?xml version="1.0"?>
    <rss><channel>
        <item>
            <title>എറണാകുളത്ത് ചൂട് കൂടുന്നു</title>
            <link>https://example.com/1</link>
            <pubDate>Fri, 25 Sep 2026 10:00:00 GMT</pubDate>
        </item>
        <item>
            <title>Unrelated sports news</title>
            <link>https://example.com/2</link>
            <pubDate>Fri, 25 Sep 2026 09:00:00 GMT</pubDate>
        </item>
    </channel></rss>
    """
    items = _parse_rss(xml, "test_source")
    assert len(items) == 2
    assert items[0].is_heat is True
    assert items[1].is_heat is False


def test_parse_rss_handles_malformed_xml_gracefully():
    assert _parse_rss("not xml at all <<<", "test_source") == []


def test_group_confirmations_counts_distinct_sources():
    items = [
        NewsItem("t1", "Asianet", "l1", "p1", districts=["എറണാകുളം"], alert_colour="yellow", is_heat=True),
        NewsItem("t2", "24 News", "l2", "p2", districts=["എറണാകുളം"], alert_colour="yellow", is_heat=True),
        NewsItem("t3", "Mathrubhumi", "l3", "p3", districts=["Kollam"], alert_colour="orange", is_heat=True),
    ]
    groups = group_confirmations(items)
    ek_group = next(g for g in groups if g["district"] == "എറണാകുളം")
    assert ek_group["n_channels"] == 2
    assert ek_group["confirmed"] is True

    kollam_group = next(g for g in groups if g["district"] == "Kollam")
    assert kollam_group["n_channels"] == 1
    assert kollam_group["confirmed"] is False


def test_group_confirmations_skips_non_heat_items():
    items = [NewsItem("t1", "Asianet", "l1", "p1", is_heat=False)]
    assert group_confirmations(items) == []
