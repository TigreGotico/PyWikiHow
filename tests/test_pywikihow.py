import os

import pytest

import pywikihow
from pywikihow import HowTo, RandomHowTo, search_wikihow
from pywikihow.exceptions import ParseError, UnsupportedLanguage

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _fixture(name):
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


TIE_A_TIE = _fixture("tie_a_tie.html")
FOLD_FITTED_SHEET = _fixture("fold_fitted_sheet.html")
CONTAR_CELULAS_PT = _fixture("contar_celulas_pt.html")
SEARCH_BITCOIN = _fixture("search_bitcoin.html")
NOT_FOUND = _fixture("not_found.html")


def _patch_get_html(monkeypatch, mapping):
    """mapping: dict of substring -> fixture bytes, checked in order."""

    def fake_get_html(url):
        for substring, body in mapping.items():
            if substring in url:
                return body
        raise AssertionError(f"unexpected URL fetched in test: {url}")

    monkeypatch.setattr(pywikihow, "get_html", fake_get_html)


class TestHowToHappyPath:
    def test_parses_title_url_intro_and_steps(self, monkeypatch):
        _patch_get_html(monkeypatch, {"Tie-a-Tie": TIE_A_TIE})
        how = HowTo("https://www.wikihow.com/Tie-a-Tie", lazy=False)

        assert how.title == "Tie a Tie"
        assert how.url == "https://www.wikihow.com/Tie-a-Tie"
        assert how.intro
        assert how.n_steps == 36
        assert how.steps[0].summary == "Drape the tie around your neck."

    def test_as_dict_roundtrip(self, monkeypatch):
        _patch_get_html(monkeypatch, {"Tie-a-Tie": TIE_A_TIE})
        how = HowTo("https://www.wikihow.com/Tie-a-Tie", lazy=False)
        d = how.as_dict()

        assert d["title"] == how.title
        assert d["n_steps"] == how.n_steps
        assert len(d["steps"]) == how.n_steps
        assert d["steps"][0]["summary"] == how.steps[0].summary

    def test_lazy_parsing_defers_until_first_access(self, monkeypatch):
        _patch_get_html(monkeypatch, {"Tie-a-Tie": TIE_A_TIE})
        how = HowTo("https://www.wikihow.com/Tie-a-Tie")
        assert how._parsed is False
        assert how.title == "Tie a Tie"
        assert how._parsed is True


class TestPictureBug:
    """Regression tests for the step-picture correlation bug.

    wikiHow no longer nests step images inside their `div.step`, and no
    longer uses a `data-src` attribute for the final image URL. The old
    code assumed both, so `HowToStep.picture` was always empty and, on
    pages with more images than steps, `_parse_pictures` could raise an
    uncaught IndexError (masked as a generic ParseError).
    """

    def test_pictures_are_populated_from_src(self, monkeypatch):
        _patch_get_html(monkeypatch, {"Tie-a-Tie": TIE_A_TIE})
        how = HowTo("https://www.wikihow.com/Tie-a-Tie", lazy=False)

        pictured = [s for s in how.steps if s.picture]
        assert pictured, "no step picture was populated"
        for step in pictured:
            assert step.picture.startswith("http")

    def test_pictures_correlate_to_the_right_step(self, monkeypatch):
        _patch_get_html(monkeypatch, {"Tie-a-Tie": TIE_A_TIE})
        how = HowTo("https://www.wikihow.com/Tie-a-Tie", lazy=False)

        # Step-1 image must land on the first step (index 0), not on
        # whichever step happens to be next in image-list order.
        step_1_pic = how.steps[0].picture
        assert step_1_pic is not None
        assert "Step-1-" in step_1_pic

    def test_multi_part_page_does_not_raise_index_error(self, monkeypatch):
        # This page has more <a class="image"> links (12, including the
        # summary image) than the article's step count, and images are
        # spread unevenly across three "parts"/sections. Before the fix
        # this raised IndexError -> masked as ParseError.
        _patch_get_html(
            monkeypatch, {"Fold-a-Fitted-Sheet": FOLD_FITTED_SHEET}
        )
        how = HowTo("https://www.wikihow.com/Fold-a-Fitted-Sheet", lazy=False)

        assert how.n_steps == 11
        # first step of the article has a picture, correctly assigned
        assert how.steps[0].picture is not None
        assert "Step-1-" in how.steps[0].picture
        # the summary/intro image (no "Step-N" token) must never bleed
        # into a step's picture
        assert all(
            step.picture is None or "Summary" not in step.picture
            for step in how.steps
        )


class TestTitleUnicodeBug:
    """Regression test: non-ASCII titles must be percent-decoded."""

    def test_title_is_url_decoded(self, monkeypatch):
        _patch_get_html(
            monkeypatch, {"Contar-C%C3%A9lulas": CONTAR_CELULAS_PT}
        )
        how = HowTo(
            "https://pt.wikihow.com/Contar-C%C3%A9lulas-no-Google-"
            "Planilhas-no-Windows-ou-Mac",
            lazy=False,
        )
        assert "%" not in how.title
        assert "Células" in how.title


class TestSearch:
    def test_search_yields_howto_objects(self, monkeypatch):
        _patch_get_html(
            monkeypatch,
            {
                "wikiHowTo?search": SEARCH_BITCOIN,
                "Tie-a-Tie": TIE_A_TIE,
            },
        )
        # every result link resolves through the same stand-in fixture;
        # this exercises pagination/max_results, not per-result content
        monkeypatch.setattr(
            HowTo,
            "_parse",
            lambda self: setattr(self, "_parsed", True) or setattr(
                self, "_title", "stub"
            ),
        )
        results = search_wikihow("buy bitcoin", max_results=3)
        assert len(results) == 3

    def test_search_url_encodes_special_characters(self, monkeypatch):
        captured = {}

        def fake_get_html(url):
            captured["url"] = url
            return SEARCH_BITCOIN

        monkeypatch.setattr(pywikihow, "get_html", fake_get_html)
        monkeypatch.setattr(
            HowTo,
            "_parse",
            lambda self: setattr(self, "_parsed", True) or setattr(
                self, "_title", "stub"
            ),
        )
        search_wikihow("buy bitcoin & stocks", max_results=1)
        assert "&" not in captured["url"].split("search=", 1)[1]
        assert "%26" in captured["url"] or "+" not in captured["url"]

    def test_unsupported_language_raises(self):
        with pytest.raises(UnsupportedLanguage):
            search_wikihow("anything", lang="xx")

    def test_random_howto_unsupported_language_raises(self):
        with pytest.raises(UnsupportedLanguage):
            RandomHowTo(lang="xx")


class TestMalformedInput:
    def test_missing_title_raises_parse_error(self, monkeypatch):
        _patch_get_html(monkeypatch, {"ThisPageDoesNotExist": NOT_FOUND})
        how = HowTo(
            "https://www.wikihow.com/Special:ThisPageDoesNotExist123456"
        )
        with pytest.raises(ParseError):
            how._parse()

    def test_parse_error_preserves_original_cause(self, monkeypatch):
        # Regression test: `raise ParseError` used to discard the
        # underlying exception, making failures unfixable to debug (this
        # masked the IndexError picture bug above as a bare ParseError).
        _patch_get_html(monkeypatch, {"ThisPageDoesNotExist": NOT_FOUND})
        how = HowTo(
            "https://www.wikihow.com/Special:ThisPageDoesNotExist123456"
        )
        try:
            how._parse()
            pytest.fail("expected ParseError")
        except ParseError as exc:
            assert exc.__cause__ is not None
