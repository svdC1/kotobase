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

## Comprehensive Lookup

`lookup` Aggregates Every Source Into One Result

```python
result = kb.lookup("日本語")
result = kb("日本語")  # (1)!

for entry in result.entries:
    print(
        f"Written Form : {entry.headword}",
        f"High-Frequency Word ? : {entry.is_common}"
        )
    for sense in entry.senses:
        print(f"Meanings : {''.join(g.text for g in sense.glosses)}")

for kanji in result.kanji:
    print(
        f"Literal: {kanji.literal}",
        f"Meanings: {kanji.meanings}"
        )
```

1. Alias For `kb.lookup`

### Options

```python
result = kb.lookup(
    "食べ*",
    wildcard=True, # (1)!
    include_names=True, # (2)!
    sentence_limit=10,  # (3)!
    with_labels=True,  # (4)!
)
print(result.labels["sl"])
```

1. Treat `*` As A Wildcard
2. Include Proper Names From `JMNedict`
3. Return 10 Example Sentences + Translations
4. Resolve `JMDict` / `JMNedict` Tag Codes To Their Descriptions *(sl -> slang)*

---

## Search Kanji

Filter Kanji By Scalar Attributes, Or Look Them Up By SKIP Code

```python
n5 = kb.search_kanji(jlpt=5, limit=50)  # (1)!
eight_strokes = kb.search_kanji(stroke_count=8, grade=2) # (2)!
by_skip = kb.kanji_by_skip("1-4-3") # (3)!
```

1. First 50 Kanji Listed In `Tanos' N5 JLPT List`
2. Only Kanji That Have 8 Strokes And Are Learned In The Second Grade
3. Kanji That Are Vertically Split Into Left / Right Parts `(1-)`, Where The Left Part Has 4 Strokes `(1-4)`, And The Right Part Has 3 Strokes `(1-4-3)` *(e.g 那)*. Read More About The [`System of Kanji Indexing by Patterns`](https://www.edrdg.org/wwwjdic/SKIP.html)


## Radicals

Find Kanji Which Contain Certain `Radicals`

```python
radicals = kb.radicals()  # (1)!
matches = kb.by_radicals(["言", "五"]) #  (2)!
```

1. View Every Search Radical
2. Find All Kanji That Contain Both `言` + `五` Radicals *(e.g 語)*

## Proper Names

```python
tanaka = kb.names("田中")  # (1)!
places = kb.names(name_type="place")  #(2)!
```

1. Search A Proper Name Entry
2. Search By Name Type

## Search By Meaning

Find Entries From Their English Gloss Using Full Text Search

```python
for entry in kb.search_meaning("to eat", limit=10):
    print(entry.headword)
```

## Example Sentences

Find Example Sentences Containing A Given Text

```python
for sentence in kb.sentences("日本", limit=5):
    print(sentence.text)
    for translation in sentence.translations:
        print("  ", translation)
```

## Furigana

View Furigana Segmentation For A Given Word

```python
for item in kb.furigana("食べる"):
    print(item.reading, item.segments)
```

## JLPT

Browse `Tanos JLPT` Study Lists

```python
level = kb.jlpt_level("勉強")

vocab = kb.jlpt_list("vocab", 5)
kanji = kb.jlpt_list("kanji", 5)
grammar = kb.jlpt_list("grammar", 2)
```

## Stroke Order

Access Stroke Order SVGs

```python
svg = kb.stroke_svg("春") # (1)!
raw = kb.stroke_svg("春", raw=True) # (2)!
if svg is not None:
    open("haru.svg", "w", encoding="utf-8").write(svg)
```

1. A Renderable `SVG` Document
2. The Raw `KanjiVG` fragment

## Audio

Access Pronunciation Audio From The Optional Audio Pack

```python
clips = kb.audio("語")  # (1)!
for clip in clips:
    print(clip.reading, clip.fmt, clip.source, clip.license)

files = kb.audio_bytes("語")  # (2)!
name, data = files[0]

paths = kb.save_audio("語", "clips")  # (3)!
```

1. Clip Metadata, Without The Bytes
2. Each Clip As A `(file_name, bytes)` Pair
3. Write Every Clip Into `clips/` And Return The Written Paths

???+ warning "Needs The Audio Pack"
    These Raise `AudioDatabaseNotFoundError` When The Optional Audio Pack Is Not Installed *(`kotobase db pull --with-audio`)*



## Expanding Tag Codes

Exapand `JMDict` / `JMNedict` Tag Codes To Their Full Descriptions

```python
labels = kb.expand_tags(["sl", "n", "vs"])
# {"sl": "slang", "n": "noun (common) (futsuumeishi)", ...}
```

## Serialization

Every Result Object Can Be Turned Into A Plain Dictionary Or JSON With
Japanese Text Kept Verbatim

```python
result = kb.lookup("語")
data = result.to_dict()
text = result.to_json()
for field, value in result:   # iteration yields (field, value) pairs
    ...
```

## Database Metadata

```python
info = kb.db_info()
print(info["build_date"], info["size_mb"])
```

## Using Kotobase Concurrently

The Read Layer Is `Thread-Safe`, So An `async` Application Can Run A `lookup` Off
The Event Loop Without Blocking It

```python
import asyncio


async def main() -> None:
    result = await asyncio.to_thread(kb.lookup, "日本語")
    print(result.query)


asyncio.run(main())
```
