"""
Defines the extractors that turn each upstream source into database rows

abstract: Sources To Rows
    - Every extractor is a generator that yields
      [`DatabaseRow`][kotobase.db.builder.extractors.DatabaseRow] pairs, where
      the first item is a table name and the second is a row (dict) whose keys
      match that table's columns in the [`Schema`][kotobase.db.models]

    - Extractors know a single source format and nothing about `SQLite`. The
      [`Builder`][kotobase.db.builder.build.Builder] knows how to insert rows
      and nothing about parsing. They meet only at the `DatabaseRow` tuple and
      at the arguments that each extractor might take

info: Data Flow Map
    - `JMdict.gz` -> `extract_jmdict` -> Fills (`jmdict_entry`, `jmdict_kanji`,
      `jmdict_kana`, `jmdict_sense`, `jmdict_gloss`, and `tag`)

    - `JMnedict.gz` -> `extract_jmnedict` -> Fills (`jmnedict_entry`,
      `jmnedict_kanji`, `jmnedict_kana`, `jmnedict_translation`,
      `jmnedict_gloss`, and `tag`)

    - `KanjiDic2.gz` -> `extract_kanjidic` -> Fills (`kanji`, `kanji_reading`,
      `kanji_meaning`, `kanji_nanori`, `kanji_dic_ref`, `kanji_query_code`,
      `kanji_variant`, and `kanji_codepoint`)

    - `kradzip` -> `extract_krad` -> Fills (`radical` and `kanji_radical`)

    - `JmdictFurigana` -> `extract_furigana` -> Fills (`furigana`)

    - `KanjiVG.gz` -> `extract_kanjivg` -> Fills (`kanji_strokes`)

    - `Tanos JLPT JSON` -> `extract_jlpt` -> Fills (`jlpt_vocab`, `jlpt_kanji`,
      and `jlpt_grammar`)

    - `Tatoeba bz2/tar` -> `extract_tatoeba` -> Fills (`sentence` and
      `sentence_link`)

    - `Kanji alive zip` -> `extract_audio` -> Fills (`audio`), which lives in
      the separate audio pack database rather than the core one
"""

from __future__ import annotations

import bz2
import csv
import gzip
import json
import logging
import re
import tarfile
import zipfile
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

from lxml import etree

from ...exceptions import MalformedSourceError, SourceExtractionError
from . import config

# --- Module Logger ---

LOGGER = logging.getLogger(__name__)

# --- Extractor Contract ---

DatabaseRow: TypeAlias = tuple[str, dict[str, Any]]
"""
A single database row produced by an extractor

A tuple whose first item is the target table name and whose second item is a
dictionary mapping that table's column names to their row values
"""

ExtractorFunction: TypeAlias = Callable[..., Iterable[DatabaseRow]]
"""
The signature of an extractor function

Every extractor is a generator that yields
[`DatabaseRow`][kotobase.db.builder.extractors.DatabaseRow] pairs, where
the first item is a table name and the second is a row (dict) whose keys
match that table's columns in the [`Schema`][kotobase.db.models]
"""


@dataclass(frozen=True, slots=True)
class Extractor:
    """
    Represents a data extractor for a single usptream source

    info: Attribute Breakdown
        - `name` &rarr; A string used to identify the extractor's `run`
          output in build logs

        - `tables` &rarr; The database table names which this extractor yields
          rows for, always a subset of the [`Schema`][kotobase.db.models]

        - `run` &rarr; The function which parses the upstream source data and
          yields the database rows

    Attributes:
        name (str): Short identifier used in build logs
        tables (tuple[str, ...]): The tables this extractor fills, which makes
            the data flow readable from the registry alone
        run (ExtractorFunction): Callable that takes an arbitrary number of
            arguments and yields
            [`DatabaseRow`][kotobase.db.builder.extractors.DatabaseRow] pairs
    """

    name: str
    tables: tuple[str, ...]
    run: ExtractorFunction


# --- Shared Parsing Helpers ---


def _to_json(value: Any) -> str:
    """
    Serialize a value to compact `JSON` text for a `JSON` column using
    `json.dumps`

    Japanese text is kept verbatim rather than escaped to `\\uXXXX` so
    that the stored columns stay readable (`ensure_ascii=False`)

    Args:
        value (Any): Any `JSON` serializable value

    Returns:
        The `JSON` encoded value with non ASCII characters kept verbatim
    """
    return json.dumps(value, ensure_ascii=False)


def _texts(elements: Iterable[etree._Element]) -> list[str]:
    """
    Collect the texts of a collection of lxml etree elements, skipping any
    elements that have no text
    Args:
        elements (Iterable[etree._Element]): lxlm etree elements to read

    Returns:
        The text of every element that has text, in order
    """
    return [element.text for element in elements if element.text is not None]


