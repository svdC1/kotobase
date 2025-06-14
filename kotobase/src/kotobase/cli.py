from __future__ import annotations
import textwrap
import click
import sys
from typing import Union
from kotobase.api import Kotobase
from kotobase.db_builder.build_database import build as build_db_command
from kotobase.db_builder.pull import pull_db as pull_db_command
from kotobase.core.datatypes import (JMDictEntryDTO,
                                     JMNeDictEntryDTO,
                                     KanjiDTO,
                                     JLPTVocabDTO,
                                     JLPTGrammarDTO)


# ────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────

kb = Kotobase()


def bullet(text, indent=2):
    click.echo(" " * indent + "• " + text)


def section(text, indent=2, bln=False, color="green", **sechokw):
    fmt = " " * indent + f"[{text}]"
    if bln:
        fmt = f"\n{fmt}\n"
    click.secho(fmt, fg=color, **sechokw)


def entry_head(DTO: Union[JMDictEntryDTO, JMNeDictEntryDTO]):
    if isinstance(DTO, JMDictEntryDTO):
        section("JMDict", bln=True, indent=0)
    elif isinstance(DTO, JMNeDictEntryDTO):
        section("JMNeDict", bln=True, indent=0, color="bright_green")
    if DTO.kanji:
        section(" / ".join(DTO.kanji), color="magenta")
        if DTO.kana:
            section("Kana", indent=2)
            for kana in DTO.kana:
                bullet(kana, indent=4)
    else:
        if DTO.kana:
            section(" / ".join(DTO.kana), color="Magenta")


def wrap(text: str,
         width: int = 78,
         indent: int = 4
         ):
    click.echo(textwrap.fill(text,
                             width=width,
                             initial_indent=" " * indent,
                             subsequent_indent=" " * indent
                             )
               )


def handle_jmdict(DTO: JMDictEntryDTO):
    entry_head(DTO)
    if DTO.senses:
        for s in DTO.senses:
            order = s.get("order", "")
            pos = s.get("pos", "")
            gloss = s.get("gloss", "")
            section(order, indent=2)
            bullet(f"Part of Speech : {pos}".strip(), indent=4)
            bullet(f"Gloss: {gloss}".strip(), indent=4)


def handle_jmnedict(DTO: JMNeDictEntryDTO):
    entry_head(DTO)
    if DTO.translation_type:
        section("Translation Type", indent=2)
        bullet(DTO.translation_type, indent=4)
    if DTO.gloss:
        section("Gloss", indent=2)
        for g in DTO.gloss:
            bullet(g, indent=4)


def handle_kanji(DTO: KanjiDTO):
    # --- Literal ---
    section(DTO.literal, color="magenta", bold=True, bln=True)
    # --- JLPT ---
    if hasattr(DTO, "jlpt_kanjidic") and DTO.jlpt_kanjidic:
        section("JLPT - Kanjidic", indent=2)
        bullet(f"N{DTO.jlpt_kanjidic}", indent=4)
    if hasattr(DTO, "jlpt_tanos") and DTO.jlpt_tanos:
        section("JLPT - Tanos", color="bright_green", indent=2)
        bullet(f"N{DTO.jlpt_tanos}", indent=4)
    # --- Other Kanjidic Info ---
    if DTO.onyomi:
        section("Onyomi", indent=2)
        for on in DTO.onyomi:
            bullet(on, indent=4)
    if DTO.kunyomi:
        section("Kunyomi", indent=2)
        for kun in DTO.kunyomi:
            bullet(kun, indent=4)
    if DTO.stroke_count:
        section("Stroke Count", indent=2)
        bullet(str(DTO.stroke_count), indent=4)
    if hasattr(DTO, "grade") and DTO.grade:
        section("Grade", indent=2)
        bullet(str(DTO.grade), indent=4)
    if DTO.meanings:
        section("Meanings", indent=2)
        for m in DTO.meanings:
            bullet(m, indent=4)


def handle_jlpt_vocab(DTO: JLPTVocabDTO):
    if DTO.level:
        section("Level", indent=2)
        bullet(str(DTO.level), indent=4)
    if DTO.kanji:
        section("Kanji", indent=2)
        bullet(DTO.kanji, indent=4)
    if DTO.level:
        section("Hiragana", indent=2)
        bullet(DTO.hiragana, indent=4)
    if DTO.english:
        section("English", indent=2)
        bullet(DTO.english, indent=4)


def handle_jlpt_grammar(DTO: JLPTGrammarDTO):
    if DTO.level:
        section("Level", indent=2)
        bullet(DTO.level, indent=4)
    if DTO.grammar:
        section("Grammar", indent=2)
        bullet(DTO.grammar, indent=4)
    if DTO.formation:
        section("Formation", indent=2)
        bullet(DTO.formation, indent=4)
    if DTO.examples:
        section("Examples", indent=2)
        for ex in DTO.examples:
            bullet(ex, indent=4)
