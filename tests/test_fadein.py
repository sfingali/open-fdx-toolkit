"""Tests for the Fade In (.fadein / OSF) parser and builder."""

import io
import os
import zipfile
import xml.etree.ElementTree as ET

import pytest

from fadein_builder import build_fadein
from fadein_parser import parse_fadein_bytes
from fdx_parser import ParsedParagraph, ParsedScene, parse_file

SAMPLE_FADEIN = "/opt/data/home/projects/rsdoiel-fdx/testdata/sample-01.fadein"
SAMPLE_FDX = "/opt/data/home/projects/the-sample/drafts/the sample script - 03-18-26b - FINGLETON.fdx"


def _scene(number, slugline, paragraphs):
    return ParsedScene(
        scene_number=number,
        scene_number_source="script",
        slugline=slugline,
        paragraphs=paragraphs,
    )


class TestParseFadeIn:
    def test_parse_real_sample_01(self):
        if not os.path.exists(SAMPLE_FADEIN):
            pytest.skip("sample-01.fadein not available")
        with open(SAMPLE_FADEIN, "rb") as f:
            scenes = parse_fadein_bytes(f.read())

        assert len(scenes) == 1
        scene = scenes[0]
        assert scene.slugline == "EXT. LIBRARY - DAY"
        assert scene.scene_number == "1"
        assert scene.scene_number_source == "auto"

        types = [p.type for p in scene.paragraphs]
        assert types == ["Action", "Character", "Parenthetical", "Dialogue", "Transition"]
        assert scene.paragraphs[2].text == "(excited)"
        assert scene.paragraphs[1].text == "PROGRAMMER"
        assert scene.paragraphs[4].text == "FADE TO BLACK."

    def test_parse_rejects_empty_bytes(self):
        assert parse_fadein_bytes(b"") == []


class TestBuildFadeIn:
    def test_zip_contains_single_document_xml(self):
        data = build_fadein([_scene("1", "INT. ROOM - DAY", [])])
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            assert zf.namelist() == ["document.xml"]
            root = ET.fromstring(zf.read("document.xml"))

        assert root.get("type") == "Open Screenplay Format document"
        assert root.get("version") == "30"

        settings = root.find("settings")
        assert settings is not None
        assert settings.get("page_width")
        assert settings.get("page_height")

        styles = root.find("styles")
        assert styles is not None
        style_names = {s.get("name") for s in styles.findall("style")}
        assert {
            "Scene Heading",
            "Action",
            "Character",
            "Parenthetical",
            "Dialogue",
            "Transition",
        } <= style_names

    def test_scene_number_written_as_trailing_hash(self):
        data = build_fadein([_scene("12", "INT. KITCHEN - DAY", [])])
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root = ET.fromstring(zf.read("document.xml"))

        heading = root.find("paragraphs")[0]
        assert heading.find("style").get("basestylename") == "Scene Heading"
        assert heading.find("text").text == "INT. KITCHEN - DAY #12#"

        reparsed = parse_fadein_bytes(data)
        assert reparsed[0].scene_number == "12"
        assert reparsed[0].scene_number_source == "script"
        assert reparsed[0].slugline == "INT. KITCHEN - DAY"

    def test_title_page_bookmarks(self):
        data = build_fadein(
            [_scene("1", "INT. ROOM - DAY", [])],
            title_page={"title": "the sample script", "author": "Jane Doe"},
        )
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root = ET.fromstring(zf.read("document.xml"))

        titlepage = root.find("titlepage")
        assert titlepage is not None
        paras = titlepage.findall("para")
        title_para = next(p for p in paras if p.get("bookmark") == "Title")
        author_para = next(p for p in paras if p.get("bookmark") == "Author")
        assert title_para.find("text").text == "the sample script"
        assert author_para.find("text").text == "Jane Doe"
        assert title_para.find("style").get("align") == "center"
        assert author_para.find("style").get("align") == "center"


class TestRoundTrip:
    def test_synthetic_three_scene_script(self):
        scenes = [
            _scene(
                "1",
                "INT. KITCHEN - HOUSE - DAY",
                [
                    ParsedParagraph("Action", "A man cooks."),
                    ParsedParagraph("Character", "BEN"),
                    ParsedParagraph("Parenthetical", "(angry)"),
                    ParsedParagraph("Dialogue", "No."),
                    ParsedParagraph("Transition", "CUT TO:"),
                ],
            ),
            _scene(
                "2",
                "EXT. STREET - NIGHT",
                [
                    ParsedParagraph("Action", "Rain falls."),
                    ParsedParagraph("Center", "THE END"),
                ],
            ),
            _scene(
                "3",
                "INT. GARAGE - DAY",
                [
                    ParsedParagraph("Character", "ANNA"),
                    ParsedParagraph("Parenthetical", "(quiet)"),
                    ParsedParagraph("Dialogue", "It's late."),
                ],
            ),
        ]

        rebuilt = parse_fadein_bytes(build_fadein(scenes))

        assert len(rebuilt) == 3
        for original, parsed in zip(scenes, rebuilt):
            assert parsed.scene_number == original.scene_number
            assert parsed.slugline == original.slugline
            assert [(p.type, p.text) for p in parsed.paragraphs] == [
                (p.type, p.text) for p in original.paragraphs
            ]

    def test_parenthetical_uses_fade_in_text_convention(self):
        scenes = [
            _scene(
                "1",
                "INT. ROOM - DAY",
                [
                    ParsedParagraph("Character", "BEN"),
                    ParsedParagraph("Parenthetical", "(a beat too long)"),
                    ParsedParagraph("Dialogue", "Maybe not today."),
                ],
            )
        ]
        data = build_fadein(scenes)

        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            root = ET.fromstring(zf.read("document.xml"))
        paras = root.find("paragraphs").findall("para")
        parenthetical = next(
            p for p in paras
            if p.find("style").get("basestylename") == "Parenthetical"
        )
        assert parenthetical.find("text").text == "a beat too long"

        rebuilt = parse_fadein_bytes(data)
        assert rebuilt[0].paragraphs[1].text == "(a beat too long)"

    def test_sample_fdx_to_fadein_roundtrip(self):
        if not os.path.exists(SAMPLE_FDX):
            pytest.skip("the sample script FDX draft not available")

        fdx_scenes = parse_file(SAMPLE_FDX)
        assert len(fdx_scenes) == 278

        rebuilt = parse_fadein_bytes(build_fadein(fdx_scenes))

        assert len(rebuilt) == 278
        assert [s.scene_number for s in rebuilt] == [s.scene_number for s in fdx_scenes]
        assert [s.slugline for s in rebuilt] == [s.slugline for s in fdx_scenes]

        # All structured body paragraphs survive the FDX -> Fade In -> parser
        # round-trip as the same type and text.
        for fdx_scene, fade_scene in zip(fdx_scenes, rebuilt):
            assert [(p.type, p.text) for p in fade_scene.paragraphs] == [
                (p.type, p.text) for p in fdx_scene.paragraphs
            ]