def _optional_int(value: str | None) -> int | None:
    """
    Convert optional text to an integer, retuning `None` when the value can't
    be parsed or if `None` is passed

    Args:
        value (str | None): Text to convert, or None

    Returns:
        The integer value, or None when the text is missing or not numeric
    """
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _require_int(value: str | None) -> int:
    """
    Parse integer text that a well formed upstream source should always
    provide, raising when if `None` is passed or the value can't be parsed

    Args:
        value (str | None): The text to parse

    Returns:
        The parsed integer

    Raises:
        MalformedSourceError: If the text is missing or can't be parsed
    """
    if value is None:
        raise MalformedSourceError("Missing Required Integer Field")
    try:
        return int(value)
    except ValueError as e:
        raise MalformedSourceError(
            f"Required Integer Field '{value}' Can't Be Parsed"
        ) from e


def stream_elements(
    path: Path,
    tag: str,
    *,
    resolve_entities: bool = True,
) -> Iterator[etree._Element]:
    """
    Stream one tag from a gzipped XML file with flat memory usage

    info: How It Works
        - `iterparse` runs on `libxml2` and fires once per finished element,
          so the whole document is never built into a tree

        - After each element is yielded, it is cleared and its
          already processed previous siblings are deleted, which is what keeps
          memory usage flat across a multi-hundred megabyte file

        - The element is still fully populated while the caller holds it, so
          all reads must happen inside the loop body before the next iteration

    Args:
        path (Path): Path of the gzipped XML file
        tag (str): The element tag to emit, such as `entry` or `character`
        resolve_entities (bool): When True, expand XML entities such as `&n;`
            into their description text while parsing

    Yields:
        Each finished element of the requested tag, cleared once the caller
            moves on
    """
    with gzip.open(path, "rb") as handle:
        context = etree.iterparse(
            handle,
            events=("end",),
            tag=tag,
            resolve_entities=resolve_entities,
        )
        for _event, element in context:
            yield element
            # Drop this element and every sibling already processed so the
            # parser does not accumulate the whole document in memory
            element.clear()
            parent = element.getparent()
            while parent is not None and element.getprevious() is not None:
                del parent[0]


class TagResolver:
    """
    Recovers stable tag codes from `JMdict` and `JMnedict` entity descriptions

    info: Document Type Definition
        - `JMdict` writes tags as XML entities such as `<pos>&n;</pos>`,
          and the XML's `DTD` (Document Type Definition) at the top of the
          file maps each code to a description, for example `n` to
          `noun (common) (futsuumeishi)`

        - The file is parsed with entities resolved, so an element arrives
          already expanded to the long description

        - In order to store the short, stable code of the tag, but keep the
          information that the long descriptions provide, this resolver
          reverses the `DTD` map so that the long description can be turned
          back into the code, while the description is emitted into the `tag`
          table of the database

    Attributes:
        code_to_desc (dict[str, str]): Mapping of each tag code to its
            description
    """

    _ENTITY_RE = re.compile(r'<!ENTITY\s+(\S+)\s+"([^"]*)">')
    """
    Matches a `DTD` entity declaration, capturing its code and its description
    """

    def __init__(self, code_to_desc: dict[str, str]) -> None:
        """
        Build a resolver from a code to description mapping

        Args:
            code_to_desc (dict[str, str]): Mapping of tag code to description
        """
        self.code_to_desc = code_to_desc
        self._desc_to_code = {
            description: code for code, description in code_to_desc.items()
        }

    @classmethod
    def from_dtd(cls, path: Path, *, stop: str) -> TagResolver:
        """
        Read the `DTD` (Document Type Definition) entity table
        from the top of a gzipped XML file

        The scan stops at the first line containing the `stop` sentinel, which
        is the start of the document body

        Args:
            path (Path): Path of the gzipped XML file
            stop (str): Substring that marks the end of the DTD, such as
                `<JMdict` for JMdict or `]>` for JMnedict

        Returns:
            A resolver populated from the file's entity table
        """
        entities: dict[str, str] = {}
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                match = cls._ENTITY_RE.search(line)
                if match:
                    entities[match.group(1)] = match.group(2)
                if stop in line:
                    break
        return cls(entities)

    def codes(self, elements: Iterable[etree._Element]) -> list[str]:
        """
        Map resolved element texts back to their stable codes

        An element whose text is not a known description is kept verbatim,
        which leaves any non entity value untouched

        Args:
            elements (Iterable[etree._Element]): Elements whose text is a
                resolved entity description

        Returns:
            The stable code for each element, in order
        """
        result: list[str] = []
        for element in elements:
            text = element.text
            if text is None:
                continue
            result.append(self._desc_to_code.get(text, text))
        return result

    def tag_rows(
        self,
        elements: Iterable[etree._Element],
        category: str,
    ) -> Iterator[DatabaseRow]:
        """
        Emit `tag` rows for every element that resolves to a known code

        This is the additional extractor for the `tags` table of the database,
        shared by both `JMDict` and `JMNedict`

        Args:
            elements (Iterable[etree._Element]): Elements whose text is a
                resolved entity description
            category (str): The tag category to record, such as `pos` or `misc`

        Yields:
            One `tag` row per element with a known code
        """
        for element in elements:
            text = element.text
            if text is None:
                continue
            code = self._desc_to_code.get(text)
            if code is not None:
                yield (
                    "tag",
                    {
                        "code": code,
                        "category": category,
                        "description": text,
                    },
                )


