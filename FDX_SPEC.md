# Final Draft XML (.fdx) Format Specification

**Status**: Verified against production FDX files, multiple open-source parsers, and
community documentation. Items marked **[PROVISIONAL]** or **[UNCONFIRMED]** have not
been directly observed in production files by this project's authors.

**Sources**:
- Production FDX file (278 scenes, THE-WAIF, Final Draft 11/12)
- `rsdoiel/fdx` Go package test data (GitHub)
- `stultus/scriptty` FDX import analysis (GitHub #190)
- `Guernsey-Creative/screenplay-js` FDX parser (GitHub)
- XPath queries gist by surrealroad (GitHub gist)
- StackOverflow XSL transform for FDX → HTML
- `jzucker2/schoonmaker` Python FDX tool (GitHub)

> **Note**: Final Draft does not publish a public XML schema or DTD for the FDX
> format. All knowledge here is reverse-engineered from files produced by Final Draft
> 8+, Fade In, Trelby, Amazon Storywriter, and Celtx. Different applications may
> produce subtly different FDX output.

---

## 1. Document Structure

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<FinalDraft DocumentType="Script" Template="No" Version="2">
  <!-- Preamble: metadata, title page, scene numbering config, revisions -->
  <TitlePage>...</TitlePage>
  <HeaderAndFooter>...</HeaderAndFooter>
  <Revisions>...</Revisions>
  <SceneNumberOptions NumberScheme="1A" ...>...</SceneNumberOptions>
  <LockedPages>...</LockedPages>
  <Cast>...</Cast>
  <Actors>...</Actors>

  <!-- Main content: the screenplay itself -->
  <Content>
    <Paragraph Type="Scene Heading">...</Paragraph>
    <Paragraph Type="Action">...</Paragraph>
    ...
  </Content>
</FinalDraft>
```

### 1.1 Root `<FinalDraft>`

| Attribute | Observed Values | Verified |
|-----------|----------------|----------|
| `DocumentType` | `"Script"` | ✓ THE-WAIF, rsdoiel samples |
| `Template` | `"No"`, `"Yes"` | ✓ THE-WAIF (`"No"`) |
| `Version` | `"2"` | ✓ THE-WAIF |

The `standalone="no"` XML declaration is observed in THE-WAIF's FDX but not in all
examples — it may be Final Draft version-dependent.

### 1.2 Preamble Elements

These appear **before** `<Content>` in the document structure. All are optional
and vary by application.

| Element | Purpose | Observed |
|---------|---------|----------|
| `<TitlePage>` | Title page content (free-form Paragraphs) | ✓ THE-WAIF |
| `<HeaderAndFooter>` | Page header/footer configuration | ✓ THE-WAIF |
| `<Revisions>` | Revision color/scheme definitions | ✓ THE-WAIF |
| `<SceneNumberOptions>` | Numbering scheme (e.g., `NumberScheme="1A"`) | ✓ THE-WAIF, rsdoiel |
| `<LockedPages>` | Production-locked page markers | ✓ THE-WAIF |
| `<Cast>` | Cast member definitions with actor mapping | ✓ rsdoiel |
| `<Actors>` | Voice actor definitions (for text-to-speech) | ✓ rsdoiel |
| `<Macros>` | Keyboard macro definitions | ✓ rsdoiel |
| `<SplitState>` | UI split-pane state (editor metadata) | ✓ rsdoiel |
| `<CharacterHighlighting>` | Per-character color highlighting | ✓ rsdoiel |
| `<TagCategories>` | Production tag category definitions | ✓ THE-WAIF (22 categories) |
| `<DisplayBoards>` | Beat board / story map state | ✓ rsdoiel, schoonmaker |

**Parser guidance**: Preamble elements are non-critical for basic script parsing.
Production tagging (`TagCategories`, `TagData`) is relevant for breakdown tools.
Cast/actor mapping is relevant for casting workflows.

---

## 2. Paragraph Types

Every paragraph in FDX is a `<Paragraph>` with a `Type` attribute. The type defines
how the text should be rendered and what structural role it plays.

### 2.1 Complete Type List

| Type | Semantics | Observed in THE-WAIF | Count |
|------|-----------|---------------------|-------|
| `Scene Heading` | Scene heading / slugline | ✓ | 279 |
| `Action` | Action/description | ✓ | 1042 |
| `Character` | Character name cue | ✓ | 751 |
| `Dialogue` | Spoken dialogue | ✓ | 772 |
| `Parenthetical` | Actor direction (parenthesized) | ✓ | 22 |
| `Transition` | "CUT TO:", "FADE OUT." | ✓ | 22 |
| `Shot` | "CLOSE ON", "ANGLE ON" | ✓ | 1 |
| `General` | Title page, notes, free text | ✓ | 55 |
| `Lyrics` | Song lyrics **[UNCONFIRMED]** | ✗ | 0 |
| `Outline N` | Outline/beat elements **[UNCONFIRMED]** | ✗ | 0 |
| `Page #` | Page number in title page | ✓ | 2 |
| `Normal Text` | Free text in title page | ✓ | 2 |
| `Script` | Script-level metadata **[UNCONFIRMED]** | ✓ | 1 |

**Source**: Paragraph types verified against THE-WAIF FDX (278 scenes, 2,948 paragraphs).
`Lyrics` and `Outline N` mentioned in rsdoiel and scriptty docs but not observed in
production files.

### 2.2 Paragraph Children

Each `<Paragraph>` contains one or more `<Text>` children. Multiple `<Text>` children
arise from:
- **Revision-mode editing**: Final Draft splits text at edit boundaries for revision
  tracking with `Change` and `Range` attributes **[PROVISIONAL]**
- **Styled text spans**: Each differently-styled segment gets its own `<Text>` child

```xml
<Paragraph Type="Action">
  <Text>Normal text </Text>
  <Text Style="Underline">ON BEN</Text>
  <Text> more text.</Text>
</Paragraph>
```

**Parse rule**: Join all `<Text>` children by their text content, preserving order.

### 2.3 Text Styles

The `Style` attribute on `<Text>` elements uses a `+`-delimited list of style names.

**Observed in THE-WAIF (117 styled elements)**:

| Style | Count | Notes |
|-------|-------|-------|
| `Italic` | 45 | Most common |
| `Bold` | 30 | |
| `Underline` | 20 | |
| `Bold+AllCaps` | 4 | Combined styles via `+` |
| `Bold+Underline` | 1 | Combined styles via `+` |

**Complete style list** (from StackOverflow XSL + rsdoiel):

- `Bold` — bold text
- `Italic` — italic text
- `Underline` — underlined text
- `Strikeout` — strikethrough text **[UNCONFIRMED — not in THE-WAIF]**
- `AllCaps` — ALL CAPS rendering **[UNCONFIRMED — not in THE-WAIF]**
- `"0"` or `""` — observed in THE-WAIF on some elements, may indicate "no style" or be a Final Draft rendering artifact **[PROVISIONAL]**

**Parse rule**: Split on `+`, treat each token as a boolean style flag.

---

## 3. Scene Headings

### 3.1 Structure

```xml
<Paragraph Type="Scene Heading">
  <SceneProperties Length="2/8" Page="1" Title="" Number="1"/>
  <Text>INT. MASTER BEDROOM - HOUSE - NIGHT</Text>
</Paragraph>
```

### 3.2 SceneProperties Attributes

| Attribute | Type | Observed | Notes |
|-----------|------|----------|-------|
| `Length` | string | ✓ | `"N/8"` format (N = 1-8). Scenes >1 page still report `8/8` **[PROVISIONAL — inferred, not confirmed against multi-page scenes]** |
| `Page` | string | ✓ | Starting page number as string |
| `Title` | string | ✓ | Scene title (rarely used — empty in THE-WAIF) |
| `Number` | string | ✓ | Scene number. Empty = auto-numbered |

### 3.3 Scene Synopsis

Scene synopses are stored as children of `SceneProperties`, nested inside a
`Summary` element **[UNCONFIRMED — not observed in THE-WAIF, sourced from XPath gist and screenplay-js parser]**:

```xml
<SceneProperties Length="2/8" Page="1" Number="1">
  <Summary>
    <Paragraph>
      <Text>Ben wakes up and checks the house.</Text>
    </Paragraph>
  </Summary>
</SceneProperties>
```

### 3.4 Scene Number Schemes

Scene numbers can use letter suffixes (e.g., "12A", "A12"). The numbering scheme
is configured in the preamble:

```xml
<SceneNumberOptions NumberScheme="1A" ...>
```

**Observed in THE-WAIF**: THE-WAIF uses simple integer scene numbers (1, 2, 3...).
Letter-variant numbering not present. THE-WAIF's FDX `SceneNumberOptions` exists
but the scheme value was not directly inspected.

### 3.5 Scene Heading Text Format

```
INT./EXT. LOCATION - SET - TIME OF DAY
```

**Parse rule** (verified against 279 scenes in THE-WAIF):

1. **INT/EXT**: Match `^(INT\.?/?EXT\.?|EXT\.?|INT\.?|I/?E\.?)` — handle `INT./EXT.` combined
2. **Location + Set + Time**: Split on ` - ` from the right
3. **Time of day**: Last segment. Known values: `DAY`, `NIGHT`, `DAWN`, `DUSK`, `MORNING`,
   `AFTERNOON`, `EVENING`, `CONTINUOUS`, `LATER`, `MOMENTS LATER`, `SAME`, `MAGIC HOUR`,
   `SUNRISE`, `SUNSET`. Strip parenthetical markers like `(FLASHBACK)` before matching.
4. **Set name**: Segment after second-to-last ` - `, if present
5. **Location**: Everything before the set name

### 3.6 Narrative Markers

Parenthetical markers in scene headings indicate non-linear narrative:

| Marker | Semantics |
|--------|-----------|
| `(FLASHBACK)` | Scene in the past |
| `(FLASH FORWARD)` | Scene in the future |
| `(DREAM)` | Dream sequence |
| `(MEMORY)` | Memory sequence |

**Observed in THE-WAIF**: `(FLASHBACK)` present in multiple scenes. Other marker
types not present in this file but confirmed in other sources.

---

## 4. Character Cues and Dialogue

### 4.1 Standard Sequence

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

Parentheticals are **optional** and appear between Character and Dialogue.
Multiple parentheticals per dialogue block are possible.

### 4.2 Dual Dialogue

Dual dialogue (two characters speaking simultaneously) uses a `<DualDialogue>`
wrapper element **[PROVISIONAL — not observed in THE-WAIF, sourced from screenplay-js and scriptty docs]**:

```xml
<Paragraph Type="Character">
  <Text>BEN</Text>
  <DualDialogue>
    <Paragraph Type="Character"><Text>BEN</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>Hello.</Text></Paragraph>
    <Paragraph Type="Character"><Text>MARIE</Text></Paragraph>
    <Paragraph Type="Dialogue"><Text>What is it?</Text></Paragraph>
  </DualDialogue>
</Paragraph>
```

**Important**: Earlier revisions of this document incorrectly stated dual dialogue
uses a `^` suffix. That is a **Fountain convention**, not an FDX convention.
The FDX format uses the `<DualDialogue>` wrapper element.

THE-WAIF contains no dual dialogue scenes, so this format is sourced from
Guernsey-Creative's JS parser and Scriptty's FDX analysis. **Verify against a
known dual-dialogue FDX before relying on this in production.**

---

## 5. Script Notes

Script notes are stored as `<ScriptNote>` children within paragraphs
**[PROVISIONAL — not observed in THE-WAIF, sourced from XPath gist]**:

```xml
<Paragraph Type="Scene Heading">
  <SceneProperties Length="1/8" Page="1"/>
  <Text>INT. KITCHEN - DAY</Text>
  <ScriptNote>
    <Paragraph><Text>Check with director about this setting.</Text></Paragraph>
  </ScriptNote>
</Paragraph>
```

THE-WAIF's FDX contains no ScriptNote elements. Other tools (screenplay-js,
schoonmaker) document this structure but handling varies.

