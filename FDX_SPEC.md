# Final Draft XML (.fdx) Format Specification

Complete reference for the Final Draft XML format. This document enables
any agent or developer to parse, generate, validate, and manipulate FDX
files with confidence.

## Document Structure

```xml
<?xml version="1.0" encoding="UTF-8"?>
<FinalDraft DocumentType="Script" Template="No" Version="2">
  <Content>
    <!-- Paragraphs go here -->
  </Content>
</FinalDraft>
```

### Root Element `<FinalDraft>`

| Attribute | Values | Description |
|-----------|--------|-------------|
| `DocumentType` | `"Script"` | Always "Script" for screenplays |
| `Template` | `"No"`, `"Yes"` | Whether this file is a template |
| `Version` | `"2"` | FDX format version (v2 is current) |

### Script Metadata (optional, contained in `<Content>`)

```xml
<Paragraph Type="General">
  <Text>Title: MY SCREENPLAY</Text>
</Paragraph>
```

Title page content and script notes appear as `Paragraph Type="General"` elements
typically at the start of `<Content>`.

## Paragraph Types

Every paragraph in an FDX file is a `<Paragraph>` element with a `Type` attribute.
The type determines how Final Draft renders the text.

### Complete Type List

| Type | Rendering | Contains |
|------|-----------|----------|
| `Scene Heading` | ALL CAPS, numbered | Scene heading text, SceneProperties |
| `Action` | Mixed case, full width | Action/description text |
| `Character` | ALL CAPS, left margin | Character name cue |
| `Dialogue` | Mixed case, narrow | Spoken dialogue |
| `Parenthetical` | (parentheses), centered | Actor direction within dialogue |
| `Transition` | ALL CAPS, right-aligned | "CUT TO:", "FADE OUT." |
| `Shot` | ALL CAPS | "CLOSE ON", "ANGLE ON" |
| `General` | Mixed case, full width | Title page, notes, revision marks |

### Paragraph Children

Each `<Paragraph>` contains one or more `<Text>` elements. Multiple `<Text>`
children appear when Final Draft stores revision-mode editing (character-by-
character changes). For parsing, join all `<Text>` children by their text content.

```xml
<Paragraph Type="Action">
  <Text Style="Underline">ON BEN</Text>
</Paragraph>
```

The optional `Style` attribute on `<Text>` can be:
- `"Underline"` — underlined text
- `"Bold"` — bold text
- `"Italic"` — italic text

## Scene Headings

Scene headings are `Paragraph Type="Scene Heading"` and always contain a
`<SceneProperties>` child.

```xml
<Paragraph Type="Scene Heading">
  <SceneProperties Length="2/8" Page="1" Title="" Number="1"/>
  <Text>INT. MASTER BEDROOM - HOUSE - NIGHT</Text>
</Paragraph>
```

### SceneProperties

| Attribute | Type | Example | Description |
|-----------|------|---------|-------------|
| `Length` | string | `"2/8"` | Scene page count in eighths (1/8 to 8/8) |
| `Page` | string | `"1"` | Starting page number |
| `Title` | string | `""` | Optional scene title (rarely used) |
| `Number` | string | `"1"`, `"12A"`, `""` | Scene number. Empty = auto-numbered |

### Scene Heading Text Format

Scene headings follow a standard pattern:

```
INT./EXT. LOCATION - SET - TIME OF DAY
```

Components:
1. **Interior/Exterior**: `INT.`, `EXT.`, `INT./EXT.` (trailing period optional)
2. **Location**: Primary location (required)
3. **Set**: Sub-location after first ` - ` (optional)
4. **Time of Day**: After final ` - ` (DAY, NIGHT, DAWN, DUSK, CONTINUOUS, LATER, etc.)

Variations:
- `EXT. STREET - DAY` (no set)
- `INT. KITCHEN - HOUSE - NIGHT` (location + set)
- `INT./EXT. CAR - DAY` (combined interior/exterior)

