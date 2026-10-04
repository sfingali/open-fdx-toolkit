"""Tests for the Fountain screenplay parser."""

import os

import pytest

from fountain_parser import parse_fountain

SAMPLE_FOUNTAIN_PATH = os.environ.get("SAMPLE_FOUNTAIN", "")


def test_title_page_key_value_blocks():
    scenes = parse_fountain(
        "Title: My Script\n"
        "Draft date: DRAFT (SF): 03-18-26\n"
        "Copyright: © KINOLIME 2026\n"
        "\n"
        "INT. ROOM - DAY #1#\n"
        "\n"
        "Action.\n"
    )
    assert len(scenes) == 1
    notes = scenes[0].script_notes
    assert [n.name for n in notes] == ["Title", "Draft date", "Copyright"]
    assert notes[0].text == "My Script"
    assert notes[1].text == "DRAFT (SF): 03-18-26"
    assert notes[2].text == "© KINOLIME 2026"


def test_scene_heading_with_scene_number_uses_fdx_slugline_parsing():
    scenes = parse_fountain(
        "INT. KITCHEN - HOUSE - NIGHT #42#\n"
        "\n"
        "Action.\n"
    )
    assert len(scenes) == 1
    scene = scenes[0]
    assert scene.scene_number == "42"
    assert scene.scene_number_source == "script"
    assert scene.slugline == "INT. KITCHEN - HOUSE - NIGHT"
    assert scene.interior_exterior == "INT"
    assert scene.location == "KITCHEN"
    assert scene.set_name == "HOUSE"
    assert scene.time_of_day == "NIGHT"


def test_unnumbered_scene_headings_auto_number():
    scenes = parse_fountain(
        "INT. ROOM - DAY\n"
        "\n"
        "Action one.\n"
        "\n"
        "EXT. STREET - NIGHT\n"
        "\n"
        "Action two.\n"
    )
    assert len(scenes) == 2
    assert [s.scene_number for s in scenes] == ["1", "2"]
    assert [s.scene_number_source for s in scenes] == ["auto", "auto"]
    assert scenes[1].slugline == "EXT. STREET - NIGHT"


def test_character_cues_extensions_dialogue_and_parentheticals():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "MARIE (O.S.)\n"
        "Get up and I'll make you coffee.\n"
        "\n"
        "BEN\n"
        "(a beat too long)\n"
        "Maybe not today.\n"
    )
    assert len(scenes) == 1
    scene = scenes[0]
    assert [p.type for p in scene.paragraphs] == [
        "Character",
        "Dialogue",
        "Character",
        "Parenthetical",
        "Dialogue",
    ]
    assert scene.paragraphs[0].text == "MARIE (O.S.)"
    assert scene.paragraphs[1].text == "Get up and I'll make you coffee."
    assert scene.paragraphs[3].text == "(a beat too long)"
    assert "MARIE (O.S.)" in scene.characters
    assert "BEN" in scene.characters


def test_transitions():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "CUT TO:\n"
        "\n"
        "Action after transition.\n"
    )
    assert len(scenes) == 1
    transitions = [p for p in scenes[0].paragraphs if p.type == "Transition"]
    assert len(transitions) == 1
    assert transitions[0].text == "CUT TO:"


def test_centered_line_with_underscores():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "_ON BEN_\n"
        "\n"
        "Action.\n"
    )
    paras = scenes[0].paragraphs
    assert paras[0].type == "Center"
    assert paras[0].text == "ON BEN"


def test_centered_line_with_angle_brackets():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        ">THE END<\n"
        "\n"
        "Action.\n"
    )
    paras = scenes[0].paragraphs
    assert paras[0].type == "Center"
    assert paras[0].text == "THE END"


def test_dual_dialogue_with_caret():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "BEN^\n"
        "I am Ben.\n"
        "\n"
        "JACK\n"
        "I am Jack.\n"
    )
    scene = scenes[0]
    assert scene.has_dual_dialogue is True
    assert len(scene.dual_dialogue_pairs) == 1
    pair = scene.dual_dialogue_pairs[0]
    assert pair.character_a == "BEN"
    assert pair.dialogue_a == "I am Ben."
    assert pair.character_b == "JACK"
    assert pair.dialogue_b == "I am Jack."
    # The caret is not part of the stored character name.
    assert any(p.type == "Character" and p.text == "BEN" for p in scene.paragraphs)


