import json

from visat import live, news, reactions


def _boom():
    raise TimeoutError("no network")


def test_live_falls_back_to_snapshot(tmp_path):
    snap = tmp_path / "snap.json"
    snap.write_text(json.dumps({"temp_c": 30, "band": "Caution"}))
    out = live.get(tmp_path / "cache.json", snap, fetcher=_boom)
    assert out["status"] == "snapshot" and out["temp_c"] == 30


def test_live_unavailable_never_raises(tmp_path):
    assert live.get(tmp_path / "a.json", tmp_path / "b.json", fetcher=_boom)["status"] == "unavailable"


def test_news_hidden_without_any_data(tmp_path):
    assert news.get(tmp_path / "a.json", tmp_path / "b.json", fetcher=_boom) is None


def test_malayalam_chillu_normalisation():
    assert news.normalize("അലര്‍ട്ട്") == news.normalize("അലർട്ട്")


def test_news_classification():
    assert news.classify("യുഎഇയിൽ ചൂട് കൂടും") is None  # Gulf story excluded
    tag = news.classify("എറണാകുളം ജില്ലയിൽ ചൂട് കൂടും; യെല്ലോ അലർട്ട്")
    assert tag == {"kind": "heat", "colour": "Yellow"}


def test_news_classification_handles_inflected_malayalam_forms():
    # Real headlines almost always inflect place/heat words rather than using
    # the bare dictionary form (e.g. "in Ernakulam" is "എറണാകുളത്ത്", not
    # "എറണാകുളം" + a separate word) -- these must still match.
    assert news.classify("എറണാകുളത്ത് ചൂട് ജാഗ്രത") is not None
    assert news.classify("കൊല്ലത്ത് ചൂട് കൂടുന്നു") is not None
    assert news.classify("കോട്ടയത്ത് ചൂട് കൂടുന്നു") is not None
    assert news.classify("കേരളത്തിൽ ചൂടേറുന്നു") is not None  # "heat is rising"
    # and unrelated Kerala news, or Gulf heat in its inflected form, must
    # still be excluded -- the fix must not create new false positives.
    assert news.classify("കേരളത്തിൽ തെരഞ്ഞെടുപ്പ് പ്രഖ്യാപിച്ചു") is None
    assert news.classify("ദുബായിൽ ചൂട് കൂടുന്നു") is None


def test_news_chip_counts_channels():
    items = [{"title": "a", "channel": c, "time": "2026-04-23T10:00", "kind": "heat", "colour": None,
              "link": "x"} for c in ("Asianet", "24 News", "Asianet")]
    chip = news.chip(items, today="2026-04-23")
    assert chip["n_channels"] == 2 and chip["confirmed"]


def test_number_guard_drops_invented_numbers():
    facts = "It would add 1.3 °C for about 4200 people, costing ₹38 lakh."
    data = {"personas": [
        {"persona_id": "a", "top_concern": "shade", "would_change_mind_if": "", "quote_en": "1.3 °C is a lot"},
        {"persona_id": "b", "top_concern": "cost", "would_change_mind_if": "", "quote_en": "It will cost 90 lakh"},
    ]}
    out = reactions.number_guard(data, facts)
    assert [p["persona_id"] for p in out["personas"]] == ["a"] and out["guard_dropped"] == 1
