"""
Defines `Rich` / `Typer` helpers to display content in a terminal window

Used by the the kotobase [`CLI`][kotobase.cli] to display command outputs, like
`lookup` information, and by the [`Build Pipeline`][kotobase.db.builder] to
display upstream source download and database build progress
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console, Group, RenderableType
from rich.padding import Padding
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.status import Status
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from .db.dtos import (
        AudioDTO,
        FuriganaDTO,
        JLPTGrammarDTO,
        JLPTVocabDTO,
        JMDictEntryDTO,
        JMNeDictEntryDTO,
        KanjiDTO,
        LookupResult,
        RadicalDTO,
        SentenceDTO,
    )

KOTOBASE_THEME = Theme(
    {
        "heading": "bold #F4EEE3",  # Table / Section Titles
        "primary": "#3f5468",  # Active State
        "info": "#5E83A4",  # Links / Info
        "success": "#6f9c71",
        "bold_success": "bold #6f9c71",
        "danger": "bold #C8503D",
        "warning": "#D9A441",
        "muted": "#7E7567",
    }
)

THEMED_CONSOLE = Console(theme=KOTOBASE_THEME)


def download_progress_bar() -> Progress:
    """
    Builds a customized `rich.Progress` object to display network downloads

    Used to show download progress for the kotobase databases and the upstream
    sources
    """
    columns = (
        TextColumn("[heading]{task.description}[/]"),
        TextColumn("[muted]•[/]"),
        BarColumn(
            style="warning",
            complete_style="success",
            finished_style="bold_success",
        ),
        TextColumn("[muted]•[/]"),
        DownloadColumn(),
        TextColumn("[muted]•[/]"),
        TransferSpeedColumn(),
        TextColumn("[muted]•[/]"),
        TimeRemainingColumn(
            compact=True,
            elapsed_when_finished=True,
        ),
    )
    return Progress(*columns, console=THEMED_CONSOLE)


def build_status(message: str) -> Status:
    """
    Builds a themed `rich.Status` object from to display indeterminate progress

    Used as a context manager to wrap database build step progress

    Args:
        message (str): The initial status message to display

    Returns:
        A `rich.status.Status` spinner bound to the themed console
    """
    return THEMED_CONSOLE.status(
        message,
        spinner="dots",
        spinner_style="success",
    )


def inserted_rows_table(
    row_count_dict: dict[str, int],
) -> Table:
    """
    Creates a `rich.Table` to display how many rows have been inserted into the
    database for each table during a build

    Args:
        row_count_dict (dict[str, int]): Mapping of table names to their
            inserted row count
    Returns:
        A themed `rich.Table` with the `Table` and `Inserted Rows` columns
            populated from `row_count_dict`
    """

    table = Table(
        title="Inserted Rows Per Table",
        title_style="heading",
        box=ROUNDED,
        show_lines=True,
    )
    table.add_column(header="Table Name")
    table.add_column(header="Inserted Rows")

    for name, row_count in row_count_dict.items():
        table.add_row(name, str(row_count))

    return table


# --- Rendering Helpers ---


def _human_bytes(num_bytes: int) -> str:
    """
    Format a byte count as a short human readable size

    Args:
        num_bytes (int): The size in bytes

    Returns:
        The size rounded to a sensible unit, such as `141.0 MB`
    """
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return (
                f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            )
        size /= 1024
    return f"{size:.1f} GB"


def _badges(
    *,
    common: bool = False,
    freq: int | None = None,
    jlpt: int | None = None,
) -> str:
    """
    Build a badge markup-string to show beside a headword

    Args:
        common (bool): Whether to show the common marker
        freq (int | None): Frequency rank to show, when known
        jlpt (int | None): JLPT level to show, when known

    Returns:
        A Rich markup string of the badges, empty when there are none
    """
    parts = []
    if common:
        parts.append("[warning]★ Common[/]")
    if jlpt is not None:
        parts.append(f"[info]N{jlpt}[/]")
    if freq is not None:
        parts.append(f"[muted]#{freq}[/]")
    return "  ".join(parts)


def _tags(codes: Sequence[str], labels: dict[str, str] | None = None) -> str:
    """
    Render a list of tag codes as a dim inline group

    Args:
        codes (Sequence[str]): The tag codes
        labels (dict[str, str] | None): Code to description map used to expand
            the codes when given

    Returns:
        A dim Rich markup group of the codes, empty when there are no codes
    """
    if not codes:
        return ""
    shown = [labels.get(c, c) for c in codes] if labels else list(codes)
    return f"[muted]‹{' · '.join(shown)}›[/]"  # noqa: RUF001


def _panel(body: RenderableType, title: str) -> Panel:
    """
    Wrap a renderable in the shared rounded panel style

    Args:
        body (RenderableType): The panel contents
        title (str): The panel title as Rich markup

    Returns:
        A themed `rich.panel.Panel`
    """
    return Panel(
        body,
        title=title,
        title_align="left",
        border_style="primary",
        box=ROUNDED,
        padding=(0, 1),
    )


def _section_header(title: str) -> Text:
    """
    Render a sub-section header used inside an aggregate panel

    Args:
        title (str): The Title Cased header text

    Returns:
        A `rich.text.Text` styled as a section header
    """
    return Text(title, style="primary bold")


def _stack(renderables: Sequence[RenderableType]) -> Group:
    """
    Group renderables vertically with a blank line between each

    Args:
        renderables (Sequence[RenderableType]): The renderables to stack

    Returns:
        A `rich.console.Group` of the renderables separated by blank lines
    """
    stacked: list[RenderableType] = []
    for index, renderable in enumerate(renderables):
        if index:
            stacked.append(Text(""))
        stacked.append(renderable)
    return Group(*stacked)


def _kv_table(rows: Sequence[tuple[str, str]]) -> Table:
    """
    Build a borderless two column key and value table

    Args:
        rows (Sequence[tuple[str, str]]): Title Cased key and value pairs

    Returns:
        A borderless `rich.table.Table` with the keys dimmed
    """
    table = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2, 0, 0),
    )
    table.add_column(style="muted", justify="right")
    table.add_column()
    for key, value in rows:
        table.add_row(key, value)
    return table


def render_no_results(query: str) -> None:
    """
    Print the shared empty result line

    Args:
        query (str): The query that returned nothing
    """
    THEMED_CONSOLE.print(f'[muted]No Results For "{query}"[/]')


# --- Section Builders ---


def _entry_reading(entry: JMDictEntryDTO) -> str:
    """
    Return the reading to show beside a headword

    Args:
        entry (JMDictEntryDTO): The dictionary entry

    Returns:
        The primary kana reading when the entry has a kanji headword,
            otherwise an empty string
    """
    if entry.kanji and entry.kana:
        return entry.kana[0].text
    return ""


def _entry_block(entry: JMDictEntryDTO, labels: dict[str, str]) -> Text:
    """
    Render one dictionary entry as a headword line and numbered senses

    Args:
        entry (JMDictEntryDTO): The entry to render
        labels (dict[str, str]): Tag code to description map for expansion

    Returns:
        A `rich.text.Text` block for the entry
    """
    text = Text()
    text.append(entry.headword, style="heading")
    reading = _entry_reading(entry)
    if reading:
        text.append("  ・  ")
        text.append(reading, style="info")
    badges = _badges(common=entry.is_common, freq=entry.freq_rank)
    if badges:
        text.append("  ")
        text.append_text(Text.from_markup(badges))
    for index, sense in enumerate(entry.senses, start=1):
        text.append(f"\n  {index}  ")
        tags = _tags(
            [*sense.pos, *sense.field, *sense.misc, *sense.dialect],
            labels,
        )
        if tags:
            text.append_text(Text.from_markup(tags))
            text.append(" ")
        text.append("; ".join(gloss.text for gloss in sense.glosses))
        if sense.info:
            text.append("  ")
            text.append_text(
                Text.from_markup(f"[muted]({'; '.join(sense.info)})[/]")
            )
    return text


def _dictionary_section(
    entries: Sequence[JMDictEntryDTO],
    labels: dict[str, str],
) -> RenderableType:
    """
    Render a group of dictionary entries

    Args:
        entries (Sequence[JMDictEntryDTO]): The entries to render
        labels (dict[str, str]): Tag code to description map for expansion

    Returns:
        A renderable stacking each entry block
    """
    return _stack([_entry_block(entry, labels) for entry in entries])


def _name_block(name: JMNeDictEntryDTO) -> Text:
    """
    Render one proper name with its translation blocks

    Args:
        name (JMNeDictEntryDTO): The name entry to render

    Returns:
        A `rich.text.Text` block for the name
    """
    text = Text()
    text.append(name.headword, style="heading")
    if name.kanji and name.kana:
        text.append("  ・  ")
        text.append(name.kana[0], style="info")
    for block in name.translations:
        text.append("\n  ")
        if block.name_type:
            text.append_text(
                Text.from_markup(f"[muted]{', '.join(block.name_type)}[/]  ")
            )
        text.append("; ".join(block.translations))
    return text


def _names_section(names: Sequence[JMNeDictEntryDTO]) -> RenderableType:
    """
    Render a group of proper names

    Args:
        names (Sequence[JMNeDictEntryDTO]): The names to render

    Returns:
        A renderable stacking each name block
    """
    return _stack([_name_block(name) for name in names])


def _kanji_block(kanji: KanjiDTO) -> Text:
    """
    Render one kanji as a compact fact line with meanings and readings

    Args:
        kanji (KanjiDTO): The kanji to render

    Returns:
        A `rich.text.Text` block for the kanji
    """
    text = Text()
    text.append(kanji.literal, style="heading")
    facts = []
    if kanji.stroke_count is not None:
        facts.append(f"{kanji.stroke_count} Strokes")
    if kanji.grade is not None:
        facts.append(f"Grade {kanji.grade}")
    if kanji.jlpt_tanos is not None:
        facts.append(f"N{kanji.jlpt_tanos}")
    if kanji.freq is not None:
        facts.append(f"#{kanji.freq}")
    if facts:
        text.append("  ")
        text.append(" · ".join(facts), style="muted")
    if kanji.meanings:
        text.append("\n  ")
        text.append("; ".join(kanji.meanings))
    readings = []
    if kanji.onyomi:
        readings.append("On " + "、".join(kanji.onyomi))
    if kanji.kunyomi:
        readings.append("Kun " + "、".join(kanji.kunyomi))
    if readings:
        text.append("\n  ")
        text.append("   ".join(readings), style="info")
    return text


def _kanji_section(kanji_list: Sequence[KanjiDTO]) -> RenderableType:
    """
    Render a group of kanji blocks

    Args:
        kanji_list (Sequence[KanjiDTO]): The kanji to render

    Returns:
        A renderable stacking each kanji block
    """
    return _stack([_kanji_block(kanji) for kanji in kanji_list])


def _jlpt_section(
    vocab: JLPTVocabDTO | None,
    kanji_levels: dict[str, int],
    grammar: Sequence[JLPTGrammarDTO],
) -> RenderableType:
    """
    Render the JLPT block for a word

    Args:
        vocab (JLPTVocabDTO | None): The word's vocabulary entry, when listed
        kanji_levels (dict[str, int]): JLPT level per kanji in the query
        grammar (Sequence[JLPTGrammarDTO]): Matching grammar points

    Returns:
        A renderable stacking the available JLPT lines
    """
    parts: list[RenderableType] = []
    if vocab is not None and vocab.level:
        line = Text()
        line.append("Vocabulary  ", style="muted")
        line.append(f"N{vocab.level}", style="info")
        parts.append(line)
    if kanji_levels:
        line = Text()
        line.append("Kanji  ", style="muted")
        chips = "   ".join(
            f"{char} [info]N{level}[/]" for char, level in kanji_levels.items()
        )
        line.append_text(Text.from_markup(chips))
        parts.append(line)
    for point in grammar:
        line = Text()
        line.append(f"N{point.level}  ", style="info")
        line.append(point.grammar)
        parts.append(line)
    return _stack(parts)


def _sentence_block(sentence: SentenceDTO) -> Text:
    """
    Render one example sentence with its translations

    Args:
        sentence (SentenceDTO): The sentence to render

    Returns:
        A `rich.text.Text` block for the sentence
    """
    text = Text()
    text.append(sentence.text)
    for translation in sentence.translations:
        text.append("\n  ")
        text.append(translation, style="muted")
    return text


def _sentences_section(
    sentences: Sequence[SentenceDTO],
) -> RenderableType:
    """
    Render a group of example sentences

    Args:
        sentences (Sequence[SentenceDTO]): The sentences to render

    Returns:
        A renderable stacking each sentence block
    """
    return _stack([_sentence_block(sentence) for sentence in sentences])


# --- Public Renderers ---


def render_lookup(result: LookupResult, *, with_names: bool) -> None:
    """
    Render an aggregate word lookup as one panel of sub-sections

    Args:
        result (LookupResult): The aggregated lookup result
        with_names (bool): Whether to include the proper names section
    """
    sections: list[tuple[str, RenderableType]] = []
    if result.entries:
        sections.append(
            ("Dictionary", _dictionary_section(result.entries, result.labels))
        )
    if with_names and result.names:
        sections.append(("Names", _names_section(result.names)))
    if result.kanji:
        sections.append(("Kanji", _kanji_section(result.kanji)))
    if result.has_jlpt() or result.jlpt_grammar:
        sections.append(
            (
                "JLPT",
                _jlpt_section(
                    result.jlpt_vocab,
                    result.jlpt_kanji_levels,
                    result.jlpt_grammar,
                ),
            )
        )
    if result.sentences:
        sections.append(("Sentences", _sentences_section(result.sentences)))

    if not sections:
        render_no_results(result.query)
        return

    body: list[RenderableType] = []
    for index, (title, renderable) in enumerate(sections):
        if index:
            body.append(Text(""))
        body.append(_section_header(title))
        body.append(Padding(renderable, (0, 0, 0, 2)))

    common = any(entry.is_common for entry in result.entries)
    level = result.jlpt_vocab.level if result.jlpt_vocab else None
    badges = _badges(common=common, jlpt=level)
    panel_title = f"[heading]{result.query}[/]"
    if badges:
        panel_title += f"   {badges}"
    THEMED_CONSOLE.print(_panel(Group(*body), panel_title))


def render_entries(
    entries: Sequence[JMDictEntryDTO],
    *,
    query: str,
) -> None:
    """
    Render a list of dictionary entries in a panel

    Args:
        entries (Sequence[JMDictEntryDTO]): The entries to render
        query (str): The query, shown in the panel title
    """
    if not entries:
        render_no_results(query)
        return
    title = f"[heading]{query}[/]  [muted]({len(entries)})[/]"
    THEMED_CONSOLE.print(_panel(_dictionary_section(entries, {}), title))


def render_kanji(kanji: KanjiDTO) -> None:
    """
    Render the full profile of a single kanji

    Args:
        kanji (KanjiDTO): The kanji profile to render
    """
    rows: list[tuple[str, str]] = []
    if kanji.stroke_count is not None:
        rows.append(("Strokes", str(kanji.stroke_count)))
    if kanji.grade is not None:
        rows.append(("Grade", str(kanji.grade)))
    if kanji.freq is not None:
        rows.append(("Frequency", f"#{kanji.freq}"))
    jlpt = []
    if kanji.jlpt_tanos is not None:
        jlpt.append(f"N{kanji.jlpt_tanos} (Tanos)")
    if kanji.jlpt_old is not None:
        jlpt.append(f"Level {kanji.jlpt_old} (Old)")
    if jlpt:
        rows.append(("JLPT", ", ".join(jlpt)))
    if kanji.radicals:
        rows.append(("Radicals", " ".join(kanji.radicals)))
    for label, values in (
        ("On", kanji.onyomi),
        ("Kun", kanji.kunyomi),
        ("Nanori", kanji.nanori),
        ("Pinyin", kanji.pinyin),
        ("Korean", kanji.korean),
    ):
        if values:
            rows.append((label, "、".join(values)))
    skip = kanji.query_codes.get("skip")
    if skip:
        rows.append(("SKIP", ", ".join(skip)))
    four_corner = kanji.query_codes.get("four_corner")
    if four_corner:
        rows.append(("Four Corner", ", ".join(four_corner)))
    if kanji.dic_refs:
        refs = " · ".join(
            f"{name} {value}" for name, value in kanji.dic_refs.items()
        )
        rows.append(("References", refs))
    if kanji.variants:
        variants = " · ".join(
            f"{variant['type']} {variant['value']}"
            for variant in kanji.variants
        )
        rows.append(("Variants", variants))
    if kanji.has_stroke_order:
        rows.append(("Stroke Order", "Available"))

    title = f"[heading]{kanji.literal}[/]"
    if kanji.meanings:
        title += f"   [info]{'; '.join(kanji.meanings)}[/]"
    THEMED_CONSOLE.print(_panel(_kv_table(rows), title))


def render_word_jlpt(result: LookupResult) -> None:
    """
    Render the JLPT view for a word and its kanji

    Args:
        result (LookupResult): A lookup result carrying the JLPT data
    """
    if not (result.has_jlpt() or result.jlpt_grammar):
        render_no_results(result.query)
        return
    body = _jlpt_section(
        result.jlpt_vocab,
        result.jlpt_kanji_levels,
        result.jlpt_grammar,
    )
    THEMED_CONSOLE.print(_panel(body, f"[heading]{result.query}[/]   JLPT"))


def render_kanji_table(kanji: Sequence[KanjiDTO], *, title: str) -> None:
    """
    Render a table of kanji search results

    Args:
        kanji (Sequence[KanjiDTO]): The matching kanji
        title (str): A Title Cased description of the search
    """
    if not kanji:
        render_no_results(title)
        return
    table = Table(
        title=f"{title}  ({len(kanji)})",
        title_style="heading",
        title_justify="left",
        box=ROUNDED,
        border_style="primary",
        header_style="heading",
    )
    table.add_column("Kanji", justify="center")
    table.add_column("Strokes", justify="right")
    table.add_column("Grade", justify="right")
    table.add_column("Freq", justify="right")
    table.add_column("JLPT", justify="center")
    table.add_column("Meanings")
    for entry in kanji:
        table.add_row(
            Text(entry.literal, style="heading"),
            str(entry.stroke_count) if entry.stroke_count else "",
            str(entry.grade) if entry.grade else "",
            str(entry.freq) if entry.freq else "",
            f"N{entry.jlpt_tanos}" if entry.jlpt_tanos else "",
            "; ".join(entry.meanings[:3]),
        )
    THEMED_CONSOLE.print(table)


def render_radicals(radicals: Sequence[RadicalDTO]) -> None:
    """
    Render every search radical grouped by stroke count

    Args:
        radicals (Sequence[RadicalDTO]): The radicals to render
    """
    if not radicals:
        render_no_results("Radicals")
        return
    groups: dict[int | None, list[str]] = {}
    for radical in radicals:
        groups.setdefault(radical.stroke_count, []).append(radical.radical)
    parts: list[RenderableType] = []
    ordered = sorted(groups, key=lambda count: (count is None, count or 0))
    for count in ordered:
        label = f"{count} Strokes" if count is not None else "Unknown"
        parts.append(_section_header(label))
        grid = Columns(
            [Text(char) for char in groups[count]],
            padding=(0, 2),
        )
        parts.append(Padding(grid, (0, 0, 1, 2)))
    THEMED_CONSOLE.print(_panel(Group(*parts), "[heading]Radicals[/]"))


def render_names(names: Sequence[JMNeDictEntryDTO]) -> None:
    """
    Render a list of proper names in a panel

    Args:
        names (Sequence[JMNeDictEntryDTO]): The names to render
    """
    if not names:
        render_no_results("Names")
        return
    title = f"[heading]Names[/]  [muted]({len(names)})[/]"
    THEMED_CONSOLE.print(_panel(_names_section(names), title))


def render_sentences(
    sentences: Sequence[SentenceDTO],
    *,
    query: str,
) -> None:
    """
    Render example sentences in a panel

    Args:
        sentences (Sequence[SentenceDTO]): The sentences to render
        query (str): The query, used in the empty result message
    """
    if not sentences:
        render_no_results(query)
        return
    title = f"[heading]Sentences[/]  [muted]({len(sentences)})[/]"
    THEMED_CONSOLE.print(_panel(_sentences_section(sentences), title))


def render_furigana(items: Sequence[FuriganaDTO]) -> None:
    """
    Render furigana segmentations in a panel

    Args:
        items (Sequence[FuriganaDTO]): The furigana rows to render
    """
    if not items:
        render_no_results("Furigana")
        return
    parts: list[RenderableType] = []
    for item in items:
        line = Text()
        for segment in item.segments:
            line.append(str(segment.get("ruby", "")), style="heading")
            rt = segment.get("rt")
            if rt:
                line.append(f"({rt})", style="info")
        line.append("   ")
        line.append(item.reading, style="muted")
        parts.append(line)
    THEMED_CONSOLE.print(_panel(_stack(parts), "[heading]Furigana[/]"))


def render_jlpt_list(items: Sequence[Any], *, kind: str, level: int) -> None:
    """
    Render a full Tanos JLPT study list as a table

    Args:
        items (Sequence[Any]): The vocab, kanji or grammar items
        kind (str): One of `vocab`, `kanji` or `grammar`
        level (int): The JLPT level
    """
    if not items:
        render_no_results(f"N{level} {kind.capitalize()}")
        return
    table = Table(
        title=f"N{level} {kind.capitalize()}  ({len(items)})",
        title_style="heading",
        title_justify="left",
        box=ROUNDED,
        border_style="primary",
        header_style="heading",
    )
    if kind == "vocab":
        table.add_column("Word")
        table.add_column("Reading")
        table.add_column("Meaning")
        for item in items:
            table.add_row(
                item.word or "",
                item.reading or "",
                item.meaning or "",
            )
    elif kind == "kanji":
        table.add_column("Kanji", justify="center")
        table.add_column("On")
        table.add_column("Kun")
        table.add_column("Meaning")
        for item in items:
            table.add_row(
                item.kanji,
                item.on_yomi or "",
                item.kun_yomi or "",
                item.meaning or "",
            )
    else:
        table.add_column("Grammar")
        table.add_column("Formation")
        table.add_column("Examples")
        for item in items:
            table.add_row(
                item.grammar,
                item.formation or "",
                "; ".join(item.examples),
            )
    THEMED_CONSOLE.print(table)


def render_db_info(info: dict[str, str]) -> None:
    """
    Render database build metadata in a panel

    Args:
        info (dict[str, str]): The `db_meta` key and value pairs
    """
    rows: list[tuple[str, str]] = []
    nice = {
        "schema_version": "Schema Version",
        "build_date": "Build Date",
        "build_seconds": "Build Seconds",
        "size_mb": "Size (MB)",
    }
    for key, label in nice.items():
        if key in info:
            rows.append((label, info[key]))
    for key in sorted(k for k in info if k.startswith("source.")):
        rows.append((key.removeprefix("source."), info[key]))
    THEMED_CONSOLE.print(_panel(_kv_table(rows), "[heading]Database Info[/]"))


def render_cache_path(path: Path) -> None:
    """
    Render the cache directory path

    Args:
        path (Path): The cache directory path
    """
    THEMED_CONSOLE.print(f"[info]{path}[/]")


def render_cache_size(sizes: dict[str, int]) -> None:
    """
    Render a breakdown of the cache disk usage

    Args:
        sizes (dict[str, int]): Title Cased label to byte count pairs
    """
    table = Table(
        box=None,
        show_header=False,
        pad_edge=False,
        padding=(0, 2, 0, 0),
    )
    table.add_column(style="muted", justify="right")
    table.add_column()
    total = 0
    for label, num_bytes in sizes.items():
        table.add_row(label, _human_bytes(num_bytes))
        total += num_bytes
    table.add_row("", "")
    table.add_row(
        Text("Total", style="heading"),
        Text(_human_bytes(total), style="heading"),
    )
    THEMED_CONSOLE.print(_panel(table, "[heading]Cache Size[/]"))


def render_cache_cleared(removed: Sequence[Path], freed: int) -> None:
    """
    Render the result of clearing the cache

    Args:
        removed (Sequence[Path]): The paths that were removed
        freed (int): The number of bytes freed
    """
    if not removed:
        THEMED_CONSOLE.print("[muted]Nothing To Clear[/]")
        return
    body = Text()
    for index, path in enumerate(removed):
        if index:
            body.append("\n")
        body.append("Removed  ", style="success")
        body.append(str(path))
    body.append("\n\n")
    body.append("Freed  ", style="heading")
    body.append(_human_bytes(freed), style="heading")
    THEMED_CONSOLE.print(_panel(body, "[heading]Cache Cleared[/]"))


def render_audio(key: str, clips: Sequence[AudioDTO]) -> None:
    """
    Render the audio clips available for a key

    Args:
        key (str): The looked-up key
        clips (Sequence[AudioDTO]): The clips to list
    """
    table = Table(
        title=f"[heading]{key}[/]  Audio  [muted]({len(clips)})[/]",
        title_style="heading",
        title_justify="left",
        box=ROUNDED,
        border_style="primary",
        header_style="heading",
    )
    table.add_column("Reading")
    table.add_column("Format")
    table.add_column("Source")
    table.add_column("License")
    for clip in clips:
        table.add_row(
            clip.reading or "",
            clip.fmt or "",
            clip.source,
            clip.license or "",
        )
    THEMED_CONSOLE.print(table)


def render_audio_saved(paths: Sequence[Path]) -> None:
    """
    Render the result of saving audio clips to disk

    Args:
        paths (Sequence[Path]): The written audio file paths
    """
    if not paths:
        THEMED_CONSOLE.print("[muted]No Audio To Save[/]")
        return
    body = Text()
    for index, path in enumerate(paths):
        if index:
            body.append("\n")
        body.append("Saved  ", style="success")
        body.append(str(path))
    title = f"[heading]Audio Saved[/]  [muted]({len(paths)})[/]"
    THEMED_CONSOLE.print(_panel(body, title))