def _read_tsv_bz2(path: Path) -> Iterator[list[str]]:
    """
    Stream a `bzip2` compressed `TSV` file as split columns

    Args:
        path (Path): Path of the `.tsv.bz2` file

    Yields:
        The tab separated columns of each line
    """
    with bz2.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield line.rstrip("\n").split("\t")


def _read_tar_bz2_member(path: Path, suffix: str) -> Iterator[list[str]]:
    """
    Stream the first member of a bzip2 tar archive that matches `suffix` as
    split columns

    Args:
        path (Path): Path of the `.tar.bz2` archive
        suffix (str): Filename suffix that selects the member to read

    Yields:
        The tab separated columns of each line in the member

    Raises:
        FileNotFoundError: If no member matches the suffix or has no data
    """
    with tarfile.open(path, "r:bz2") as archive:
        member = next(
            (m for m in archive.getmembers() if m.name.endswith(suffix)),
            None,
        )
        if member is None:
            raise SourceExtractionError(f"No Member Ending In '{suffix!r}'")
        handle = archive.extractfile(member)
        if handle is None:
            raise SourceExtractionError(
                f"No Data Found For Member With Suffix '{suffix}'"
            )
        for raw in handle:
            yield raw.decode("utf-8").rstrip("\n").split("\t")


# --- JMdict ---

_NF_RE = re.compile(r"nf(\d+)")
"""
Matches a JMdict `nfXX` corpus frequency band code and captures the band
number, where a lower number is more frequent
"""

_COMMON_PRIORITY = frozenset({"news1", "ichi1", "spec1", "spec2", "gai1"})
"""
Priority codes that mark a `JMdict` written or read form as `common` when any
one of them is present
"""

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
"""
The fully qualified `xml:lang` attribute name, used to read the language of
gloss and source language elements
"""


def _priority_common(codes: list[str]) -> bool:
    """
    Decides whether a list of priority codes marks a form as `common`

    Args:
        codes (list[str]): Priority codes from a kanji or reading element

    Returns:
        True when any code is one of the common priority markers
    """
    return any(code in _COMMON_PRIORITY for code in codes)


def _freq_rank(codes: list[str]) -> int | None:
    """
    Derive a frequency rank from a list of priority codes

    `JMdict` encodes corpus frequency as `nfXX` bands, where a lower number is
    more frequent. The best band across all of an entry's forms is used

    Args:
        codes (list[str]): Priority codes from all forms of an entry

    Returns:
        The smallest `nfXX` band as an integer, or None when no band is present
    """
    bands = [
        int(match.group(1))
        for code in codes
        if (match := _NF_RE.fullmatch(code))
    ]
    return min(bands) if bands else None