### Narrative Markers

Parenthetical markers in scene headings indicate non-linear narrative:

```
(FLASHBACK)     — Scene takes place in the past
(FLASH FORWARD) — Scene takes place in the future
(DREAM)         — Dream sequence
(MEMORY)        — Memory sequence
```

Example: `INT. CLASSROOM (FLASHBACK) - DAY`

These should be parsed separately from the time-of-day indicator and can influence
story threading.

## Page Lengths (Eighths)

Final Draft measures scene length in eighths of a page:

| Length | Pages |
|--------|-------|
| `1/8` | ~0.125 pages (very short) |
| `2/8` | ~0.25 pages |
| `4/8` | ~0.5 pages |
| `8/8` | ~1 page |

The `SceneProperties Length` attribute stores this value. A scene longer than
1 page will have `8/8` in the XML (Final Draft truncates at one page per scene
in the FDX export).

## Character Cues and Dialogue

```xml
<Paragraph Type="Character">
  <Text>BEN</Text>
</Paragraph>
<Paragraph Type="Parenthetical">
  <Text>(whispering)</Text>
</Paragraph>
<Paragraph Type="Dialogue">
  <Text>I can't believe it.</Text>
</Paragraph>
```

Parentheticals are optional and appear between Character and Dialogue paragraphs.

## Dual Dialogue

Dual dialogue (two characters speaking simultaneously) uses a `^` character
suffix on the Character paragraph:

```
BEN^
    Hello.
MARIE^
    What is it?
```

In FDX XML, the `^` is part of the Character paragraph text and the following
Dialogue paragraph is the character's line. Final Draft handles the exact
layout — parsers should detect the `^` suffix and flag `has_dual_dialogue = True`.

## Complete XML Schema

For reference, the full valid structure:

```
FinalDraft [DocumentType, Template, Version]
  └── Content
       ├── Paragraph [Type="General"]              (title page, notes)
       │    └── Text [Style?]
       ├── Paragraph [Type="Scene Heading"]
       │    ├── SceneProperties [Length, Page, Title, Number]
       │    └── Text
       ├── Paragraph [Type="Action"]
       │    └── Text [Style?]
       ├── Paragraph [Type="Character"]
       │    └── Text
       ├── Paragraph [Type="Parenthetical"]
       │    └── Text
       ├── Paragraph [Type="Dialogue"]
       │    └── Text [Style?]
       ├── Paragraph [Type="Transition"]
       │    └── Text
       ├── Paragraph [Type="Shot"]
       │    └── Text
       └── Paragraph [Type="General"]
            └── Text
```

## Validation Rules

A well-formed FDX file:

1. Has exactly one `<Content>` child inside `<FinalDraft>`
2. All `<SceneHeading>` paragraphs have a `<SceneProperties>` child
3. Character paragraphs are followed by zero or one Parenthetical, then one Dialogue
4. Scene heading text contains at minimum a location
5. Page lengths are in the format `N/8` where N is 1-8
6. XML is valid UTF-8

## Known Limitations

- **Split `<Text>` nodes**: Final Draft may split a paragraph's text across
  multiple `<Text>` elements for revision tracking. Always join all `<Text>`
  children.
- **Long scenes**: FDX caps SceneProperties Length at `8/8`. Scenes longer
  than one page all report `8/8`.
- **No embedded media**: FDX does not contain images, audio, or video.
- **No script notes content**: The FDX format doesn't include Final Draft's
  Script Notes feature in a parseable way.
- **Revision marks**: FDX may contain revision-mode artifacts (colored text
  spans, `Change="Added"` attributes) that are safe to ignore for basic parsing.

## See Also

- [Final Draft](https://www.finaldraft.com/)
- [Fountain](https://fountain.io/) — plain-text screenplay format
- [Open Screenplay Format](https://github.com/OpenScreenplayFormat) — related standardization efforts
