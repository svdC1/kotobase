import click
from kotobase.api import Kotobase
from kotobase.db_builder.build_database import build as build_db_command
from kotobase.db_builder.pull import pull_db as pull_db_command


@click.group()
def main():
    """
    A command-line interface for Kotobase.
    """
    pass


@main.command()
@click.argument('word')
def lookup(word):
    """
    Looks up a word and provides comprehensive information about it.
    """
    with Kotobase() as kb:
        word_info = kb.lookup_word(word)

        # JMDict Entries
        click.echo(click.style("\n[JMDict Entries]", fg='cyan'))
        if word_info["jmdict_entries"]:
            for entry in word_info["jmdict_entries"]:
                kanji_text = ', '.join([k.text for k in entry.kanji])
                kana_text = ', '.join([k.text for k in entry.kana])
                click.echo(f"  \
                    {click.style(kanji_text, bold=True)} ({kana_text})")
                for i, sense in enumerate(entry.senses):
                    click.echo(f"    {i+1}. {sense.gloss}")
        else:
            click.echo("  No JMDict entries found.")

        # Kanjidic Entries
        click.echo(click.style("\n[Kanjidic Entries]", fg='cyan'))
        if word_info["kanjidic_entries"]:
            for kanji in word_info["kanjidic_entries"]:
                if kanji:
                    jlpt_level = word_info['jlpt_kanji_levels'].get(
                        kanji.literal)
                    jlpt_text = f"(JLPT N{jlpt_level})" if jlpt_level else ""
                    click.echo(f"  \
                        {click.style(kanji.literal, bold=True)} {jlpt_text}")
                    click.echo(f"    Meaning: {kanji.meanings}")
                    click.echo(f"    On-Readings: {kanji.on_readings}")
                    click.echo(f"    Kun-Readings: {kanji.kun_readings}")
                    click.echo(f"    JLPT: {kanji.jlpt}")
                    click.echo(f"    Grade: {kanji.grade}")
                    click.echo(f"    Stroke Count: {kanji.stroke_count}")
        else:
            click.echo("  No Kanjidic entries found.")

        # Tatoeba Sentences
        click.echo(click.style("\n[Tatoeba Examples]", fg='cyan'))
        if word_info["tatoeba_sentences"]:
            for sentence in word_info["tatoeba_sentences"][:5]:
                click.echo(f"  - {sentence.text}")
        else:
            click.echo("  No Tatoeba examples found.")

        # JLPT Info
        click.echo(click.style("\n[JLPT Information]", fg='cyan'))
        if word_info["jlpt_vocab_level"]:
            click.echo(f"  Word is in JLPT N{word_info['jlpt_vocab_level']} \
                vocabulary.")
        else:
            click.echo("  Word not found in standard JLPT vocabulary lists.")

        if word_info["jlpt_grammar_entries"]:
            click.echo(click.style("\n[Related JLPT Grammar]", fg='cyan'))
            for entry in word_info["jlpt_grammar_entries"]:
                click.echo(f"  - N{entry.level}: {entry.grammar}")


main.add_command(build_db_command)
main.add_command(pull_db_command)

if __name__ == '__main__':
    main()
