# Final Draft XML (.fdx) Format Specification

**Status**: Verified against production FDX files, multiple open-source parsers, and
community documentation. Items marked **[PROVISIONAL]** or **[UNCONFIRMED]** have not
been directly observed in production files by this project's authors.

**Sources**:
- Production FDX file (278 scenes, THE-WAIF, Final Draft 11/12)
- `rsdoiel/fdx` Go package — 6 verified test FDX files + complete Go data model (GitHub)
- `stultus/scriptty` FDX import analysis (GitHub #190)
- `Guernsey-Creative/screenplay-js` FDX parser source (GitHub)
- XPath queries gist by surrealroad (GitHub gist)
- StackOverflow XSL transform for FDX → HTML
- `jzucker2/schoonmaker` Python FDX tool (GitHub)

> **Note**: Final Draft does not publish a public XML schema or DTD for the FDX
> format. All knowledge here is reverse-engineered from files produced by Final Draft
> 8+, Fade In, Trelby, Amazon Storywriter, and Celtx. Different applications may
> produce subtly different FDX output.

## 0. Version Dependence

FDX features vary across Final Draft versions and export settings. Features
marked **[PROVISIONAL]** or **[UNCONFIRMED]** may exist only in specific versions
or configurations.

| Feature | FD 8 | FD 9 | FD 10 | FD 11 | FD 12 | Fade In | Amazon Storywriter |
|---------|------|------|-------|-------|-------|---------|-------------------|
| Core paragraph types | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `SceneProperties` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `DualDialogue` wrapper | ? | ? | ✓ | ✓ | ✓ | ✓ | ? |
| `Summary` (synopses) | ? | ? | ✓ | ✓ | ✓ | ? | ? |
| `ScriptNote` | ? | ✓ | ✓ | ✓ | ✓ | ? | ? |
| `TagData` / `TagCategory` | — | — | ✓ | ✓ | ✓ | ✓ | — |
| `RevisionID` on `Text` | ? | ✓ | ✓ | ✓ | ✓ | — | — |
| `StartsNewPage` on `Paragraph` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `Alignment` on `Paragraph` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `NumberScheme="1A"` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `Beat` / `StoryMap` elements | — | — | ✓ | ✓ | ✓ | — | — |
| `Cast` / `Actors` | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| `LockedPages` | — | — | — | ✓ | ✓ | — | — |
| `SmartType` / `MoresAndContinueds` | ✓ | ✓ | ✓ | ✓ | ✓ | — | — |
| `SplitState` (editor UI) | ? | ✓ | ✓ | ✓ | ✓ | — | — |

**Legend**: ✓ = verified in test files, — = absent in test files, ? = unknown / not yet verified.

Key: Production tagging (`TagData`, `TagCategory`) and locked pages appear to be
Final Draft 11+ features. The `<DualDialogue>` wrapper for simultaneous dialogue is
absent from all available test files but confirmed in parser source code.

## 0.1 Application-Specific Variations

| Application | Notable differences from Final Draft |
|-------------|--------------------------------------|
| **Fade In** | Cleaner XML, fewer preamble elements, may omit `Revisions` and `SplitState` |
| **Amazon Storywriter** | Similar to Fade In, may omit `Cast`/`Actors` |
| **Trelby** | Minimal preamble, may omit `TitlePage` entirely |
| **Celtx** | May produce non-standard paragraph types, omits most preamble |

**Data**: Application variations inferred from rsdoiel/fdx source code and Go
struct field optionality (`omitempty` tags).

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
| `<Revisions>` | Revision color/scheme definitions (revision-mode support) | ✓ THE-WAIF |
| `<SceneNumberOptions>` | Numbering scheme (e.g., `NumberScheme="1A"`) | ✓ THE-WAIF, rsdoiel |
| `<LockedPages>` | Production-locked page markers | ✓ THE-WAIF |
| `<Cast>` | Cast member definitions with actor mapping | ✓ rsdoiel |
| `<Actors>` | Voice actor definitions (for text-to-speech) | ✓ rsdoiel |
| `<Macros>` | Keyboard macro definitions | ✓ rsdoiel |
| `<SplitState>` | UI split-pane state (editor metadata) | ✓ rsdoiel |
| `<CharacterHighlighting>` | Per-character color highlighting | ✓ rsdoiel |
| `<TagCategories>` | Production tag category definitions | ✓ THE-WAIF (22 categories) |
| `<DisplayBoards>` | Beat board / story map state | ✓ rsdoiel, schoonmaker |
| `<ElementSettings>` | Per-element formatting overrides | ✓ rsdoiel struct |
| `<PageLayout>` | Page layout configuration | ✓ rsdoiel struct |
| `<WindowState>` | Editor window state (purely UI) | ✓ rsdoiel struct |
| `<TextState>` | Text editing state | ✓ rsdoiel struct |
| `<ScriptNoteDefinitions>` | Script note category definitions | ✓ rsdoiel struct |
| `<SmartType>` | SmartType configuration | ✓ rsdoiel struct |
| `<MoresAndContinueds>` | MORE/CONT'D configuration | ✓ rsdoiel struct |
| `<SpellCheckIgnoreLists>` | Spelling ignore lists | ✓ rsdoiel struct |
| `<UnanchoredScriptNotes>` | Unanchored script notes container | ✓ rsdoiel sample-01 |
| `<Characters>` | Character name autocomplete list | ✓ rsdoiel sample-01 |
| `<SceneIntros>` | Scene intro autocomplete (INT./EXT./etc) | ✓ rsdoiel sample-01 |
| `<Locations>` | Location autocomplete list | ✓ rsdoiel sample-01 |
| `<TimesOfDay>` | Time-of-day autocomplete list | ✓ rsdoiel sample-01 |
| `<Transitions>` | Transition autocomplete list | ✓ rsdoiel sample-01 |
| `<Extensions>` | Character extension list (V.O., O.S., etc.) | ✓ rsdoiel sample-01 |

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
| `Beat` | Beat board element **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Cast List` | Cast list **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Center` | Centered text **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Last Revised` | Last revision marker **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Page #` | Page number in title page **[VERIFIED]** | ✓ | 2 |
| `Right` | Right-aligned text **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Script` | Script-level metadata **[VERIFIED]** | ✓ | 1 |
| `StoryMap` | Story map element **[VERIFIED]** | ✗ | ✓ in rsdoiel |
| `Lyrics` | Song lyrics **[UNCONFIRMED]** | ✗ | 0 |
| `Outline N` | Outline/beat elements **[UNCONFIRMED]** | ✗ | 0 |
| `Normal Text` | Free text in title page **[VERIFIED]** | ✓ | 2 |

**Note**: `Beat`, `Cast List`, `Center`, `Last Revised`, `Right`, and `StoryMap` are
title-page and preamble paragraph types. They appear in rsdoiel's 6 test files but
not in THE-WAIF's FDX export. They are typically generated by Final Draft's title
page editor, beat board, and story map features.

### 2.2 Paragraph Attributes

Paragraphs can have attributes beyond `Type`. These are verified against rsdoiel's
6 sample FDX files and the Go struct definitions.

| Attribute | Example | Observed | Description |
|-----------|---------|----------|-------------|
| `Type` | `"Action"` | ✓ | Paragraph type (required) |
| `Number` | `"1"`, `"12A"` | ✓ | Scene number (Scene Headings only) |
| `Alignment` | `"Center"`, `"Right"` | ✓ | Text alignment (14 in sample-01.fdx) |
| `StartsNewPage` | `"Yes"` | ✓ | Page break before this paragraph (14 in sample-01.fdx) |
| `FirstIndent` | ? | ✓ in struct | First-line indent **[UNCONFIRMED]** |
| `Leading` | ? | ✓ in struct | Line spacing **[UNCONFIRMED]** |
| `LeftIndent` | ? | ✓ in struct | Left margin **[UNCONFIRMED]** |
| `RightIndent` | ? | ✓ in struct | Right margin **[UNCONFIRMED]** |
| `SpaceBefore` | ? | ✓ in struct | Space before paragraph **[UNCONFIRMED]** |
| `Spacing` | ? | ✓ in struct | Paragraph spacing **[UNCONFIRMED]** |

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

### 2.4 Additional Text Attributes

From rsdoiel/fdx Go struct definitions (`Text` struct). These attributes appear
on `<Text>` elements in addition to `Style`.

| Attribute | Example | Observed | Purpose |
|-----------|---------|----------|---------|
| `Style` | `"Bold+Underline"` | ✓ | Text style flags |
| `RevisionID` | `"1"`, `"2"` | ✓ (17 in sample-01.fdx) | Revision layer this text belongs to |
| `Font` | `"Courier Final Draft"` | ✓ in struct | Font name |
| `Size` | `"12"` | ✓ in struct | Font size |
| `Color` | `"#000000000000"` | ✓ in struct | Text color (hex) |
| `Background` | `"#FFFFFFFFFFFF"` | ✓ in struct | Background color (hex) |
| `AdornmentStyle` | `"0"` | ✓ in struct | Adornment style ID |

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

### 3.3 Scene Arc Beats

**[VERIFIED — rsdoiel sample-01.fdx]**. `SceneProperties` can contain `<SceneArcBeats>` with
per-character arc beat tracking:

```xml
<SceneProperties Length="2/8" Page="1">
  <SceneArcBeats>
    <CharacterArcBeat Name="PROGRAMMER"></CharacterArcBeat>
  </SceneArcBeats>
</SceneProperties>
```

This appears to be a Final Draft beat board feature that links character arcs to
specific scenes. The beat data itself may be stored in `<DisplayBoards>` elements
in the preamble. The empty `CharacterArcBeat` element (no children, no attributes
beyond `Name`) is the observed form in rsdoiel's test data.

### 3.3 Scene Synopsis

**[VERIFIED — REARVIEW.fdx, Final Draft 11/12 export]**. Scene synopses are stored
as `<Summary>` children of `<SceneProperties>`:

```xml
<SceneProperties Length="2/8" Page="1" Title="">
  <Summary>
    <Paragraph Alignment="Left" FirstIndent="0.00" Leading="Regular"
               LeftIndent="0.00" RightIndent="1.39" SpaceBefore="0"
               Spacing="1" StartsNewPage="No">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF" Color="#000000000000"
            Font="Courier Final Draft" RevisionID="0" Size="12" Style="">
        The racecar catches fire.
      </Text>
    </Paragraph>
  </Summary>
  <SceneArcBeats/>
</SceneProperties>
```

**Structure**: The `<Summary>` contains a full `<Paragraph>` with all standard
paragraph attributes and `<Text>` children. The synopsis text follows the same
`<Text>` + attribute pattern as regular paragraphs. Despite the XPath gist
showing `Summary/Paragraph/Text` as the path, the actual structure is
`Summary → Paragraph → Text`. **[CONFIRMED]**

**Note**: Summary paragraphs carry the full attribute set (Alignment, indents,
spacing) even though synopses are plain text. These attributes may be ignored
during import.

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
wrapper element inside a `<Paragraph Type="Character">`.

**[VERIFIED — REARVIEW.fdx, Fade In export, 1 dual dialogue exchange]**:

```xml
<Paragraph Type="Character">
  <DualDialogue>
    <Paragraph Type="Character">
      <Text>RAY</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>I said no... don't give me this bullshit.</Text>
    </Paragraph>
    <Paragraph Type="Character">
      <Text>LORY</Text>
    </Paragraph>
    <Paragraph Type="Dialogue">
      <Text>-you said weed stayed in the system for weeks...</Text>
    </Paragraph>
  </DualDialogue>
</Paragraph>
```

**Structure**:
1. Outer `<Paragraph Type="Character">` — the first character's cue (container)
2. `<DualDialogue>` wrapper
3. Character A → Dialogue A → Character B → Dialogue B in sequence
4. All inner paragraphs follow the same `<Text>` + attributes pattern

**Parse rule**: When a `Character` paragraph has a `<DualDialogue>` child, walk
its children (Character + Dialogue paragraphs in pairs) rather than treating the
outer paragraph as a single character cue.

**Note**: THE-WAIF contains no dual dialogue. This structure was confirmed against
a 207-scene Fade In FDX export (REARVIEW.fdx, 520KB). The Fade In application
produces FDX that Final Draft 11+ can import.

---

## 5. Script Notes

**[VERIFIED — REARVIEW.fdx, Final Draft 11/12 export, 3 ScriptNotes]**.

Script notes are stored as `<ScriptNote>` children within any paragraph type.
They can appear inside `General`, `Scene Heading`, or any other paragraph:

```xml
<Paragraph Type="General">
  <ScriptNote Author="" Color="#000000000000"
              DateModified="20260725T174904" DateTime="20260725T174846"
              Name="note for AI" Type="">
    <Paragraph Alignment="Left" FirstIndent="0.00" Leading="Regular"
               LeftIndent="0.00" RightIndent="1.39" SpaceBefore="0"
               Spacing="1" StartsNewPage="No">
      <Text AdornmentStyle="0" Background="#FFFFFFFFFFFF"
            Color="#000000000000" Font="Courier Final Draft"
            RevisionID="0" Size="12" Style="">
        This is where I made something dual-dialogue.
      </Text>
    </Paragraph>
  </ScriptNote>
  <DualDialogue>
    ...dual dialogue content...
  </DualDialogue>
</Paragraph>
```

**ScriptNote attributes**:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `Author` | `""`, name | Script note author |
| `Color` | `"#000000000000"` | Note color |
| `DateModified` | `"20260725T174904"` | Last modified (ISO compact) |
| `DateTime` | `"20260725T174846"` | Created timestamp (ISO compact) |
| `Name` | `"note for AI"` | Note name/title |
| `Type` | `""` | Note type (empty in observed files) |

The script note body is a full `<Paragraph>` with standard attributes and
`<Text>` children. A single paragraph can contain both a `<ScriptNote>` AND
other content (like `<DualDialogue>`), showing they coexist independently.

---

## 6. Production Tagging

### 6.1 Tag Categories

**[VERIFIED — THE-WAIF (22 categories), REARVIEW.fdx (22 categories)]**

FDX files can contain production tagging data for breakdown elements in a
`<TagData>` element in the preamble. Confirmed in both Final Draft and Fade In
exports:

```xml
<TagData>
  <TagCategories>
    <TagCategory Color="#00000000FFFF" Id="01fc9642-84ff-4366-b37c-a3068dee57e8"
                 Name="Cast" Number="1" Style="Bold"/>
    <TagCategory Color="#0000BFBFFFFF" Id="028a4e2b-b507-4d09-88ab-90e3edae9071"
                 Name="Background Actors" Number="2" Style="Bold"/>
    ...
  </TagCategories>
  <TagDefinitions/>
  <Tags/>
</TagData>
```

**TagCategory attributes**:

| Attribute | Example | Description |
|-----------|---------|-------------|
| `Name` | `"Cast"`, `"Props"` | Human-readable category name |
| `Color` | `"#00000000FFFF"` | RGB color with alpha prefix |
| `Id` | UUID | Unique identifier (Fade In uses UUIDs; Final Draft may use integers) |
| `Number` | `"1"` | Category sort order |
| `Style` | `"Bold"` | Text style for category label |

**`<TagDefinitions/>` and `<Tags/>`**: Present in Fade In exports but empty in
observed files. These may store per-scene tag assignments when populated.
**[PROVISIONAL]**

### 6.2 Scene Tags

Within scene heading paragraphs, `<TagData>` elements reference tagged categories.
THE-WAIF contains 2 TagData elements in the preamble (not scene-level). Scene-level
tagging structure is still unconfirmed. **[PROVISIONAL]**

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
production FDX files by this project.

| Feature | Status | Priority | Source |
|---------|--------|----------|--------|
| Multi-page scene length (beyond `8/8`) | PROVISIONAL | LOW | Inferred |
| `Lyrics` paragraph type | UNCONFIRMED | LOW | rsdoiel struct |
| `Outline N` paragraph types | UNCONFIRMED | LOW | rsdoiel struct |
| Scene-level TagData assignments | PROVISIONAL | MEDIUM | TagData in preamble only |
| `FirstIndent` / `Leading` / `LeftIndent` values | UNCONFIRMED | LOW | rsdoiel struct only |
| `SmartType` configuration format | UNCONFIRMED | LOW | rsdoiel struct only |
| `SplitState` / `WindowState` schema | UNCONFIRMED | LOW | rsdoiel struct (UI metadata) |

**Newly verified** (removed from gaps in this revision): DualDialogue wrapper
structure, TagCategory UUID-based attributes, `Fade In` as FDX source application,
`RevisionID` on all Text elements (4,493+ instances confirmed), 207-scene Fade In
export as test fixture. DualDialogue confirmed to use `<DualDialogue>` inside
`<Paragraph Type="Character">` — not the `^` suffix (Fountain convention).
Scene synopses (`Summary`) and Script notes (`ScriptNote` with full attribute set)
verified from Final Draft export of REARVIEW.

**To verify remaining gaps**: Find or produce FDX files with dual dialogue, scene
synopses, lyrics, and script notes. Submit test fixtures as a PR.

---

## 11. See Also

- [Final Draft](https://www.finaldraft.com/)
- [Fountain](https://fountain.io/) — plain-text screenplay format
- [rsdoiel/fdx](https://github.com/rsdoiel/fdx) — Go FDX package
- [Guernsey-Creative/screenplay-js](https://github.com/Guernsey-Creative/screenplay-js) — JS FDX parser
- [jzucker2/schoonmaker](https://github.com/jzucker2/schoonmaker) — Python FDX diff tool
- [surrealroad/fdx-queries](https://gist.github.com/surrealroad/effaa4f84d8ba53cecb6) — XPath queries for FDX
