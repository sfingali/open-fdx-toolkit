"""Tests for the PDF screenplay importer (pdf_import.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_import import (
    _detect_margins,
    _is_initials_name,
    _strip_contd,
    LayoutLine,
    extract_layout_lines,
    parse_pdf,
)

SAMPLE_PDF = os.environ.get("SAMPLE_PDF", "")
SAMPLE_FDX = os.environ.get("SAMPLE_FDX", "")

pymupdf = pytest.importorskip("pymupdf")


class TestHelpers:
    def test_detect_margins_three_bands(self):
        lines = [
            LayoutLine("action", 89.0),
            LayoutLine("action2", 89.0),
            LayoutLine("dialogue", 183.0),
            LayoutLine("dialogue2", 183.0),
            LayoutLine("cue", 269.0),
            LayoutLine("cue2", 269.0),
        ]
        a, d, c = _detect_margins(lines)
        assert a == 89.0
        assert d == 183.0
        assert c == 269.0

    def test_strip_contd(self):
        assert _strip_contd("BEN (cont'd)") == "BEN"
        assert _strip_contd("BEN (CONT'D)") == "BEN"
        assert _strip_contd("MARIE (O.S.)") == "MARIE (O.S.)"

    def test_initials_name(self):
        assert _is_initials_name("T.R.")
        assert _is_initials_name("J.R.")
        assert not _is_initials_name("BEN")
        assert not _is_initials_name("THE END")


class TestSampleGroundTruth:
    """End-to-end ground-truth: the sample script PDF vs its FDX sibling."""

    def test_pdf_extracts_scenes(self):
        if not os.path.exists(SAMPLE_PDF):
            pytest.skip("the sample script PDF not available")
        scenes = parse_pdf(SAMPLE_PDF)
        assert len(scenes) == 279  # 03-17-26 draft has 279 scenes

    def test_pdf_matches_fdx_up_to_draft_divergence(self):
        if not os.path.exists(SAMPLE_PDF) or not os.path.exists(SAMPLE_FDX):
            pytest.skip("ground-truth files not available")
        from fdx_parser import parse_file

        scenes = parse_pdf(SAMPLE_PDF)
        fdx = parse_file(SAMPLE_FDX)
        assert len(scenes) == len(fdx) + 1  # PDF draft has one extra scene

        # First 272 scenes match exactly; PDF has one extra scene at 272;
        # remaining 6 match again after the offset.
        for i in range(272):
            assert scenes[i].slugline.upper() == fdx[i].slugline.upper(), f"POS {i}"
        for i in range(272, len(fdx)):
            assert scenes[i + 1].slugline.upper() == fdx[i].slugline.upper(), f"POS {i}"

    def test_character_sets_match_fdx(self):
        if not os.path.exists(SAMPLE_PDF) or not os.path.exists(SAMPLE_FDX):
            pytest.skip("ground-truth files not available")
        import re
        from fdx_parser import parse_file

        scenes = parse_pdf(SAMPLE_PDF)
        fdx = parse_file(SAMPLE_FDX)
        norm = lambda c: re.sub(r"\s+", " ", re.sub(r"\(?\s*(?:cont'?d|contd)\s*\)?", "", c, flags=re.I)).strip()
        pdf_chars = {norm(c) for s in scenes for c in s.characters}
        fdx_chars = {norm(c) for s in fdx for c in s.characters}
        # Identical after stripping pagination (CONT'D) artifacts — the PDF
        # importer normalizes them away, the FDX file retains them.
        assert pdf_chars == fdx_chars

    def test_location_sets_match_fdx(self):
        if not os.path.exists(SAMPLE_PDF) or not os.path.exists(SAMPLE_FDX):
            pytest.skip("ground-truth files not available")
        from fdx_parser import parse_file

        scenes = parse_pdf(SAMPLE_PDF)
        fdx = parse_file(SAMPLE_FDX)
        pdf_locs = {s.location for s in scenes if s.location}
        fdx_locs = {s.location for s in fdx if s.location}
        assert pdf_locs == fdx_locs  # identical 81-location sets

    def test_title_page_skipped(self):
        if not os.path.exists(SAMPLE_PDF):
            pytest.skip("the sample script PDF not available")
        scenes = parse_pdf(SAMPLE_PDF)
        # First scene must be a real slugline, not title-page text.
        assert scenes[0].slugline.upper().startswith(("INT.", "EXT.", "INT/EXT."))
        # Title-page copy ("written by", copyright, cover lines) must not
        # leak into the first scene's paragraphs.
        first_paras = " ".join(p.text for p in scenes[0].paragraphs).upper()
        assert "WRITTEN BY" not in first_paras
        assert "KINOLIME" not in first_paras

    def test_no_continuation_artifacts(self):
        if not os.path.exists(SAMPLE_PDF):
            pytest.skip("the sample script PDF not available")
        scenes = parse_pdf(SAMPLE_PDF)
        for s in scenes:
            for c in s.characters:
                assert "(cont'd)" not in c.lower()
                assert "CONT'D" not in c.upper()

    def test_tr_initial_name_character(self):
        if not os.path.exists(SAMPLE_PDF):
            pytest.skip("the sample script PDF not available")
        scenes = parse_pdf(SAMPLE_PDF)
        chars = {c for s in scenes for c in s.characters}
        assert "T.R." in chars


class TestPrintedSceneNumbers:
    """Numbered scripts print each scene's number in both margins of its
    heading. Those numbers are the script's, so they must come through."""

    def _numbered_pdf(self, tmp_path):
        doc = pymupdf.open()
        page = doc.new_page(width=612, height=792)
        y = 72

        def put(x, text):
            page.insert_text((x, y), text, fontname="cour", fontsize=12)

        put(522, "1.")   # page number, top right
        y = 108
        for num, heading, action in [("12", "INT. HOUSE - DAY", "Ben waits."),
                                     ("12A", "EXT. HOUSE - DAY", "Rain."),
                                     ("13", "INT. CAR - NIGHT", "Ben drives.")]:
            put(54, num)
            put(108, heading)
            put(540, num)
            y += 24
            put(108, action)
            y += 36
        path = tmp_path / "numbered.pdf"
        doc.save(str(path))
        doc.close()
        return str(path)

    def test_numbers_printed_beside_headings(self, tmp_path):
        scenes = parse_pdf(self._numbered_pdf(tmp_path))
        assert [(s.scene_number, s.scene_number_source, s.slugline) for s in scenes] == [
            ("12", "script", "INT. HOUSE - DAY"),
            ("12A", "script", "EXT. HOUSE - DAY"),
            ("13", "script", "INT. CAR - NIGHT"),
        ]
        assert all(not any(n in s.body_lines for n in ("12", "12A", "13")) for s in scenes)

    def test_numbers_joined_into_the_heading_text(self):
        from pdf_import import parse_layout_lines
        lines = [LayoutLine("12INT. HOUSE - DAY12", 54, 1, 100),
                 LayoutLine("Ben waits.", 108, 1, 124),
                 LayoutLine("12A  EXT. HOUSE - DAY  12A", 54, 1, 160),
                 LayoutLine("Rain.", 108, 1, 184),
                 LayoutLine("INT. CAR - NIGHT", 108, 1, 220),
                 LayoutLine("Ben drives.", 108, 1, 244)]
        scenes = parse_layout_lines(lines)
        assert [(s.scene_number, s.scene_number_source, s.slugline) for s in scenes] == [
            ("12", "script", "INT. HOUSE - DAY"),
            ("12A", "script", "EXT. HOUSE - DAY"),
            ("3", "auto", "INT. CAR - NIGHT"),
        ]

    def test_unnumbered_pdf_still_counts(self):
        from pdf_import import parse_layout_lines
        lines = [LayoutLine("INT. A - DAY", 108, 1, 100), LayoutLine("One.", 108, 1, 124),
                 LayoutLine("EXT. B - NIGHT", 108, 1, 160), LayoutLine("Two.", 108, 1, 184)]
        assert [(s.scene_number, s.scene_number_source)
                for s in parse_layout_lines(lines)] == [("1", "auto"), ("2", "auto")]