---

## 6. Production Tagging

### 6.1 Tag Categories

FDX files can contain production tagging data for breakdown elements. THE-WAIF's
FDX contains 22 `<TagCategory>` elements in the preamble.

```xml
<TagCategories>
  <TagCategory Name="Cast" Color="..." />
  <TagCategory Name="Props" Color="..." />
  ...
</TagCategories>
```

### 6.2 Scene Tags

Within paragraphs, `<TagData>` elements reference tagged categories
**[PROVISIONAL — THE-WAIF contains 2 TagData elements, need further analysis]**:

```xml
<Paragraph Type="Scene Heading">
  <SceneProperties Length="2/8" Page="1"/>
  <Text>INT. KITCHEN - DAY</Text>
  <TagData Category="Props" Tag="Coffee mug" />
</Paragraph>
```

---

## 7. Complete XML Structure

```
FinalDraft [DocumentType, Template, Version]
  ├── TitlePage [Header/Footer content]
  ├── HeaderAndFooter
  ├── Revisions
  ├── SceneNumberOptions [NumberScheme, LeftLocation, RightLocation]
  │    └── FontSpec [Font, Size, Color, ...]
  ├── LockedPages
  ├── Cast / Actors
  ├── Macros
  ├── TagCategories
  │    └── TagCategory [Name, Color]
  ├── SplitState (editor UI state)
  ├── DisplayBoards (beat board state)
  └── Content
       └── Paragraph [Type] × N
            ├── SceneProperties (if Type="Scene Heading")
            │    ├── [Length, Page, Title, Number]
            │    └── Summary (optional)
            │         └── Paragraph
            │              └── Text
            ├── Text [Style?] × N
            ├── DualDialogue (optional)
            │    └── Paragraph [Type="Character"|"Dialogue"] × N
            ├── ScriptNote (optional)
            │    └── Paragraph
            │         └── Text
            └── TagData [Category, Tag] (optional)
```

