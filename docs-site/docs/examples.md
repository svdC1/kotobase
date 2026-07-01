# Examples

This section includes task-oriented snippets using `kotobase`



```python
from kotobase import Kotobase

# Every method opens its own `read-only session`,
# so a single shared instance is enough
kb = Kotobase()
```

---

???+ tip "Results"
    All returned objects are typed, immutable [`DTOs`][kotobase.db.dtos] that do not depend on an open
    session, so they are safe to keep, pass around and serialize

## Build A Flashcard Deck

Turn a `Tanos JLPT` level into study cards for an `SRS` app like `Anki`. Each
card pulls the reading, meaning and frequency from the dictionary, the stroke
order for every kanji, and a pronunciation clip, then exports as `JSON` with
Japanese text kept verbatim

```python
import json
from pathlib import Path

from kotobase import AudioDatabaseNotFoundError, Kotobase

kb = Kotobase()


def build_deck(level: int, audio_dir: Path) -> list[dict]:
    cards: list[dict] = []
    for vocab in kb.jlpt_list("vocab", level):  # (1)!
        word = vocab.word or vocab.reading
        if not word:
            continue

        result = kb.lookup(word)  # (2)!
        readings = kb.furigana(word)  # (3)!
        card = {
            "word": word,
            "reading": vocab.reading,
            "meaning": vocab.meaning,
            "common": any(e.is_common for e in result.entries),  # (4)!
            "parts_of_speech": (
                result.entries[0].all_pos() if result.entries else []
            ),  # (5)!
            "furigana": readings[0].segments if readings else [],
            "kanji": [
                {"literal": k.literal, "stroke_order": kb.stroke_svg(k.literal)}
                for k in result.kanji  # (6)!
            ],
        }

        try:
            saved = kb.save_audio(word, audio_dir)  # (7)!
            card["audio"] = [path.name for path in saved]
        except AudioDatabaseNotFoundError:
            card["audio"] = []

        cards.append(card)
    return cards


deck = build_deck(5, Path("audio"))
Path("n5_deck.json").write_text(
    json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8"
)  # (8)!
```

1. Every N5 vocabulary item from the `Tanos` list
2. Enrich the word with its full dictionary entry and per-kanji details
3. Per-form furigana segments, ready to render as ruby text
4. A pure `DTO` field, so a deck can prioritise common words
5. A pure `DTO` helper, the unique parts of speech across every sense
6. A renderable stroke-order `SVG` for each kanji in the word
7. Writes `<reading>.<fmt>` into the directory, needs the optional audio pack
8. Import-ready, with Japanese text and any audio file names kept verbatim

## Explore Related Words

Power a writing assistant by expanding one entry into the words around it: its
meaning with human-readable tags, the entries its cross-references and antonyms
point to, other vocabulary that shares a kanji, and a natural usage example

```python
import pprint

from kotobase import Kotobase

kb = Kotobase()


def related_words(word: str) -> dict:
    result = kb.lookup(word, with_labels=True)  # (1)!
    if not result.entries:
        return {}

    entry = result.entries[0]
    sense = entry.senses[0]
    panel = {
        "word": entry.headword,
        "meaning": [gloss.text for gloss in sense.glosses],
        "tags": sense.expand_tags(result.labels),  # (2)!
        "see_also": [e.headword for e in kb.resolve_references(entry)],  # (3)!
    }

    if entry.kanji:
        kanji = entry.kanji[0].text[0]
        panel["shares_kanji"] = [
            e.headword
            for e in kb.words_with_kanji(kanji, limit=8)  # (4)!
            if e.headword != entry.headword
        ]
        panel["example"] = next(
            (s.text for s in kb.sentences_with_kanji(kanji, limit=1)), None
        )  # (5)!

    return panel


pprint.pp(related_words("勉強"))
```

1. `with_labels` fills `result.labels` with each tag code's description
2. Resolve this sense's tag codes to descriptions on the `DTO` itself
3. Follow the entry's cross-references and antonyms to the real entries
4. Other words written with the kanji, accepts a string or a `KanjiDTO`
5. A natural sentence using the kanji, `None` when nothing matches

???+ tip "Async Applications"
    The read layer is `thread-safe`, so a web app can run any lookup off the
    event loop without blocking it

    ```python
    import asyncio


    async def lookup(word: str):
        return await asyncio.to_thread(kb.lookup, word)
    ```