def extract_jmdict(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `JMdict` into database rows

    info: File Format
        - A gzipped XML file with a root `<JMdict>` element and one `<entry>`
          per dictionary entry, streamed one entry at a time

        - `<ent_seq>` holds the unique sequence number used as the entry id

        - Each written form is a `<k_ele>` with the kanji spelling in `<keb>`,
          spelling-info tags in `<ke_inf>` and priority codes in `<ke_pri>`

        - Each reading is an `<r_ele>` with the kana in `<reb>`, info tags in
          `<re_inf>`, priority codes in `<re_pri>`, optional `<re_restr>`
          entries that limit the reading to specific `<keb>`, and a
          `<re_nokanji/>` flag for readings that pair with no kanji

        - Each `<sense>` is one meaning, holding part of speech `<pos>`, field
          of use `<field>`, register `<misc>` (slang, vulgar, ...), `<dial>`
          dialect, free notes `<s_inf>`, `<xref>` and `<ant>` cross
          references, `<stagk>` and `<stagr>` form restrictions, loanword
          origin `<lsource>` and the translations in `<gloss>`

        - The tag elements (`<pos>`, `<ke_inf>`, `<misc>`, ...) are written as
          XML entities such as `&n;` defined in the DTD header, which
          [`TagResolver`][kotobase.db.builder.extractors.TagResolver] turns
          back into stable codes

        - A `<sense>` with no `<pos>` reuses the previous sense's, so the last
          seen value is carried forward

        - Priority codes include corpus frequency bands written as `nfXX`,
          where a lower number is more frequent

    Args:
        path (Path): Path of the gzipped JMdict XML

    Yields:
        Rows for the `jmdict_entry`, `jmdict_kanji`, `jmdict_kana`,
            `jmdict_sense`, `jmdict_gloss` and `tag` tables
    """
    tags = TagResolver.from_dtd(path, stop="<JMdict")
    sense_id = 0

    for entry in stream_elements(path, "entry", resolve_entities=True):
        seq = _require_int(entry.findtext("ent_seq"))
        kanji_forms = entry.findall("k_ele")
        kana_forms = entry.findall("r_ele")
        senses = entry.findall("sense")

        # An entry is common, and gets a frequency rank, based on the priority
        # markers pooled across all of its written and read forms
        all_priority: list[str] = []
        for form in kanji_forms:
            all_priority += _texts(form.findall("ke_pri"))
        for form in kana_forms:
            all_priority += _texts(form.findall("re_pri"))

        yield (
            "jmdict_entry",
            {
                "id": seq,
                "is_common": _priority_common(all_priority),
                "freq_rank": _freq_rank(all_priority),
            },
        )

        for position, form in enumerate(kanji_forms):
            priority = _texts(form.findall("ke_pri"))
            yield (
                "jmdict_kanji",
                {
                    "entry_id": seq,
                    "position": position,
                    "text": form.findtext("keb"),
                    "is_common": _priority_common(priority),
                    "info": _to_json(tags.codes(form.findall("ke_inf"))),
                    "priority": _to_json(priority),
                },
            )
            yield from tags.tag_rows(form.findall("ke_inf"), "ke_inf")

        for position, form in enumerate(kana_forms):
            priority = _texts(form.findall("re_pri"))
            restrictions = _texts(form.findall("re_restr"))
            yield (
                "jmdict_kana",
                {
                    "entry_id": seq,
                    "position": position,
                    "text": form.findtext("reb"),
                    "is_common": _priority_common(priority),
                    "no_kanji": form.find("re_nokanji") is not None,
                    "restrictions": _to_json(restrictions),
                    "info": _to_json(tags.codes(form.findall("re_inf"))),
                    "priority": _to_json(priority),
                },
            )
            yield from tags.tag_rows(form.findall("re_inf"), "re_inf")

        # JMdict omits the part of speech on a sense when it repeats the
        # previous sense, so the last non empty value is carried forward
        previous_pos: list[str] = []
        for position, sense in enumerate(senses):
            sense_id += 1
            pos = tags.codes(sense.findall("pos"))
            if pos:
                previous_pos = pos
            else:
                pos = previous_pos
            lsource = [
                {
                    "lang": e.get(_XML_LANG, "eng"),
                    "type": e.get("ls_type"),
                    "wasei": e.get("ls_wasei") == "y",
                    "text": e.text,
                }
                for e in sense.findall("lsource")
            ]
            yield (
                "jmdict_sense",
                {
                    "id": sense_id,
                    "entry_id": seq,
                    "position": position,
                    "pos": _to_json(pos),
                    "field": _to_json(tags.codes(sense.findall("field"))),
                    "misc": _to_json(tags.codes(sense.findall("misc"))),
                    "dialect": _to_json(tags.codes(sense.findall("dial"))),
                    "info": _to_json([e.text for e in sense.findall("s_inf")]),
                    "xref": _to_json([e.text for e in sense.findall("xref")]),
                    "antonym": _to_json(
                        [e.text for e in sense.findall("ant")]
                    ),
                    "applies_to_kanji": _to_json(
                        [e.text for e in sense.findall("stagk")]
                    ),
                    "applies_to_kana": _to_json(
                        [e.text for e in sense.findall("stagr")]
                    ),
                    "lsource": _to_json(lsource),
                },
            )
            yield from tags.tag_rows(sense.findall("pos"), "pos")
            yield from tags.tag_rows(sense.findall("field"), "field")
            yield from tags.tag_rows(sense.findall("misc"), "misc")
            yield from tags.tag_rows(sense.findall("dial"), "dialect")
            for gloss_position, gloss in enumerate(sense.findall("gloss")):
                yield (
                    "jmdict_gloss",
                    {
                        "sense_id": sense_id,
                        "position": gloss_position,
                        "lang": gloss.get(_XML_LANG, "eng"),
                        "text": gloss.text,
                        "gender": gloss.get("g_gend"),
                        "gtype": gloss.get("g_type"),
                    },
                )


# --- JMnedict ---


def extract_jmnedict(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `JMnedict` into database rows

    info: File Format
        - A gzipped XML file with the same shape as `JMdict` but for proper
          names, streamed one `<entry>` at a time

        - `<ent_seq>` holds the unique sequence number used as the entry id

        - Written forms are `<k_ele>` with the spelling in `<keb>`, readings
          are `<r_ele>` with the kana in `<reb>`

        - Each `<trans>` block is one name reading with its type in
          `<name_type>` (surname, place, given, ...), `<xref>` cross
          references and the actual translated names in `<trans_det>`

        - `<name_type>` is written as an XML entity defined in the DTD header,
          which [`TagResolver`][kotobase.db.builder.extractors.TagResolver]
          turns back into a stable code

    Args:
        path (Path): Path of the gzipped JMnedict XML

    Yields:
        Rows for the `jmnedict_entry`, `jmnedict_kanji`, `jmnedict_kana`,
            `jmnedict_translation`, `jmnedict_gloss` and `tag` tables
    """
    tags = TagResolver.from_dtd(path, stop="]>")
    translation_id = 0

    for entry in stream_elements(path, "entry", resolve_entities=True):
        seq = _require_int(entry.findtext("ent_seq"))
        yield ("jmnedict_entry", {"id": seq})

        for position, form in enumerate(entry.findall("k_ele")):
            yield (
                "jmnedict_kanji",
                {
                    "entry_id": seq,
                    "position": position,
                    "text": form.findtext("keb"),
                },
            )

        for position, form in enumerate(entry.findall("r_ele")):
            yield (
                "jmnedict_kana",
                {
                    "entry_id": seq,
                    "position": position,
                    "text": form.findtext("reb"),
                },
            )

        for position, trans in enumerate(entry.findall("trans")):
            translation_id += 1
            yield (
                "jmnedict_translation",
                {
                    "id": translation_id,
                    "entry_id": seq,
                    "position": position,
                    "name_type": _to_json(
                        tags.codes(trans.findall("name_type"))
                    ),
                    "xref": _to_json([e.text for e in trans.findall("xref")]),
                },
            )
            yield from tags.tag_rows(trans.findall("name_type"), "name_type")
            for gloss_position, detail in enumerate(
                trans.findall("trans_det")
            ):
                yield (
                    "jmnedict_gloss",
                    {
                        "translation_id": translation_id,
                        "position": gloss_position,
                        "lang": "eng",
                        "text": detail.text,
                    },
                )


# --- KanjiDic2 ---


def extract_kanjidic(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `KanjiDic2` into database rows

    A single character fans out across the kanji table and its seven detail
    tables

    info: File Format
        - A gzipped XML file with a root `<kanjidic2>` element and one
          `<character>` per kanji, streamed one at a time. Unlike `JMdict` it
          uses no XML entities, so values are read directly

        - `<literal>` holds the kanji character itself

        - `<codepoint>` lists `<cp_value cp_type=...>` encodings (Unicode, JIS)

        - `<radical>` lists `<rad_value rad_type=...>` radical numbers, where
          `classical` and `nelson_c` are kept

        - `<misc>` holds the school `<grade>`, one or more `<stroke_count>`
          values (the first is accepted, the rest are common miscounts),
          newspaper `<freq>`, the old `<jlpt>` level and `<variant>` forms

        - `<dic_number>` lists `<dic_ref dr_type=...>` references into print
          dictionaries, with optional `m_vol` and `m_page` attributes

        - `<query_code>` lists `<q_code qc_type=...>` lookup codes such as
          SKIP, where a `skip_misclass` attribute flags common
          misclassifications

        - `<reading_meaning>` groups readings and meanings in `<rmgroup>`
          blocks, where `<reading r_type=...>` covers on, kun, pinyin and
          korean, and `<meaning m_lang=...>` defaults to English, while
          `<nanori>` name readings sit outside the groups

    Args:
        path (Path): Path of the gzipped KanjiDic2 XML

    Yields:
        Rows for the `kanji`, `kanji_reading`, `kanji_meaning`, `kanji_nanori`,
            `kanji_dic_ref`, `kanji_query_code`, `kanji_variant` and
            `kanji_codepoint` tables
    """
    for char in stream_elements(path, "character"):
        literal = char.findtext("literal")
        misc = char.find("misc")

        # A character may list more than one stroke count, the first is the
        # accepted value and the rest are common miscounts kept for reference.
        strokes = [
            _optional_int(s.text)
            for s in (misc.findall("stroke_count") if misc is not None else [])
        ]
        strokes = [s for s in strokes if s is not None]

        rad_classical = None
        rad_nelson = None
        radical = char.find("radical")
        if radical is not None:
            for value in radical.findall("rad_value"):
                if value.get("rad_type") == "classical":
                    rad_classical = _optional_int(value.text)
                elif value.get("rad_type") == "nelson_c":
                    rad_nelson = _optional_int(value.text)

        yield (
            "kanji",
            {
                "literal": literal,
                "grade": _optional_int(
                    misc.findtext("grade") if misc is not None else None
                ),
                "stroke_count": strokes[0] if strokes else None,
                "freq": _optional_int(
                    misc.findtext("freq") if misc is not None else None
                ),
                "jlpt_old": _optional_int(
                    misc.findtext("jlpt") if misc is not None else None
                ),
                "rad_classical": rad_classical,
                "rad_nelson": rad_nelson,
                "stroke_miscounts": _to_json(strokes[1:]),
            },
        )

        codepoint = char.find("codepoint")
        if codepoint is not None:
            for value in codepoint.findall("cp_value"):
                yield (
                    "kanji_codepoint",
                    {
                        "literal": literal,
                        "type": value.get("cp_type"),
                        "value": value.text,
                    },
                )

        if misc is not None:
            for value in misc.findall("variant"):
                yield (
                    "kanji_variant",
                    {
                        "literal": literal,
                        "type": value.get("var_type"),
                        "value": value.text,
                    },
                )

        dic_number = char.find("dic_number")
        if dic_number is not None:
            for ref in dic_number.findall("dic_ref"):
                extra = None
                if ref.get("m_vol") or ref.get("m_page"):
                    extra = _to_json(
                        {"vol": ref.get("m_vol"), "page": ref.get("m_page")}
                    )
                yield (
                    "kanji_dic_ref",
                    {
                        "literal": literal,
                        "type": ref.get("dr_type"),
                        "value": ref.text,
                        "extra": extra,
                    },
                )

        query_code = char.find("query_code")
        if query_code is not None:
            for code in query_code.findall("q_code"):
                yield (
                    "kanji_query_code",
                    {
                        "literal": literal,
                        "type": code.get("qc_type"),
                        "value": code.text,
                        "skip_misclass": code.get("skip_misclass"),
                    },
                )

        reading_meaning = char.find("reading_meaning")
        if reading_meaning is not None:
            reading_pos = 0
            meaning_pos = 0
            for group in reading_meaning.findall("rmgroup"):
                for reading in group.findall("reading"):
                    yield (
                        "kanji_reading",
                        {
                            "literal": literal,
                            "type": reading.get("r_type"),
                            "value": reading.text,
                            "position": reading_pos,
                        },
                    )
                    reading_pos += 1
                for meaning in group.findall("meaning"):
                    yield (
                        "kanji_meaning",
                        {
                            "literal": literal,
                            "lang": meaning.get("m_lang", "en"),
                            "value": meaning.text,
                            "position": meaning_pos,
                        },
                    )
                    meaning_pos += 1
            for position, nanori in enumerate(
                reading_meaning.findall("nanori")
            ):
                yield (
                    "kanji_nanori",
                    {
                        "literal": literal,
                        "value": nanori.text,
                        "position": position,
                    },
                )


# --- KRADFILE and RADKFILE ---

_KRAD_MEMBERS = ("kradfile", "kradfile2")
"""
`KRADFILE` member names inside the kradzip archive, which list the radical
components that make up each kanji
"""

_RADK_MEMBERS = ("radkfile", "radkfile2")
"""
`RADKFILE` member names inside the kradzip archive, which list each radical
with its stroke count
"""


def extract_krad(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `KRADFILE` and `RADKFILE` into database rows

    info: File Format
        - The `kradzip` archive is a ZIP bundling several `EUC-JP` encoded
          text files, where lines starting with `#` are comments

        - `RADKFILE` is grouped by radical, where a `$ radical strokes` line
          introduces a radical and is followed by the kanji that contain it.
          Only the `$` lines are read here, for the radical stroke counts

        - `KRADFILE` lists one kanji per line as `kanji : rad1 rad2 ...`,
          giving the radical components that make up that kanji

        - The two `2` suffixed members (`kradfile2`, `radkfile2`) are newer
          supplements read the same way

    Args:
        path (Path): Path of the kradzip archive

    Yields:
        Rows for the `radical` and `kanji_radical` tables
    """
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())

        for member in _RADK_MEMBERS:
            if member not in names:
                continue
            text = archive.read(member).decode("euc-jp", errors="replace")
            for line in text.splitlines():
                if not line or line.startswith("#"):
                    continue
                if line.startswith("$"):
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    radical = parts[1]
                    stroke = (
                        int(parts[2])
                        if len(parts) > 2 and parts[2].isdigit()
                        else None
                    )
                    yield (
                        "radical",
                        {"radical": radical, "stroke_count": stroke},
                    )

        for member in _KRAD_MEMBERS:
            if member not in names:
                continue
            text = archive.read(member).decode("euc-jp", errors="replace")
            for line in text.splitlines():
                if not line or line.startswith("#") or " : " not in line:
                    continue
                kanji, components = line.split(" : ", 1)
                literal = kanji.strip()
                for radical in components.split():
                    yield (
                        "kanji_radical",
                        {"literal": literal, "radical": radical},
                    )


# --- JmdictFurigana ---


def extract_furigana(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `JmdictFurigana` into database rows

    info: File Format
        - A gzipped tar archive holding a single `.json` file, which is one
          large `JSON` array of records

        - Each record is an object with `text` (the written spelling),
          `reading` (its full kana reading) and `furigana` (the segmentation)

        - `furigana` is a list of `{"ruby": span, "rt": kana}` objects that
          align each span of the spelling to the kana it is read as, and is
          stored verbatim as JSON in the `segments` column

    Args:
        path (Path): Path of the gzipped tar archive that holds the JSON

    Yields:
        Rows for the `furigana` table

    Raises:
        FileNotFoundError: If the archive has no `JSON` member
    """
    with tarfile.open(path, "r:gz") as archive:
        member = next(
            (m for m in archive.getmembers() if m.name.endswith(".json")),
            None,
        )
        if member is None:
            raise SourceExtractionError(f"No JSON Member In '{path}'")
        handle = archive.extractfile(member)
        if handle is None:
            raise SourceExtractionError(f"Couldn't Read '{member.name}'")
        records = json.load(handle)

    for record in records:
        yield (
            "furigana",
            {
                "text": record["text"],
                "reading": record["reading"],
                "segments": _to_json(record["furigana"]),
            },
        )


# --- KanjiVG ---

_KVG_ID_RE = re.compile(r"^kvg:kanji_([0-9a-f]+)$")
"""
Matches a base `KanjiVG` element id such as `kvg:kanji_06f22` and captures the
hex Unicode codepoint, which excludes the suffixed variant ids
"""


def extract_kanjivg(path: Path) -> Iterator[DatabaseRow]:
    """
    Stream `KanjiVG` stroke order data into database rows

    info: File Format
        - A gzipped XML file whose root holds one `<kanji>` element per
          character, streamed one at a time

        - The `id` attribute is `kvg:kanji_XXXXX`, where `XXXXX` is the kanji's
          lowercase hex Unicode codepoint, decoded back into the literal

        - Variant forms carry an extra suffix on the `id` and are skipped so
          each literal appears once

        - Inside, nested `<g>` groups hold the `<path>` stroke elements, where
          each `<path>` is one stroke. The whole element is stored as SVG
          markup and the stroke count is the number of `<path>` descendants

    Args:
        path (Path): Path of the gzipped `KanjiVG` XML

    Yields:
        Rows for the `kanji_strokes` table
    """
    for element in stream_elements(path, "kanji"):
        match = _KVG_ID_RE.match(element.get("id", ""))
        if match:
            literal = chr(int(match.group(1), 16))
            yield (
                "kanji_strokes",
                {
                    "literal": literal,
                    "stroke_count": len(element.findall(".//path")),
                    "svg": etree.tostring(element, encoding="unicode"),
                },
            )


# --- Tanos JLPT ---


def _load_jlpt(kind: str, level: int) -> list[dict[str, Any]]:
    """
    Reads a single `Tanos JLPT` JSON file shipped with the package

    Args:
        kind (str): One of `vocab`, `kanji` or `grammar`
        level (int): A JLPT level from 1 to 5

    Returns:
        The decoded list of records from the file
    """
    path = config.jlpt_file(kind, level)
    data: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
    return data


def extract_jlpt() -> Iterator[DatabaseRow]:
    """
    Stream the `Tanos JLPT` lists into database rows

    info: File Format
        - The lists come from Tanos and ship inside the package, not
          downloaded, as the files `{kind}_n{level}.json` for the three kinds
          across the five levels

        - Each file is a `JSON` array of records

        - A `vocab` record has `kanji`, `hiragana` and `english`, where the
          stored word falls back to `hiragana` when `kanji` is empty

        - A `kanji` record has `kanji`, space joined `on` and `kun` readings
          and `english`

        - A `grammar` record has `grammar`, `formation` and `examples`, though
          `formation` and `examples` are empty across the current dataset

    Yields:
        Rows for the `jlpt_vocab`, `jlpt_kanji` and `jlpt_grammar` tables
    """
    for level in config.JLPT_LEVELS:
        for record in _load_jlpt("vocab", level):
            yield (
                "jlpt_vocab",
                {
                    "level": level,
                    "word": record.get("kanji") or record.get("hiragana"),
                    "reading": record.get("hiragana"),
                    "meaning": record.get("english"),
                },
            )
        for record in _load_jlpt("kanji", level):
            yield (
                "jlpt_kanji",
                {
                    "level": level,
                    "kanji": record.get("kanji"),
                    "on_yomi": record.get("on"),
                    "kun_yomi": record.get("kun"),
                    "meaning": record.get("english"),
                },
            )
        for record in _load_jlpt("grammar", level):
            yield (
                "jlpt_grammar",
                {
                    "level": level,
                    "grammar": record.get("grammar"),
                    "formation": record.get("formation"),
                    "examples": _to_json(record.get("examples") or []),
                },
            )


# --- Tatoeba ---


def extract_tatoeba(
    jpn_path: Path,
    links_path: Path | None = None,
    eng_path: Path | None = None,
) -> Iterator[DatabaseRow]:
    """
    Stream `Tatoeba` sentences and their alignments into database rows

    The global links file is huge, so it is filtered in a single pass to the
    links that touch a Japanese sentence rather than held in full, and only the
    English sentences that those links reach are stored

    info: File Format
        - `jpn_sentences.tsv.bz2` and `eng_sentences.tsv.bz2` are bzip2
          compressed TSV files with the columns `id`, `lang` and `text`

        - `links.tar.bz2` is a tar archive holding `links.csv`, which is
          actually tab separated `source_id` and `target_id` pairs, listing
          both directions of every translation link

        - The id columns are integers and are matched across the three files
          to align Japanese sentences with their English translations

    Args:
        jpn_path (Path): Path of the Japanese `jpn_sentences.tsv.bz2`
        links_path (Path | None): Path of the global `links.tar.bz2`, or None
            to skip alignment
        eng_path (Path | None): Path of the English `eng_sentences.tsv.bz2`, or
            None to skip alignment

    Yields:
        Rows for the `sentence` and `sentence_link` tables
    """
    # Pass 1: every Japanese sentence, remembering its id for the link filter
    japanese_ids: set[int] = set()
    for columns in _read_tsv_bz2(jpn_path):
        if len(columns) < 3:
            continue
        sentence_id = int(columns[0])
        japanese_ids.add(sentence_id)
        yield (
            "sentence",
            {"id": sentence_id, "lang": columns[1], "text": columns[2]},
        )

    if links_path is None or eng_path is None:
        return

    # Pass 2: keep only links whose source is a Japanese sentence, and collect
    # the English ids they point at
    pairs: list[tuple[int, int]] = []
    needed: set[int] = set()
    for columns in _read_tar_bz2_member(links_path, "links.csv"):
        if len(columns) < 2:
            continue
        source_id = int(columns[0])
        target_id = int(columns[1])
        if source_id in japanese_ids:
            pairs.append((source_id, target_id))
            needed.add(target_id)

    # Pass 3: store only the English sentences those links reach, then the
    # links
    english_ids: set[int] = set()
    for columns in _read_tsv_bz2(eng_path):
        if len(columns) < 3:
            continue
        sentence_id = int(columns[0])
        if sentence_id in needed:
            english_ids.add(sentence_id)
            yield (
                "sentence",
                {"id": sentence_id, "lang": columns[1], "text": columns[2]},
            )

    for source_id, target_id in pairs:
        if target_id in english_ids:
            yield (
                "sentence_link",
                {"source_id": source_id, "target_id": target_id},
            )


# --- Kanji alive audio ---

_AUDIO_NAME_RE = re.compile(r"^(?P<prefix>.+)_\d+_[a-z]\.mp3$")
"""
Matches a Kanji alive audio filename and captures the romanized reading
`prefix` that precedes the clip index and the variant letter
"""

_AUDIO_SOURCE = "kanjialive"
"""
Source identifier recorded on every Kanji alive audio row
"""

_AUDIO_LICENSE = "CC-BY-4.0"
"""
SPDX license identifier recorded on every Kanji alive audio row
"""

_AUDIO_ATTRIBUTION = "https://kanjialive.com/"
"""
Attribution URL recorded on every Kanji alive audio row
"""


def _kname_map(ka_data_path: Path) -> dict[str, str]:
    """
    Build a mapping of reading prefix to kanji from the Kanji alive data

    The `kname` column of the spreadsheet is exactly the prefix that each audio
    filename starts with, which is how a clip is tied back to its kanji

    Args:
        ka_data_path (Path): Path of the `ka_data.csv` spreadsheet

    Returns:
        A mapping of the romanized `kname` prefix to its kanji character
    """
    mapping: dict[str, str] = {}
    with open(ka_data_path, encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        kanji_index = header.index("kanji")
        kname_index = header.index("kname")
        for row in reader:
            if len(row) > max(kanji_index, kname_index) and row[kname_index]:
                mapping[row[kname_index]] = row[kanji_index]
    return mapping


def extract_audio(
    audio_path: Path,
    ka_data_path: Path,
) -> Iterator[DatabaseRow]:
    """
    Stream `Kanji Alive` audio clips into database rows

    The raw mp3 bytes are stored in the row alongside their license metadata

    info: File Format
        - `audio-mp3.zip` is a ZIP of mp3 clips named
          `{kname}_{index}_{variant}.mp3`, such as `jutsu-no(beru)_1_a.mp3`,
          where the leading `kname` prefix is a romanized reading

        - `ka_data.csv` is a spreadsheet with a `kanji` column and a `kname`
          column, where `kname` matches the filename prefix and maps each clip
          to its kanji

        - Clips whose prefix is not found in the spreadsheet are skipped

    Args:
        audio_path (Path): Path of the `audio-mp3.zip` archive
        ka_data_path (Path): Path of the `ka_data.csv` spreadsheet

    Yields:
        Rows for the `audio` table
    """
    kname_to_kanji = _kname_map(ka_data_path)
    with zipfile.ZipFile(audio_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = Path(info.filename).name
            match = _AUDIO_NAME_RE.match(name)
            if match is None:
                continue
            literal = kname_to_kanji.get(match.group("prefix"))
            if literal is None:
                continue
            yield (
                "audio",
                {
                    "kind": "kanji_word",
                    "key": literal,
                    "reading": Path(name).stem,
                    "fmt": "mp3",
                    "sample_rate": None,
                    "data": archive.read(info),
                    "url": None,
                    "source": _AUDIO_SOURCE,
                    "license": _AUDIO_LICENSE,
                    "attribution": _AUDIO_ATTRIBUTION,
                },
            )


# --- Extractor Registry ---


EXTRACTORS: dict[str, Extractor] = {
    "jmdict": Extractor(
        "jmdict",
        (
            "jmdict_entry",
            "jmdict_kanji",
            "jmdict_kana",
            "jmdict_sense",
            "jmdict_gloss",
            "tag",
        ),
        extract_jmdict,
    ),
    "jmnedict": Extractor(
        "jmnedict",
        (
            "jmnedict_entry",
            "jmnedict_kanji",
            "jmnedict_kana",
            "jmnedict_translation",
            "jmnedict_gloss",
            "tag",
        ),
        extract_jmnedict,
    ),
    "kanjidic": Extractor(
        "kanjidic",
        (
            "kanji",
            "kanji_reading",
            "kanji_meaning",
            "kanji_nanori",
            "kanji_dic_ref",
            "kanji_query_code",
            "kanji_variant",
            "kanji_codepoint",
        ),
        extract_kanjidic,
    ),
    "krad": Extractor(
        "krad",
        ("radical", "kanji_radical"),
        extract_krad,
    ),
    "furigana": Extractor(
        "furigana",
        ("furigana",),
        extract_furigana,
    ),
    "kanjivg": Extractor(
        "kanjivg",
        ("kanji_strokes",),
        extract_kanjivg,
    ),
    "jlpt": Extractor(
        "jlpt",
        ("jlpt_vocab", "jlpt_kanji", "jlpt_grammar"),
        extract_jlpt,
    ),
    "tatoeba": Extractor(
        "tatoeba",
        ("sentence", "sentence_link"),
        extract_tatoeba,
    ),
    "audio": Extractor(
        "audio",
        ("audio",),
        extract_audio,
    ),
}
"""
Represents all extractors available to the builder

A dictionary mapping extractor names to their respective `Extractor` object
"""
