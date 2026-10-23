"""Core logic for the Fade In MCP server.

Reads and edits Fade In (.fadein / Open Screenplay Format) documents without
launching Fade In. Parsing reuses the sibling `open-fdx-toolkit` package.

Two invariants matter here:

1. Page count comes from ``<info pagecount="...">`` — the number Fade In itself
   computed. Never estimate pages from scene counts; the toolkit's
   ``page_eighths`` defaults to 1 per scene for OSF input and yields nonsense.
2. Writes never rebuild the document from parsed scenes. They perform surgical
   text replacement inside ``document.xml`` and copy every other zip entry
   through untouched, so embedded assets, revision marks, notes and styling
   survive.
"""

from __future__ import annotations

import difflib
import hashlib
import html
import io
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from fadein_parser import parse_fadein_bytes
from fdx_parser import ParsedScene

DEFAULT_DRAFTS_DIR = Path(
    os.environ.get("FADEIN_DRAFTS_DIR", "/opt/data/home/projects/the-waif/drafts")
).expanduser()

DRAFT_SUFFIXES = (".fadein", ".fdx", ".fountain", ".txt", ".pdf")
CONVERSION_SUFFIXES = (".fadein", ".fdx", ".fountain", ".pdf", ".txt")


# --------------------------------------------------------------------------- #
# Document loading
# --------------------------------------------------------------------------- #


@dataclass
class Script:
    """A loaded screenplay file plus the bits of OSF metadata worth keeping."""

    path: Path
    data: bytes
    scenes: list[ParsedScene]
    pagecount: int | None = None
    revision: str | None = None
    draft_uuid: str | None = None
    saved_with: str | None = None
    is_osf: bool = False

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def size_kb(self) -> int:
        return round(len(self.data) / 1024)

    def fingerprint(self) -> str:
        return hashlib.sha256(self.data).hexdigest()[:12]


def _attr(xml: str, tag: str, attr: str) -> str | None:
    m = re.search(rf'<{tag}\b[^>]*\b{attr}="([^"]*)"', xml)
    return m.group(1) if m else None


def load_script(path: str | Path) -> Script:
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"no screenplay at {p}")
    data = p.read_bytes()
    scenes = parse_fadein_bytes(data)
    script = Script(path=p, data=data, scenes=scenes)

    if zipfile.is_zipfile(io.BytesIO(data)):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                xml = z.read("document.xml").decode("utf-8", "replace")
        except KeyError:
            return script
        script.is_osf = True
        pc = _attr(xml, "info", "pagecount")
        script.pagecount = int(pc) if pc and pc.isdigit() else None
        script.revision = _attr(xml, "settings", "revision")
        script.draft_uuid = _attr(xml, "info", "draft_uuid")
        script.saved_with = _attr(xml, "fadein_settings", "saved_with")
    return script


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #

_CHAR_SUFFIX = re.compile(r"\s*\((?:[^)]*)\)\s*$")


def character_key(name: str) -> str:
    """Canonical key for a character cue: strips (O.S.)/(V.O.)/(CONT'D), case."""
    s = _CHAR_SUFFIX.sub("", name.strip()).strip().lower()
    return re.sub(r"\s+", " ", s)


def scene_text(scene: ParsedScene, numbered: bool = True) -> str:
    """Render a parsed scene as plain readable screenplay text."""
    lines: list[str] = []
    head = scene.slugline or ""
    if numbered and scene.scene_number:
        head = f"{scene.scene_number}. {head}"
    lines.append(head)
    for para in scene.paragraphs:
        text = " ".join(para.text.split())
        if not text:
            continue
        kind = (para.type or "").lower()
        if kind in {"character", "parenthetical", "dialogue", "dual dialogue"}:
            lines.append(f"\t{text}")
        elif kind == "transition":
            lines.append(f"\t\t{text}")
        else:
            lines.append(text)
    return "\n".join(lines).rstrip() + "\n"


