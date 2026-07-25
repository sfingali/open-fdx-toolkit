"""Tests for open-fdx-parser."""

from fdx_parser import parse_fdx, _parse_slugline, _detect_narrative


class TestSluglineParsing:
    def test_standard_int(self):
        r = _parse_slugline("INT. KITCHEN - HOUSE - DAY")
        assert r["interior_exterior"] == "INT"
        assert r["location"] == "KITCHEN"
        assert r["set_name"] == "HOUSE"
        assert r["time_of_day"] == "DAY"

    def test_ext_no_period(self):
        r = _parse_slugline("EXT STREET - DAY")
        assert r["interior_exterior"] == "EXT"
        assert r["location"] == "STREET"
        assert r["time_of_day"] == "DAY"

    def test_int_ext_combined(self):
        r = _parse_slugline("INT./EXT. CAR - DAY")
        assert r["interior_exterior"] == "INT/EXT"

    def test_no_time_of_day(self):
        r = _parse_slugline("INT. HALLWAY")
        assert r["interior_exterior"] == "INT"
        assert r["location"] == "HALLWAY"
        assert r["time_of_day"] == ""


class TestNarrativeDetection:
    def test_flashback(self):
        assert _detect_narrative("INT. CLASSROOM (FLASHBACK) - DAY") == "flashback"

    def test_flash_forward(self):
        assert _detect_narrative("EXT. CITY (FLASH FORWARD) - NIGHT") == "flashforward"

    def test_dream(self):
        assert _detect_narrative("INT. BEDROOM (DREAM) - NIGHT") == "dream"

    def test_memory(self):
        assert _detect_narrative("INT. HOUSE (MEMORY) - DAY") == "memory"

    def test_no_narrative(self):
        assert _detect_narrative("INT. OFFICE - DAY") is None


class TestParseFdx:
    def test_empty(self):
        scenes = parse_fdx('<?xml version="1.0"?><FinalDraft></FinalDraft>')
        assert scenes == []

    def test_single_scene(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="2/8" Page="1" Number="1"/>
      <Text>INT. KITCHEN - HOUSE - DAY</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        assert len(scenes) == 1
        assert scenes[0].slugline == "INT. KITCHEN - HOUSE - DAY"
        assert scenes[0].interior_exterior == "INT"
        assert scenes[0].location == "KITCHEN"
        assert scenes[0].scene_number == "1"
        assert scenes[0].page_eighths == 2

    def test_scene_with_character_and_dialogue(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="1/8" Page="1"/>
      <Text>EXT. STREET - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action"><Text>A man walks.</Text></Paragraph>
    <Paragraph Type="Character"><Text>BEN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Hello.</Text></Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        assert len(scenes) == 1
        assert "BEN" in scenes[0].characters
        assert "Hello." in scenes[0].body_lines

    def test_multiple_scenes(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="1/8" Page="1"/>
      <Text>INT. ROOM - DAY</Text>
    </Paragraph>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="2/8" Page="1"/>
      <Text>EXT. STREET - NIGHT</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        assert len(scenes) == 2
        assert scenes[0].slugline == "INT. ROOM - DAY"
        assert scenes[1].slugline == "EXT. STREET - NIGHT"

    def test_flashback_detection(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="1/8" Page="1"/>
      <Text>INT. CLASSROOM (FLASHBACK) - DAY</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        assert scenes[0].narrative_position_hint == "flashback"

    def test_auto_numbering(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="1/8" Page="1"/>
      <Text>INT. ROOM - DAY</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        assert scenes[0].scene_number_source == "auto"
        assert scenes[0].scene_number == "1"

    def test_to_dict(self):
        fdx = """<?xml version="1.0"?>
<FinalDraft>
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="2/8" Page="1" Number="42"/>
      <Text>INT. BAR - NIGHT</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(fdx)
        d = scenes[0].to_dict()
        assert d["scene_number"] == "42"
        assert d["location"] == "BAR"
        assert d["time_of_day"] == "NIGHT"

class TestFixtureFiles:
    def test_parse_sample_01(self):
        from fdx_parser import parse_fdx
        import os
        path = os.path.join(os.path.dirname(__file__), "fixtures", "sample-01.fdx")
        with open(path) as f:
            scenes = parse_fdx(f.read())
        assert len(scenes) > 0
        # Verify core paragraph types
        all_types = set()
        for s in scenes:
            for p in s.paragraphs:
                all_types.add(p.type)
        assert "Scene Heading" in all_types
        assert "Character" in all_types
        assert "Dialogue" in all_types
        assert "Action" in all_types

    def test_parse_sample_02(self):
        from fdx_parser import parse_fdx
        import os
        path = os.path.join(os.path.dirname(__file__), "fixtures", "sample-02.fdx")
        with open(path) as f:
            scenes = parse_fdx(f.read())
        assert len(scenes) > 0

    def test_parse_sample_03(self):
        from fdx_parser import parse_fdx
        import os
        path = os.path.join(os.path.dirname(__file__), "fixtures", "sample-03.fdx")
        with open(path) as f:
            scenes = parse_fdx(f.read())
        assert len(scenes) > 0

    def test_all_samples_parse_without_error(self):
        from fdx_parser import parse_fdx
        import os
        fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        count = 0
        for fname in sorted(os.listdir(fixtures_dir)):
            if fname.endswith('.fdx'):
                with open(os.path.join(fixtures_dir, fname)) as f:
                    scenes = parse_fdx(f.read())
                assert len(scenes) > 0, f"{fname} produced no scenes"
                count += 1
        assert count == 3, f"Expected 3 fixtures, got {count}"
