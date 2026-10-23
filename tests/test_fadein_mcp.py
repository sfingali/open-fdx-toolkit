"""Tests for fadein_mcp.core — the OSF read path and surgical text edits."""

from __future__ import annotations

import io
import zipfile

import pytest

from fadein_builder import build_fadein
from fdx_parser import ParsedParagraph, ParsedScene
from fadein_mcp import core


def _scene(number: str, slugline: str, body: list[tuple[str, str]]) -> ParsedScene:
    return ParsedScene(
        scene_number=number,
        slugline=slugline,
        paragraphs=[ParsedParagraph(type=t, text=x) for t, x in body],
    )


def _sample() -> list[ParsedScene]:
    return [
        _scene(
            "1",
            "INT. KITCHEN - NIGHT",
            [
                ("Action", "Ben fills the kettle."),
                ("Character", "BEN"),
                ("Dialogue", "Where is she?"),
            ],
        ),
        _scene(
            "2",
            "EXT. LANE - DAY",
            [
                ("Action", "Ben walks the lane past the bat."),
                ("Character", "MARIE (O.S.)"),
                ("Dialogue", "Ben, wait."),
                ("Action", "He does not turn."),
            ],
        ),
    ]


def _write(tmp_path, scenes, name="draft.fadein", extra_asset: bytes | None = None,
           pagecount: str | None = None):
    data = build_fadein(scenes)
    buf = io.BytesIO(data)
    with zipfile.ZipFile(buf) as zin:
        entries = [(i, zin.read(i.filename)) for i in zin.infolist()]
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zout:
        for info, payload in entries:
            if info.filename == "document.xml" and pagecount:
                payload = payload.decode("utf-8").replace(
                    'pagecount="1"', f'pagecount="{pagecount}"', 1
                ).encode("utf-8")
            zout.writestr(info, payload)
        if extra_asset is not None:
            zout.writestr("embedded-asset", extra_asset)
    path = tmp_path / name
    path.write_bytes(out.getvalue())
    return path


class TestRead:
    def test_script_info_reports_document_pagecount(self, tmp_path):
        path = _write(tmp_path, _sample(), pagecount="42")
        info = core.script_info(path)
        assert info["pages"] == 42
        assert info["scenes"] == 2
        assert info["format"].startswith("Open Screenplay")
        assert info["characters_in_script"] == 2

    def test_list_scenes_and_selector(self, tmp_path):
        path = _write(tmp_path, _sample())
        rows = core.list_scenes(path)
        assert [r["n"] for r in rows["scenes"]] == ["1", "2"]
        assert core.list_scenes(path, contains="kettle")["matched"] == 1
        got = core.get_scene(path, "2")
        assert "Ben, wait." in got["scenes"][0]["text"]
        assert [s["n"] for s in core.get_scene(path, "1-2")["scenes"]] == ["1", "2"]

    def test_search_returns_scene_and_element(self, tmp_path):
        path = _write(tmp_path, _sample())
        hits = core.search(path, "lane")["hits"]
        assert hits and hits[0]["scene"] == "2"
        assert core.search(path, "wait", regex=False)["hits"]

    def test_character_report_normalises_cues(self, tmp_path):
        path = _write(tmp_path, _sample())
        rows = core.character_report(path)["characters"]
        names = {r["character"] for r in rows}
        assert "marie" in names
        assert all("(" not in n for n in names)

    def test_location_report_groups(self, tmp_path):
        path = _write(tmp_path, _sample())
        locs = core.location_report(path)["locations"]
        assert {l["location"] for l in locs} == {"kitchen", "lane"}


class TestCompare:
    def test_compare_reports_page_and_word_deltas(self, tmp_path):
        a = _write(tmp_path, _sample(), name="a.fadein", pagecount="10")
        edited = _sample()
        edited[1].paragraphs.append(ParsedParagraph(type="Action", text="The lane is empty."))
        b = _write(tmp_path, edited, name="b.fadein", pagecount="12")
        diff = core.compare_drafts(a, b)
        assert diff["page_delta"] == 2
        assert diff["scene_delta"] == 0
        assert diff["word_delta"] == 4
        assert diff["changed_count"] == 1
        assert diff["scenes_changed"][0]["scene"] == "2"


class TestReplace:
    def test_replace_writes_copy_and_preserves_assets(self, tmp_path):
        asset = b"\x89PNG\r\n\x1a\n" + b"asset-bytes" * 50
        src = _write(tmp_path, _sample(), extra_asset=asset, pagecount="7")
        out = tmp_path / "edited.fadein"
        res = core.replace_text(src, "kettle", "saucepan", out_path=out)
        assert res["replacements"] == 1
        assert res["checks"]["scenes_preserved"]
        assert res["checks"]["pagecount_preserved"]
        assert core.get_scene(out, "1")["scenes"][0]["text"].count("saucepan") == 1

        with zipfile.ZipFile(src) as a, zipfile.ZipFile(out) as b:
            assert a.read("embedded-asset") == b.read("embedded-asset") == asset
            assert a.namelist() == b.namelist()

    def test_replace_refuses_to_overwrite_source(self, tmp_path):
        src = _write(tmp_path, _sample())
        with pytest.raises(ValueError):
            core.replace_text(src, "kettle", "saucepan", out_path=src)

    def test_replace_dry_run_writes_nothing(self, tmp_path):
        src = _write(tmp_path, _sample())
        before = src.read_bytes()
        res = core.replace_text(src, "kettle", "saucepan", dry_run=True)
        assert res["replacements"] == 1
        assert src.read_bytes() == before
        assert not (tmp_path / "draft (edited).fadein").exists()

    def test_scene_scope_limits_edits(self, tmp_path):
        scenes = _sample()
        scenes[1].paragraphs.append(ParsedParagraph(type="Action", text="Ben fills the kettle."))
        src = _write(tmp_path, scenes)
        out = tmp_path / "scoped.fadein"
        res = core.replace_text(src, "kettle", "saucepan", scene="1", out_path=out)
        assert res["replacements"] == 1
        text = core.get_scene(out, "1")["scenes"][0]["text"] + core.get_scene(out, "2")["scenes"][0]["text"]
        assert text.count("saucepan") == 1
        assert "Ben fills the kettle." in text

    def test_no_match_leaves_file_alone(self, tmp_path):
        src = _write(tmp_path, _sample())
        before = src.read_bytes()
        res = core.replace_text(src, "not in script", "x")
        assert res["replacements"] == 0
        assert src.read_bytes() == before
