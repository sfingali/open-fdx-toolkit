"""Tests for FDX builder."""

from fdx_builder import FDXDocument, Scene, Paragraph, SceneProperties, scene_from_parsed
from fdx_parser import parse_fdx


class TestBuilder:
    def test_empty_document(self):
        doc = FDXDocument()
        xml = doc.to_xml()
        assert "FinalDraft" in xml
        assert "Content" in xml

    def test_single_scene(self):
        doc = FDXDocument()
        doc.add_scene(Scene(heading="INT. KITCHEN - DAY", number="1"))
        xml = doc.to_xml()
        assert 'INT. KITCHEN - DAY' in xml
        assert 'Number="1"' in xml

    def test_scene_with_action(self):
        doc = FDXDocument()
        doc.add_scene(Scene(
            heading="EXT. STREET - NIGHT",
            number="2",
            paragraphs=[Paragraph("Action", "A car passes.")],
        ))
        xml = doc.to_xml()
        assert "A car passes." in xml

    def test_scene_with_dialogue(self):
        doc = FDXDocument()
        doc.add_scene(Scene(
            heading="INT. BAR - NIGHT",
            paragraphs=[
                Paragraph("Character", "BEN"),
                Paragraph("Dialogue", "Hello."),
            ],
        ))
        xml = doc.to_xml()
        assert "BEN" in xml
        assert "Hello." in xml

    def test_multiple_scenes(self):
        doc = FDXDocument()
        doc.add_scene(Scene(heading="INT. ROOM - DAY"))
        doc.add_scene(Scene(heading="EXT. STREET - NIGHT"))
        xml = doc.to_xml()
        assert "INT. ROOM" in xml
        assert "EXT. STREET" in xml

    def test_scene_properties(self):
        doc = FDXDocument()
        doc.add_scene(Scene(
            heading="INT. HOUSE - DAY",
            properties=SceneProperties(length="4/8", page="3", number="12"),
        ))
        xml = doc.to_xml()
        assert 'Length="4/8"' in xml
        assert 'Page="3"' in xml
        assert 'Number="12"' in xml

    def test_no_declaration(self):
        doc = FDXDocument()
        doc.add_scene(Scene(heading="INT. ROOM - DAY"))
        xml = doc.to_xml(declaration=False)
        assert not xml.startswith("<?xml")

    def test_roundtrip_parse_build(self):
        """Parse FDX, convert to builder, generate XML, parse again."""
        original = """<?xml version="1.0"?>
<FinalDraft DocumentType="Script" Template="No" Version="2">
  <Content>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="2/8" Page="1" Number="1"/>
      <Text>INT. KITCHEN - DAY</Text>
    </Paragraph>
    <Paragraph Type="Action">
      <Text>A man cooks.</Text>
    </Paragraph>
    <Paragraph Type="Scene Heading">
      <SceneProperties Length="1/8" Page="1" Number="2"/>
      <Text>EXT. GARDEN - DAY</Text>
    </Paragraph>
  </Content>
</FinalDraft>"""
        scenes = parse_fdx(original)
        assert len(scenes) == 2

        doc = FDXDocument()
        for s in scenes:
            doc.add_scene(scene_from_parsed(s))
        rebuilt = doc.to_xml()

        reparsed = parse_fdx(rebuilt)
        assert len(reparsed) == 2
        assert reparsed[0].slugline == "INT. KITCHEN - DAY"

    def test_underline_style(self):
        doc = FDXDocument()
        doc.add_scene(Scene(
            heading="INT. ROOM - DAY",
            paragraphs=[Paragraph("Action", "ON BEN", style="Underline")],
        ))
        xml = doc.to_xml()
        assert 'Style="Underline"' in xml

    def test_parenthetical(self):
        doc = FDXDocument()
        doc.add_scene(Scene(
            heading="INT. OFFICE - DAY",
            paragraphs=[
                Paragraph("Character", "ANNA"),
                Paragraph("Parenthetical", "(angry)"),
                Paragraph("Dialogue", "No."),
            ],
        ))
        xml = doc.to_xml()
        assert "ANNA" in xml
        assert "(angry)" in xml
        assert "No." in xml