def test_notes_become_script_notes():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "[[A note for AI]]\n"
        "\n"
        "Action.\n"
    )
    scene = scenes[0]
    assert len(scene.script_notes) == 1
    assert scene.script_notes[0].name == ""
    assert scene.script_notes[0].text == "A note for AI"


def test_boneyard_comments_are_removed():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "Action before.\n"
        "\n"
        "/* hidden comment\n"
        "still hidden */\n"
        "\n"
        "Action after.\n"
    )
    action_texts = [p.text for p in scenes[0].paragraphs if p.type == "Action"]
    assert action_texts == ["Action before.", "Action after."]


def test_line_break_escape_with_two_spaces():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "The roof caves in.  \n"
        "A shockwave of blood.\n"
    )
    action = next(p for p in scenes[0].paragraphs if p.type == "Action")
    assert action.text == "The roof caves in.\nA shockwave of blood."


def test_line_break_escape_with_backslash():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "The roof caves in.\\\n"
        "A shockwave of blood.\n"
    )
    action = next(p for p in scenes[0].paragraphs if p.type == "Action")
    assert action.text == "The roof caves in.\nA shockwave of blood."


def test_page_break_paragraph():
    scenes = parse_fountain(
        "INT. ROOM - DAY #1#\n"
        "\n"
        "Action before.\n"
        "\n"
        "===\n"
        "\n"
        "Action after.\n"
    )
    paras = scenes[0].paragraphs
    page_breaks = [p for p in paras if p.type == "Page Break"]
    assert len(page_breaks) == 1
    assert page_breaks[0].text == "==="
    assert [p.text for p in paras if p.type == "Action"] == [
        "Action before.",
        "Action after.",
    ]


def test_sample_fountain_ground_truth():
    if not os.path.exists(SAMPLE_FOUNTAIN_PATH):
        pytest.skip("the sample script.fountain not available")
    with open(SAMPLE_FOUNTAIN_PATH, encoding="utf-8") as f:
        text = f.read()
    scenes = parse_fountain(text)

    # The canonical 03-18-26b fountain has 278 numbered scenes.  The FDX
    # ground-truth export in /opt/data/home/projects/the-sample/drafts has the
    # same count; the single un-numbered INT/EXT line in the fountain is an
    # action paragraph in the FDX and is therefore parsed as action here.
    assert len(scenes) == 278

    first = scenes[0]
    assert first.scene_number == "1"
    assert first.scene_number_source == "script"
    assert first.slugline == "INT. MASTER BEDROOM - HOUSE - NIGHT"
    assert first.interior_exterior == "INT"
    assert first.location == "MASTER BEDROOM"
    assert first.set_name == "HOUSE"
    assert first.time_of_day == "NIGHT"

    scene_3 = scenes[2]
    assert scene_3.scene_number == "3"
    assert scene_3.slugline == "INT. JACK'S BEDROOM - HOUSE - NIGHT"
    assert "BEN" in scene_3.characters
    assert "JACK" in scene_3.characters

    last = scenes[-1]
    assert last.scene_number == "278"
    assert last.scene_number_source == "script"
    assert last.slugline == "EXT. INTERSECTION - DAY"

    # Every scene has a populated scene number and slugline.
    assert all(s.scene_number for s in scenes)
    assert all(s.slugline for s in scenes)
    # The scene-numbered source file has no auto-numbered scenes.
    assert all(s.scene_number_source == "script" for s in scenes)

    # If the matching FDX export is available, the fountain parse must align
    # exactly with the FDX ground truth for scene count, numbers, and
    # sluglines.
    fdx_path = os.environ.get("SAMPLE_FDX", "")
    if os.path.exists(fdx_path):
        from fdx_parser import parse_file

        fdx_scenes = parse_file(fdx_path)
        assert len(scenes) == len(fdx_scenes)
        assert [s.scene_number for s in scenes] == [s.scene_number for s in fdx_scenes]
        assert [s.slugline for s in scenes] == [s.slugline for s in fdx_scenes]
