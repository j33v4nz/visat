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