---

## 8. Known Format Variations

### 8.1 Multi-Application Compatibility

FDX is produced by multiple applications, each with subtle differences:

| Application | Known Variations |
|-------------|-----------------|
| Final Draft 8-12 | Full preamble, revision marks, SplitState |
| Fade In | Cleaner XML, fewer preamble elements **[PROVISIONAL]** |
| Trelby | May omit preamble entirely |
| Amazon Storywriter | Similar to Fade In, fewer metadata elements |
| Celtx | May have non-standard paragraph types |

### 8.2 Revision Support

Final Draft supports revision mode (colored pages for production drafts). In FDX,
this manifests as:
- `<Revisions>` element in preamble listing revision colors/names
- `RevisionID` attributes on `<Text>` elements
- `Change` attributes on `<Text>` elements **[UNCONFIRMED]**
- `Range` attributes tracking character-level edit positions **[UNCONFIRMED]**

For basic parsing, these can be safely ignored. For production workflows,
revision-aware parsing would need to track `RevisionID` values.

### 8.3 Locked Pages

Production drafts can lock page numbers (`<LockedPages>` in preamble).
THE-WAIF's FDX contains this element. Page-locked scenes may have additional
attributes **[PROVISIONAL]**.

---

## 9. Validation Rules

Based on observed behavior across 278 production scenes and community documentation:

1. **Exactly one** `<Content>` child inside `<FinalDraft>`
2. All `Scene Heading` paragraphs **must** have a `<SceneProperties>` child ✓
3. Character paragraphs are **typically** followed by 0-1 Parenthetical, then 1 Dialogue
4. Scene heading text contains **at minimum** a location name
5. Page lengths are in `N/8` format where N is 1-8 ✓
6. XML is valid UTF-8 ✓
7. Style values are `+`-delimited combinations of known style names ✓
8. No public DTD — **validate against these rules, not XSD**

---

## 10. Known Gaps

These features are documented in community sources but **not yet verified** against
production FDX files by this project:

| Feature | Status | Priority |
|---------|--------|----------|
| Dual dialogue (`<DualDialogue>` wrapper) | PROVISIONAL — from screenplay-js, scriptty | MEDIUM |
| Scene synopses (`Summary/Paragraph/Text`) | UNCONFIRMED — from XPath gist, screenplay-js | LOW |
| Script notes (`<ScriptNote>`) | UNCONFIRMED — from XPath gist | LOW |
| Multi-page scene length (beyond `8/8`) | PROVISIONAL — inferred, needs multi-page test file | LOW |
| Revision marks (`Change`, `Range`, `RevisionID`) | UNCONFIRMED — mentioned in scriptty docs | LOW |
| Letter-variant scene numbers (`"12A"`, `"A12"`) | PROVISIONAL — scheme exists, no examples in THE-WAIF | LOW |
| `Lyrics` paragraph type | UNCONFIRMED — from rsdoiel | LOW |
| `Outline N` paragraph types | UNCONFIRMED — from rsdoiel | LOW |
| TagData structure and semantics | PROVISIONAL — 2 elements in THE-WAIF, need analysis | MEDIUM |
| HeaderAndFooter structure | UNCONFIRMED — exists in THE-WAIF, not parsed | LOW |

**To verify**: Find an FDX file with dual dialogue, scene synopses, script notes,
and multi-page scenes. Submit as a PR to this repo.

---

## 11. See Also

- [Final Draft](https://www.finaldraft.com/)
- [Fountain](https://fountain.io/) — plain-text screenplay format
- [rsdoiel/fdx](https://github.com/rsdoiel/fdx) — Go FDX package
- [Guernsey-Creative/screenplay-js](https://github.com/Guernsey-Creative/screenplay-js) — JS FDX parser
- [jzucker2/schoonmaker](https://github.com/jzucker2/schoonmaker) — Python FDX diff tool
- [surrealroad/fdx-queries](https://gist.github.com/surrealroad/effaa4f84d8ba53cecb6) — XPath queries for FDX
