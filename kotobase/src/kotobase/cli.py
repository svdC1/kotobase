from __future__ import annotations
import textwrap
import click

from kotobase.api import Kotobase
from kotobase.db_builder.build_database import build as build_db_command
from kotobase.db_builder.pull import pull_db as pull_db_command


# ────────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────────

kb = Kotobase()


def bullet(text, indent=2):
    click.echo(" " * indent + "• " + text)


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
    result = kb.lookup(word,
                       wildcard=wildcard,
                       include_names=names,
                       sentence_limit=sentences)

    if json_out:
        click.echo(result.to_json(indent=2, ensure_ascii=False))
        return

    # ---------- JMdict / JMnedict ----------
    click.secho("\n[Dictionary Entries]", fg="cyan", bold=True)
    if result.entries:
        for ent in result.entries:
            head = ", ".join(ent.kanji) or ", ".join(ent.kana)
            sub = ", ".join(ent.kana) if ent.kanji else ""
            click.secho(f" {head}", bold=True)
            if sub:
                click.echo(f"   {sub}")
            for s in ent.senses:
                glosses = "; ".join(s["gloss"] if isinstance(s["gloss"], list)
                                    else [s["gloss"]])
                bullet(glosses, indent=4)
    else:
        click.echo("  (nothing found)")

    # ---------- Kanji ----------
    if result.kanji:
        click.secho("\n[Kanji Breakdown]", fg="cyan", bold=True)
        for kan in result.kanji:
            jlpt = kan.jlpt_tanos or kan.jlpt_kanjidic
            jlpt_str = f"N{jlpt}" if jlpt else ""
            click.secho(f"{kan.literal}\n", bold=True, nl=False)
            click.echo(f"  grade: {kan.grade or '-'}")
            click.echo(f"  strokes: {kan.stroke_count}")
            click.echo(f"  jlpt: {jlpt_str}")
            wrap("Meanings: " + ", ".join(kan.meanings))

    # ---------- JLPT vocab ----------
    if result.jlpt_vocab:
        click.secho("\n[JLPT Vocabulary]", fg="cyan", bold=True)
        click.echo(
            f"  Word appears in JLPT N{result.jlpt_vocab.level} Tanos list")

    # ---------- JLPT grammar ----------
    if result.jlpt_grammar:
        click.secho("\n[Related JLPT Grammar]", fg="cyan", bold=True)
        for g in result.jlpt_grammar:
            bullet(f"N{g.level}: {g.grammar}")

    # ---------- Sentences ----------
    if sentences:
        click.secho("\n[Example Sentences]", fg="cyan", bold=True)
        if result.examples:
            for sen in result.examples[:sentences]:
                bullet(sen.text)
        else:
            click.echo("  (none)")

# ────────────────────────────────────────────────────────────────────────
#  kanji  <character>
# ────────────────────────────────────────────────────────────────────────


@main.command()
@click.argument("literal")
def kanji(literal: str):
    """
    Show KanjiDic details for a single character.
    """
    info = kb.kanji(literal)
    if not info:
        click.echo("Kanji not found.")
        return

    click.secho(f"{info.literal}", bold=True)
    click.echo(f" Grade: {info.grade or '-'}")
    click.echo(f" Strokes: {info.stroke_count}")
    jlpt = info.jlpt_tanos or info.jlpt_kanjidic
    if jlpt:
        click.echo(f" JLPT:  N{jlpt}")
    wrap("Meanings: " + ", ".join(info.meanings))
    wrap("On-yomi:   " + ", ".join(info.onyomi))
    wrap("Kun-yomi:  " + ", ".join(info.kunyomi))


# ────────────────────────────────────────────────────────────────────────
#  jlpt  <word>
# ────────────────────────────────────────────────────────────────────────

@main.command()
@click.argument("word")
def jlpt(word: str):
    """
    Show JLPT levels associated with a word / kanji string.
    """
    vocab_level = kb.jlpt_level(word)
    kanji_levels = kb.lookup(word).jlpt_kanji_levels  # quick reuse

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