# ────────────────────────────────────────────────────────────────────────
#  Root group
# ────────────────────────────────────────────────────────────────────────


@click.group(help="Kotobase – Japanese lexical database CLI")
def main():
    pass


# ────────────────────────────────────────────────────────────────────────
#  lookup  <word>
# ────────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("word")
@click.option("-n",
              "--names",
              is_flag=True,
              help="Include JMnedict names"
              )
@click.option("-w",
              "--wildcard",
              is_flag=True,
              help="Treat '*'/'%' as wildcards"
              )
@click.option("-s",
              "--sentences",
              default=5,
              show_default=True,
              help="Number of example sentences to display (0 = none)"
              )
@click.option("--json-out",
              "-j",
              is_flag=True,
              help="Dump raw JSON result"
              )
def lookup(word: str,
           names: bool,
           wildcard: bool,
           sentences: int,
           json_out: bool
           ):
    """
    Comprehensive dictionary lookup.
    """
    try:
        result = kb.lookup(word,
                           wildcard=wildcard,
                           include_names=names,
                           sentence_limit=sentences)

        if json_out:
            click.echo(result.to_json())
            return

        # ---------- JMdict / JMnedict ----------
        click.secho("\n[Dictionary Entries]", fg="cyan", bold=True)
        if result.entries:
            for ent in result.entries:
                if isinstance(ent, JMDictEntryDTO):
                    handle_jmdict(ent)
                elif isinstance(ent, JMNeDictEntryDTO):
                    handle_jmnedict(ent)
        else:
            click.echo("No Entries")

        # ---------- Kanji ----------
        if result.kanji:
            click.secho("\n[Kanji Breakdown]", fg="cyan", bold=True)
            for kan in result.kanji:
                handle_kanji(kan)

        # ---------- JLPT vocab ----------
        if result.jlpt_vocab:
            click.secho("\n[Tanos JLPT Vocabulary]", fg="cyan", bold=True)
            handle_jlpt_vocab(result.jlpt_vocab)

        # ---------- JLPT grammar ----------
        if result.jlpt_grammar:
            click.secho("\n[Tanos JLPT Grammar]", fg="cyan", bold=True)
            for g in result.jlpt_grammar:
                handle_jlpt_grammar(g)
        # ---------- Sentences ----------
        if sentences:
            click.secho("\n[Example Sentences]", fg="cyan", bold=True)
            if result.examples:
                for sen in result.examples[:sentences]:
                    bullet(sen.text)
            else:
                click.echo("No Examples Found")
    except Exception as e:
        click.secho(f"Error During Lookup: {e}",
                    fg="red",
                    err=True
                    )
        sys.exit(1)

# ────────────────────────────────────────────────────────────────────────
#  kanji  <character>
# ────────────────────────────────────────────────────────────────────────


@main.command()
@click.argument("literal")
def kanji(literal: str):
    """
    Show KanjiDic details for a single character.
    """
    try:
        info = kb.kanji(literal)
        if not info:
            click.echo("Kanji not found.")
            return
        handle_kanji(info)
    except Exception as e:
        click.secho(f"Error During Lookup: {e}",
                    fg="red",
                    err=True
                    )
        sys.exit(1)


# ────────────────────────────────────────────────────────────────────────
#  jlpt  <word>
# ────────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("word")
def jlpt(word: str):
    """
    Show JLPT levels associated with a word / kanji string.
    """
    try:
        vocab_level = kb.jlpt_level(word)
        kanji_levels = kb.lookup(word).jlpt_kanji_levels
        if vocab_level:
            click.echo(f"Vocabulary level: N{vocab_level}")
        else:
            click.echo("Vocabulary: (not in JLPT lists)")

        if kanji_levels:
            click.echo("Kanji levels:")
            for k, lvl in kanji_levels.items():
                click.echo(f"  {k} -> N{lvl}")
        else:
            click.echo("Kanji: (none in JLPT lists)")
    except Exception as e:
        click.secho(f"Error During Lookup: {e}",
                    fg="red",
                    err=True
                    )
        sys.exit(1)

# ────────────────────────────────────────────────────────────────────────
#  db_info
# ────────────────────────────────────────────────────────────────────────


@main.command()
def db_info():
    """
    Print information about Database being used.
    """
    try:
        info = kb.db_info()
        click.secho("--- Database Build Log ---",
                    fg="blue")
        click.secho(f"Build Date : {info['build_date']}")
        click.secho(f"Build Time : {info['build_time']} seconds")
        click.secho(f"File Size : {info['size_mb']} MB")

    except Exception as e:
        click.secho(f"Error Getting Database Info: {e}",
                    fg="red",
                    err=True
                    )
        sys.exit(1)
# ────────────────────────────────────────────────────────────────────────
#  Wire maintenance commands from db_builder
# ────────────────────────────────────────────────────────────────────────


main.add_command(build_db_command)
main.add_command(pull_db_command)


# ────────────────────────────────────────────────────────────────────────
#  Entrypoint
# ────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    main()
