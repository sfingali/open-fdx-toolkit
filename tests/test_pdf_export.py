"""Tests for the PDF screenplay exporter (pdf_export.py)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pdf_export import build_pdf, write_pdf, _wrap

SAMPLE_FDX = os.environ.get("SAMPLE_FDX", "")

pymupdf = pytest.importorskip("pymupdf")


class TestWrap:
    def test_simple_wrap(self):
        lines = _wrap("A short line", 360.0)
        assert lines == ["A short line"]

    def test_long_wrap(self):
        lines = _wrap("word " * 60, 360.0)  # 360pt / 7.2 = 50 chars
        assert all(len(l) <= 50 for l in lines)
        assert len(lines) > 1

    def test_empty(self):
        assert _wrap("", 100.0) == []


class TestBuildPdf:
    def test_roundtrip_text_extraction(self):
        from fdx_parser import parse_file
        from pdf_import import extract_layout_lines

        if not os.path.exists(SAMPLE_FDX):
            pytest.skip("the sample script FDX not available")
        scenes = parse_file(SAMPLE_FDX)
        data = build_pdf(scenes, title="the sample script")
        assert data[:4] == b"%PDF"

        # Write to temp file, extract text back, verify key sluglines survive
        tmp = "/tmp/_sample_export_test.pdf"
        write_pdf(tmp, scenes, title="the sample script")
        lines = extract_layout_lines(tmp)
        extracted = " ".join(l.text.upper() for l in lines)
        assert "INT. MASTER BEDROOM" in extracted
        assert "INT. KITCHEN" in extracted
        assert "EXT. SUBURBAN HOME" in extracted
        os.remove(tmp)

    def test_dialogue_and_characters_present(self):
        from fdx_parser import parse_file

        if not os.path.exists(SAMPLE_FDX):
            pytest.skip("the sample script FDX not available")
        scenes = parse_file(SAMPLE_FDX)
        # Every character name should appear in the rendered PDF
        tmp = "/tmp/_sample_chars_test.pdf"
        write_pdf(tmp, scenes)
        from pdf_import import extract_layout_lines

        lines = extract_layout_lines(tmp)
        extracted = " ".join(l.text.upper() for l in lines)
        chars = {c for s in scenes for c in s.characters}
        missing = [c for c in chars if c.upper() not in extracted]
        assert not missing, f"chars missing from PDF: {missing}"
        os.remove(tmp)
