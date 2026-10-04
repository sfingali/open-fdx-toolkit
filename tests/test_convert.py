"""Cross-format conversion tests: every format -> every other format.

Uses the sample script ground-truth files when available; otherwise falls back to a
small synthetic script so the suite runs anywhere.
"""

import io
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fdx_builder import FDXDocument, scene_from_parsed
from fdx_parser import parse_file, parse_fdx
from fadein_builder import build_fadein
from fadein_parser import parse_fadein_bytes
from fountain_builder import build_fountain
from fountain_parser import parse_fountain
from txt_import import parse_plain_text

SAMPLE_FDX = os.environ.get("SAMPLE_FDX", "")
SAMPLE_PDF = os.environ.get("SAMPLE_PDF", "")

SYNTHETIC = """INT. KITCHEN - DAY

A man cooks.

BEN
Morning. Coffee?

MARIE
Please.

He pours. Steam rises.

CUT TO:

EXT. STREET - NIGHT

Rain. Ben walks.

MARIE (O.S.)
Don't forget the milk.

FADE OUT.
"""


def _synthetic_scenes():
    return parse_fountain(SYNTHETIC)


def _sluglines(scenes):
    return [s.slugline for s in scenes]


def _chars(scenes):
    return sorted({c for s in scenes for c in s.characters})


class TestSyntheticRoundTrips:
    """Every pairwise conversion on the small synthetic script."""

    def test_fountain_to_fdx_to_fountain(self):
        scenes = _synthetic_scenes()
        doc = FDXDocument()
        for s in scenes:
            doc.add_scene(scene_from_parsed(s))
        back = parse_fdx(doc.to_xml())
        assert _sluglines(back) == _sluglines(scenes)
        assert _chars(back) == _chars(scenes)

    def test_fountain_to_fadein_to_fountain(self):
        scenes = _synthetic_scenes()
        data = build_fadein(scenes)
        back = parse_fadein_bytes(data)
        assert _sluglines(back) == _sluglines(scenes)
        assert _chars(back) == _chars(scenes)

    def test_fountain_to_fountain_text_roundtrip(self):
        scenes = _synthetic_scenes()
        text = build_fountain(scenes, title="SYNTHETIC")
        back = parse_fountain(text)
        assert _sluglines(back) == _sluglines(scenes)
        assert _chars(back) == _chars(scenes)

    def test_txt_import_detects_structure(self):
        scenes = parse_plain_text(SYNTHETIC)
        assert _sluglines(scenes) == [
            "INT. KITCHEN - DAY",
            "EXT. STREET - NIGHT",
        ]
        assert "BEN" in _chars(scenes)
        assert "MARIE" in _chars(scenes)

    def test_fdx_write_read(self):
        scenes = _synthetic_scenes()
        doc = FDXDocument()
        for s in scenes:
            doc.add_scene(scene_from_parsed(s))
        xml = doc.to_xml()
        assert "<FinalDraft" in xml
        assert "INT. KITCHEN - DAY" in xml


class TestSampleCrossFormat:
    """the sample script ground truth: FDX -> every other format -> compare."""

    def test_fdx_to_fountain_scene_count(self):
        if not os.path.exists(SAMPLE_FDX):
            pytest.skip("the sample script FDX not available")
        scenes = parse_file(SAMPLE_FDX)
        text = build_fountain(scenes, title="the sample script")
        back = parse_fountain(text)
        assert len(back) == len(scenes) == 278
        assert _sluglines(back) == _sluglines(scenes)

    def test_fdx_to_fadein_roundtrip(self):
        if not os.path.exists(SAMPLE_FDX):
            pytest.skip("the sample script FDX not available")
        scenes = parse_file(SAMPLE_FDX)
        data = build_fadein(scenes)
        back = parse_fadein_bytes(data)
        assert len(back) == 278
        assert _sluglines(back) == _sluglines(scenes)
        assert _chars(back) == _chars(scenes)

    def test_pdf_import_to_fountain_reparse(self):
        """The user-facing chain: PDF -> Fountain (via ParsedScene)."""
        if not os.path.exists(SAMPLE_PDF):
            pytest.skip("the sample script PDF not available")
        pytest.importorskip("pymupdf")
        from pdf_import import parse_pdf

        scenes = parse_pdf(SAMPLE_PDF)
        assert len(scenes) == 279  # 03-17-26 draft
        text = build_fountain(scenes, title="the sample script")
        back = parse_fountain(text)
        # Scene count preserved through PDF -> fountain -> reparse
        assert len(back) == 279
        assert _sluglines(back)[:5] == _sluglines(scenes)[:5]
