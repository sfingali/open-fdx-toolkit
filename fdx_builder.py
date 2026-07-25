"""FDX builder — generate Final Draft XML from structured Python data.

Zero-dependency. Creates valid FDX XML suitable for import into Final Draft 8+,
Fade In, and other screenwriting applications that support the format.

Usage:
    from fdx_builder import FDXDocument, Scene, Paragraph

    doc = FDXDocument()
    doc.add_scene(Scene(
        heading="INT. KITCHEN - DAY",
        number="1",
        paragraphs=[Paragraph("Action", "A man cooks.")],
    ))
    xml = doc.to_xml()
"""

from __future__ import annotations

import xml.dom.minidom
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

__all__ = ["FDXDocument", "Scene", "Paragraph", "SceneProperties"]


@dataclass
class SceneProperties:
    """Scene-level metadata in FDX format."""

    length: str = "1/8"  # Page length in eighths: "2/8", "6/8"
    page: str = "1"       # Starting page number
    title: str = ""       # Optional scene title
    number: str = ""      # Scene number (empty = auto)


@dataclass
class Paragraph:
    """A single paragraph within a scene."""

    type: str  # "Scene Heading", "Action", "Character", "Dialogue", etc.
    text: str
    style: str = ""  # Optional: "Underline", "Bold", etc.

    def to_element(self) -> ET.Element:
        el = ET.Element("Paragraph", Type=self.type)
        if self.style:
            el.append(ET.Element("Text", Style=self.style))
            el[-1].text = self.text
        else:
            ET.SubElement(el, "Text").text = self.text
        return el


@dataclass
class Scene:
    """A single scene: heading, optional paragraphs, and properties."""

    heading: str
    number: str = ""
    paragraphs: list[Paragraph] = field(default_factory=list)
    properties: SceneProperties | None = None

    def to_element(self) -> ET.Element:
        el = ET.Element("Paragraph", Type="Scene Heading")
        sp = self.properties or SceneProperties(number=self.number)
        ET.SubElement(el, "SceneProperties",
            Length=sp.length, Page=sp.page, Title=sp.title,
            Number=sp.number,
        )
        ET.SubElement(el, "Text").text = self.heading
        return el


@dataclass
class FDXDocument:
    """Represents a complete FDX document.

    Build scenes, add paragraphs, and export to well-formed XML string.
    """

    scenes: list[Scene] = field(default_factory=list)
    document_type: str = "Script"
    template: str = "No"
    version: str = "2"
    title: str = ""

    def add_scene(self, scene: Scene) -> None:
        self.scenes.append(scene)

    def add_paragraph(self, scene_index: int, para: Paragraph) -> None:
        if 0 <= scene_index < len(self.scenes):
            self.scenes[scene_index].paragraphs.append(para)

    def to_element_tree(self) -> ET.Element:
        root = ET.Element("FinalDraft",
            DocumentType=self.document_type,
            Template=self.template,
            Version=self.version,
        )
        content = ET.SubElement(root, "Content")

        for scene in self.scenes:
            content.append(scene.to_element())
            for para in scene.paragraphs:
                content.append(para.to_element())

        return root

    def to_xml(self, pretty: bool = True, declaration: bool = True) -> str:
        """Generate FDX XML string.

        Args:
            pretty: If True, pretty-print with indentation.
            declaration: If True, include XML declaration.

        Returns:
            Formatted FDX XML string.
        """
        raw = ET.tostring(self.to_element_tree(), encoding="unicode")
        if pretty:
            dom = xml.dom.minidom.parseString(raw)
            result = dom.toprettyxml(indent="  ")
            if not declaration:
                result = result.split("\n", 1)[1] if "\n" in result else result
            return result
        return raw


def scene_from_parsed(parsed_scene, paragraphs: list[Paragraph] | None = None) -> Scene:
    """Convert a ParsedScene (from fdx_parser) into a builder Scene.

    Useful for parse-edit-export workflows.
    """
    sp = SceneProperties(
        length=f"{parsed_scene.page_eighths}/8",
        number=parsed_scene.scene_number,
    )
    return Scene(
        heading=parsed_scene.slugline,
        number=parsed_scene.scene_number,
        paragraphs=paragraphs or [
            Paragraph("Action", line)
            for line in parsed_scene.body_lines
        ],
        properties=sp,
    )