def _norm_slug(slug: str) -> str:
    s = slug.lower().strip()
    s = re.sub(r"^\d+[a-z]?\s*[.)-]?\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _scene_words(scene: ParsedScene) -> int:
    return len(" ".join(p.text for p in scene.paragraphs).split())


# --------------------------------------------------------------------------- #
# Reports
# --------------------------------------------------------------------------- #


def script_info(path: str | Path) -> dict:
    s = load_script(path)
    cues: dict[str, int] = {}
    display: dict[str, str] = {}
    for sc in s.scenes:
        for cue in sc.characters:
            k = character_key(cue)
            if not k:
                continue
            cues[k] = cues.get(k, 0) + 1
            display.setdefault(k, _CHAR_SUFFIX.sub("", cue.strip()))

    locations: dict[str, int] = {}
    for sc in s.scenes:
        loc = (sc.location or "").strip().lower()
        if loc:
            locations[loc] = locations.get(loc, 0) + 1

    paragraphs = sum(len(sc.paragraphs) for sc in s.scenes)
    words = sum(_scene_words(sc) for sc in s.scenes)

    return {
        "file": s.name,
        "path": str(s.path),
        "size_kb": s.size_kb,
        "sha256_12": s.fingerprint(),
        "format": "Open Screenplay Format (.fadein)" if s.is_osf else "other",
        "saved_with": s.saved_with,
        "revision": s.revision,
        "draft_uuid": s.draft_uuid,
        "pages": s.pagecount,
        "scenes": len(s.scenes),
        "paragraphs": paragraphs,
        "words": words,
        "characters_in_script": len(cues),
        "locations": len(locations),
        "first_scene": s.scenes[0].slugline if s.scenes else None,
        "last_scene": s.scenes[-1].slugline if s.scenes else None,
        "flashback_scenes": [
            sc.scene_number for sc in s.scenes if sc.narrative_position_hint
        ],
        "top_characters": sorted(cues, key=lambda k: -cues[k])[:8],
    }


def list_scenes(
    path: str | Path, offset: int = 0, limit: int = 40, contains: str | None = None
) -> dict:
    s = load_script(path)
    rows = []
    needle = (contains or "").lower()
    for sc in s.scenes:
        blob = (sc.slugline + " " + " ".join(p.text for p in sc.paragraphs)).lower()
        if needle and needle not in blob:
            continue
        first_action = next(
            (
                " ".join(p.text.split())
                for p in sc.paragraphs
                if (p.type or "").lower() not in {"character", "parenthetical", "dialogue"}
            ),
            "",
        )
        rows.append(
            {
                "n": sc.scene_number,
                "slug": sc.slugline,
                "chars": sorted({character_key(c) for c in sc.characters})[:5],
                "words": _scene_words(sc),
                "opens": first_action[:80],
            }
        )
    total = len(rows)
    page = rows[offset : offset + limit]
    return {
        "file": s.name,
        "pages": s.pagecount,
        "matched": total,
        "offset": offset,
        "returned": len(page),
        "scenes": page,
    }


def _parse_scene_selector(selector: str, available: list[str]) -> list[int]:
    """Accept '12', '12-15', '12,14,20'. Returns indices into `available`."""
    wanted: list[str] = []
    for part in str(selector).replace(" ", "").split(","):
        if not part:
            continue
        m = re.fullmatch(r"(\d+)-(\d+)", part)
        if m:
            lo, hi = int(m.group(1)), int(m.group(2))
            wanted.extend(str(n) for n in range(lo, hi + 1))
        else:
            wanted.append(part)
    index = {n: i for i, n in enumerate(available)}
    return [index[w] for w in wanted if w in index]


def get_scene(path: str | Path, scenes: str) -> dict:
    s = load_script(path)
    numbers = [sc.scene_number for sc in s.scenes]
    picked = _parse_scene_selector(scenes, numbers)
    if not picked:
        raise ValueError(f"no scene matching {scenes!r}; file has {len(numbers)} scenes")
    out = []
    for i in picked:
        sc = s.scenes[i]
        out.append(
            {
                "n": sc.scene_number,
                "slug": sc.slugline,
                "words": _scene_words(sc),
                "text": scene_text(sc, numbered=False),
            }
        )
    return {"file": s.name, "pages": s.pagecount, "scenes": out}


def search(
    path: str | Path,
    query: str,
    regex: bool = False,
    limit: int = 40,
    context_chars: int = 60,
) -> dict:
    s = load_script(path)
    if not query:
        raise ValueError("empty query")
    pattern = re.compile(query if regex else re.escape(query), re.IGNORECASE)
    hits = []
    for sc in s.scenes:
        blocks = [(sc.slugline, "Scene Heading")] + [
            (p.text, p.type or "Action") for p in sc.paragraphs
        ]
        for text, kind in blocks:
            for m in pattern.finditer(text):
                lo = max(0, m.start() - context_chars)
                hi = min(len(text), m.end() + context_chars)
                hits.append(
                    {
                        "scene": sc.scene_number,
                        "slug": sc.slugline,
                        "element": kind,
                        "context": ("…" if lo else "")
                        + text[lo:hi].replace("\n", " ")
                        + ("…" if hi < len(text) else ""),
                    }
                )
                if len(hits) >= limit:
                    return {
                        "file": s.name,
                        "query": query,
                        "truncated": True,
                        "hits": hits,
                    }
    return {"file": s.name, "query": query, "truncated": False, "hits": hits}


def character_report(path: str | Path) -> dict:
    s = load_script(path)
    stats: dict[str, dict] = {}
    for sc in s.scenes:
        keys = {character_key(c) for c in sc.characters if character_key(c)}
        for cue in sc.characters:
            k = character_key(cue)
            if not k:
                continue
            rec = stats.setdefault(k, {"name": cue.strip(), "scenes": 0, "words": 0})
            if sc.scene_number:
                rec.setdefault("_seen", set()).add(sc.scene_number)
        # dialogue words belong to whoever is speaking
        speaker = None
        for p in sc.paragraphs:
            kind = (p.type or "").lower()
            if kind == "character":
                speaker = character_key(p.text)
            elif kind in {"dialogue", "parenthetical"} and speaker:
                stats.setdefault(speaker, {"name": p.text.strip(), "scenes": 0, "words": 0})
                stats[speaker]["words"] += len(p.text.split())
    rows = []
    for k, rec in stats.items():
        seen = rec.pop("_seen", set())
        rows.append(
            {"character": k, "as_written": rec["name"], "scenes": len(seen), "dialogue_words": rec["words"]}
        )
    rows.sort(key=lambda r: (-r["dialogue_words"], -r["scenes"]))
    return {"file": s.name, "pages": s.pagecount, "characters": rows}


def location_report(path: str | Path) -> dict:
    s = load_script(path)
    groups: dict[str, dict] = {}
    for sc in s.scenes:
        loc = (sc.location or "").strip().lower()
        if not loc:
            continue
        rec = groups.setdefault(
            loc, {"location": loc, "scenes": [], "int_ext": set(), "times": set()}
        )
        rec["scenes"].append(sc.scene_number)
        if sc.interior_exterior:
            rec["int_ext"].add(sc.interior_exterior.lower())
        if sc.time_of_day:
            rec["times"].add(sc.time_of_day.lower())
    rows = [
        {
            "location": r["location"],
            "scene_count": len(r["scenes"]),
            "int_ext": sorted(r["int_ext"]),
            "times": sorted(r["times"]),
            "scenes": r["scenes"],
        }
        for r in groups.values()
    ]
    rows.sort(key=lambda r: (-r["scene_count"], r["location"]))
    return {"file": s.name, "distinct_locations": len(rows), "locations": rows}


def _pair_scenes(
    left: list[ParsedScene], right: list[ParsedScene]
) -> list[tuple[ParsedScene, ParsedScene]]:
    """Pair scenes from two drafts by slugline, then by text similarity.

    Renumbering must not read as a rewrite, and neither must reordering of
    scenes that share a slugline (a repeated INT. LODGE ROOM - NIGHT). Group by
    normalised slugline; when counts differ, the leftover scenes fall out as
    added or removed.
    """
    def group(scenes: list[ParsedScene]) -> dict[str, list[ParsedScene]]:
        out: dict[str, list[ParsedScene]] = {}
        for sc in scenes:
            out.setdefault(_norm_slug(sc.slugline), []).append(sc)
        return out

    gl, gr = group(left), group(right)
    pairs: list[tuple[ParsedScene, ParsedScene]] = []
    for slug, ls in gl.items():
        rs = gr.get(slug, [])
        if not rs:
            continue
        if len(ls) == 1 and len(rs) == 1:
            pairs.append((ls[0], rs[0]))
            continue
        # greedy best-match on paragraph text, so reordered duplicates pair up
        scored = []
        for i, a in enumerate(ls):
            for j, b in enumerate(rs):
                ratio = difflib.SequenceMatcher(
                    None, [p.text for p in a.paragraphs], [p.text for p in b.paragraphs]
                ).ratio()
                scored.append((ratio, i, j))
        scored.sort(reverse=True)
        used_l: set[int] = set()
        used_r: set[int] = set()
        for _ratio, i, j in scored:
            if i in used_l or j in used_r:
                continue
            used_l.add(i)
            used_r.add(j)
            pairs.append((ls[i], rs[j]))
    return pairs


def compare_drafts(path_a: str | Path, path_b: str | Path) -> dict:
    a, b = load_script(path_a), load_script(path_b)
    pairs = _pair_scenes(a.scenes, b.scenes)
    paired_b = {id(sb) for _sa, sb in pairs}

    paired_a = {id(sa) for sa, _sb in pairs}
    removed = [sa for sa in a.scenes if id(sa) not in paired_a]
    added = [sb for sb in b.scenes if id(sb) not in paired_b]

    changed = []
    for sa, sb in pairs:
        pa = [p.text for p in sa.paragraphs]
        pb = [p.text for p in sb.paragraphs]
        if pa == pb:
            continue
        sm = difflib.SequenceMatcher(None, pa, pb)
        added_lines = removed_lines = 0
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag in {"replace", "delete"}:
                removed_lines += i2 - i1
            if tag in {"replace", "insert"}:
                added_lines += j2 - j1
        changed.append(
            {
                "scene": sb.scene_number,
                "slug": sb.slugline,
                "paragraphs_added": added_lines,
                "paragraphs_removed": removed_lines,
                "delta": added_lines - removed_lines,
                "words_before": _scene_words(sa),
                "words_after": _scene_words(sb),
            }
        )
    changed.sort(key=lambda r: -abs(r["delta"]))

    wa = sum(_scene_words(sc) for sc in a.scenes)
    wb = sum(_scene_words(sc) for sc in b.scenes)
    return {
        "a": {"file": a.name, "pages": a.pagecount, "scenes": len(a.scenes), "words": wa},
        "b": {"file": b.name, "pages": b.pagecount, "scenes": len(b.scenes), "words": wb},
        "page_delta": (b.pagecount - a.pagecount)
        if (a.pagecount is not None and b.pagecount is not None)
        else None,
        "scene_delta": len(b.scenes) - len(a.scenes),
        "word_delta": wb - wa,
        "scenes_removed": [
            {"slug": sc.slugline, "words": _scene_words(sc)} for sc in removed
        ],
        "scenes_added": [
            {"slug": sc.slugline, "words": _scene_words(sc)} for sc in added
        ],
        "scenes_changed": changed[:25],
        "changed_count": len(changed),
    }



# --------------------------------------------------------------------------- #
# Surgical text replacement (preserves everything the parser can't represent)
# --------------------------------------------------------------------------- #

_PARA_RE = re.compile(r"<para\b[^>]*>.*?</para>", re.DOTALL)
_TEXT_RE = re.compile(r"(<text\b[^>]*>)(.*?)(</text>)", re.DOTALL)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


@dataclass
class Para:
    """A <para> block with its text runs mapped back to document offsets."""

    span: tuple[int, int]
    raw: str
    runs: list[tuple[int, int, str, list[str]]] = field(default_factory=list)
    # each run: (start, end, plain_text, original_attr_list)

    @property
    def plain(self) -> str:
        return "".join(r[2] for r in self.runs)


def _parse_paras(xml: str) -> list[Para]:
    paras: list[Para] = []
    for m in _PARA_RE.finditer(xml):
        raw = m.group(0)
        runs = []
        plain_pos = 0
        for tm in _TEXT_RE.finditer(raw):
            content = html.unescape(tm.group(2))
            runs.append((plain_pos, plain_pos + len(content), content, tm.group(1)))
            plain_pos += len(content)
        paras.append(Para(span=(m.start(), m.end()), raw=raw, runs=runs))
    return paras


_SLUG_RE = re.compile(
    r"^\s*(?:INT\.?/EXT\.?|EXT\.?/INT\.?|I/E\.?|INT\.?|EXT\.?)\s+\S", re.IGNORECASE
)


def _is_scene_heading(para: Para) -> bool:
    """True for a scene heading paragraph.

    Fade In writes `<style basestyle="Scene Heading"/>`; the toolkit builder
    writes `basestylename="Scene Heading"`, so match either spelling and fall
    back to the slugline itself.
    """
    if "Scene Heading" in para.raw:
        return True
    return bool(_SLUG_RE.match(para.plain or ""))


def _scene_windows(paras: list[Para], scene_numbers: list[str], wanted: set[str]) -> list[Para]:
    """Paragraphs belonging to the wanted scene numbers.

    The parsed scene list is in document order, so the n-th heading window is
    the n-th parsed scene.
    """
    heading_idx = [i for i, para in enumerate(paras) if _is_scene_heading(para)]
    out: list[Para] = []
    for i, heading in enumerate(heading_idx):
        if i >= len(scene_numbers):
            break
        if scene_numbers[i] in wanted:
            end = heading_idx[i + 1] if i + 1 < len(heading_idx) else len(paras)
            out.extend(paras[heading:end])
    return out


def replace_text(
    path: str | Path,
    find: str,
    replace: str,
    out_path: str | Path | None = None,
    case_sensitive: bool = True,
    scene: str | None = None,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict:
    """Replace text inside a .fadein document, leaving all other XML untouched.

    Edits are made on paragraph text runs, so `<marks>`, style attributes,
    revision colours, and every other zip entry (embedded assets included) are
    carried through untouched. New text is not tagged as a revision — Fade In
    applies its own revision colour on the next save.

    Inline emphasis *within* an edited paragraph is flattened: the paragraph
    keeps its opening run's styling and the replacement text takes the whole
    paragraph. Everything outside the edited paragraphs is byte-identical.

    The source file is never modified: omit `out_path` and a ` (edited)` copy is
    written beside it.
    """
    src = Path(path).expanduser()
    if not find:
        raise ValueError("find string is empty")
    if not zipfile.is_zipfile(src):
        raise ValueError(f"{src.name} is not an OSF .fadein (not a zip)")

    with zipfile.ZipFile(src) as z:
        if "document.xml" not in z.namelist():
            raise ValueError(f"{src.name} is not an OSF .fadein (no document.xml)")
        xml = z.read("document.xml").decode("utf-8")

    paras = _parse_paras(xml)
    allowed = paras
    if scene:
        loaded = load_script(src)
        numbers = [sc.scene_number for sc in loaded.scenes]
        picked = _parse_scene_selector(scene, numbers)
        if not picked:
            raise ValueError(f"no scene matching {scene!r}")
        wanted = {loaded.scenes[i].scene_number for i in picked}
        allowed = _scene_windows(paras, numbers, wanted)
        if not allowed:
            raise ValueError(f"scene filter {scene!r} matched no paragraphs")

    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(find), flags)

    per_para: dict[int, tuple[Para, list[tuple[int, int]]]] = {}
    hit_count = 0
    for para in allowed:
        plain = para.plain
        spans = [m.span() for m in pattern.finditer(plain)]
        if not spans:
            continue
        if limit is not None:
            remaining = limit - hit_count
            if remaining <= 0:
                break
            spans = spans[:remaining]
        per_para[id(para)] = (para, spans)
        hit_count += len(spans)

    if hit_count == 0:
        return {
            "file": src.name,
            "replacements": 0,
            "dry_run": dry_run,
            "note": "no match; nothing written",
        }

    rebuilt: list[tuple[int, int, str]] = []
    for para, spans in per_para.values():
        plain = para.plain
        new_plain = plain
        for start, end in sorted(spans, reverse=True):
            new_plain = new_plain[:start] + replace + new_plain[end:]
        rebuilt.append((para.span[0], para.span[1], _rebuild_para(para, new_plain)))

    new_xml = xml
    for start, end, block in sorted(rebuilt, reverse=True):
        new_xml = new_xml[:start] + block + new_xml[end:]

    buf = io.BytesIO()
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(buf, "w") as zout:
        for info in zin.infolist():
            payload = (
                new_xml.encode("utf-8")
                if info.filename == "document.xml"
                else zin.read(info.filename)
            )
            zout.writestr(info, payload)
    new_bytes = buf.getvalue()

    before = load_script(src)
    scratch = Path(
        os.environ.get("TMPDIR") or "/tmp"
    ) / f".fadein-mcp-verify-{os.getpid()}-{before.fingerprint()}.fadein"
    scratch.write_bytes(new_bytes)
    try:
        after = load_script(scratch)
        checks = {
            "scenes_before": len(before.scenes),
            "scenes_after": len(after.scenes),
            "pages_before": before.pagecount,
            "pages_after": after.pagecount,
            "scenes_preserved": len(before.scenes) == len(after.scenes),
            "pagecount_preserved": before.pagecount == after.pagecount,
            "words_before": sum(_scene_words(sc) for sc in before.scenes),
            "words_after": sum(_scene_words(sc) for sc in after.scenes),
        }
        preview = _diff_snippet(before.scenes, after.scenes)
    finally:
        scratch.unlink(missing_ok=True)

    result: dict = {
        "file": src.name,
        "replacements": hit_count,
        "dry_run": dry_run,
        "checks": checks,
        "preview": preview,
    }
    if dry_run:
        return result

    dest = (
        Path(out_path).expanduser()
        if out_path
        else src.with_name(f"{src.stem} (edited){src.suffix}")
    )
    if dest.resolve() == src.resolve():
        raise ValueError(
            "refusing to overwrite the source draft; pass out_path or omit it for a copy"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(new_bytes)
    result["written"] = str(dest)
    result["bytes"] = len(new_bytes)
    return result


def _rebuild_para(para: Para, new_plain: str) -> str:
    """Put `new_plain` into the paragraph's first text run, emptying later runs.

    Paragraph-level attributes, `<marks>`, and inter-run style tags survive; the
    run structure inside the edited paragraph does not.
    """
    raw = para.raw
    matches = list(_TEXT_RE.finditer(raw))
    if not matches:
        return raw
    pieces: list[str] = []
    cursor = 0
    for idx, tm in enumerate(matches):
        pieces.append(raw[cursor : tm.start()])
        open_tag, close_tag = tm.group(1), tm.group(3)
        pieces.append(open_tag + (_escape(new_plain) if idx == 0 else "") + close_tag)
        cursor = tm.end()
    pieces.append(raw[cursor:])
    return "".join(pieces)



def _diff_snippet(a: list[ParsedScene], b: list[ParsedScene], max_scenes: int = 3) -> list[dict]:
    out = []
    for sa, sb in zip(a, b):
        pa = [p.text for p in sa.paragraphs]
        pb = [p.text for p in sb.paragraphs]
        if pa == pb:
            continue
        diff = list(difflib.unified_diff(pa, pb, lineterm="", n=0))[:12]
        out.append({"scene": sb.scene_number, "slug": sb.slugline, "diff": diff})
        if len(out) >= max_scenes:
            break
    return out


# --------------------------------------------------------------------------- #
# Conversion / listing
# --------------------------------------------------------------------------- #


def convert_script(path: str | Path, out_path: str | Path) -> dict:
    from script_cli import _write_any  # noqa: PLC0415  (toolkit CLI writers)

    src = Path(path).expanduser()
    dest = Path(out_path).expanduser()
    if dest.suffix.lower() not in CONVERSION_SUFFIXES:
        raise ValueError(f"unsupported output suffix {dest.suffix!r}")
    scenes = load_script(src).scenes
    _write_any(str(dest), scenes, title=src.stem)
    return {
        "from": src.name,
        "to": str(dest),
        "bytes": dest.stat().st_size if dest.exists() else 0,
        "scenes": len(scenes),
    }


def list_scripts(folder: str | Path | None = None, pattern: str = "*") -> dict:
    root = Path(folder).expanduser() if folder else DEFAULT_DRAFTS_DIR
    if not root.exists():
        raise FileNotFoundError(f"no such folder: {root}")
    files = [
        p
        for p in root.rglob(pattern)
        if p.suffix.lower() in DRAFT_SUFFIXES and p.is_file()
    ]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    rows = []
    for p in files[:60]:
        stat = p.stat()
        rows.append(
            {
                "name": p.name,
                "kb": round(stat.st_size / 1024),
                "modified": __import__("datetime")
                .datetime.fromtimestamp(stat.st_mtime)
                .strftime("%Y-%m-%d %H:%M"),
                "path": str(p),
            }
        )
    return {"folder": str(root), "count": len(files), "scripts": rows}
