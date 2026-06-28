# Third-Party Notices

Kotobase is licensed under the [`MIT License`](https://github.com/svdC1/kotobase/blob/main/LICENSE)

This page acknowledges the third-party software and data Kotobase depends on
and redistributes

???+ abstract "License Locations"
    - The full license text for every bundled `Python` dependency ships inside that package's metadata (`*.dist-info/`) in your environment

    - The compiled database is a `derived work` of the data sources in `Required Attributions` below, and each clip in the optional audio pack additionally records its own `source` / `license` / `attribution`

    - The notices below cover the components whose licenses require explicit attribution

## Required Attributions

### JMdict / JMnedict &rarr; Dictionary + Name Data

- Kotobase's dictionary and proper-name lookups use data derived from the `JMdict` and `JMnedict` files, the property of the [`Electronic Dictionary Research and Development Group (EDRDG)`](https://www.edrdg.org/), used in conformance with the group's [`Licence`](https://www.edrdg.org/edrdg/licence.html)

- These files are made available under the `Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)` Licence

### KanjiDic2 &rarr; Kanji Data

- Kotobase's kanji profiles use data derived from the `KanjiDic2` file, also the property of the [`EDRDG`](https://www.edrdg.org/) and used in conformance with their [`Licence`](https://www.edrdg.org/edrdg/licence.html)

- Made available under the `CC BY-SA 4.0` Licence

### KRADFILE / RADKFILE &rarr; Radical Decomposition

- Radical search uses the `KRADFILE` and `RADKFILE` files, part of the [`EDRDG`](https://www.edrdg.org/) projects and used in conformance with their [`Licence`](https://www.edrdg.org/krad/kradinf.html)

- Made available under the `CC BY-SA 4.0` Licence

### JmdictFurigana &rarr; Furigana Segmentation

- Furigana segmentation uses [`JmdictFurigana`](https://github.com/Doublevil/JmdictFurigana), itself a derivative of `JMdict`

- Made available under the `CC BY-SA 4.0` Licence

### KanjiVG &rarr; Stroke Order

- Stroke-order data uses [`KanjiVG`](https://kanjivg.tagaini.net/), Copyright (C) Ulrich Apel

- Made available under the `Creative Commons Attribution-ShareAlike 3.0 (CC BY-SA 3.0)` Licence

### Tatoeba &rarr; Example Sentences

- Example sentences and their Japanese to English alignments come from the [`Tatoeba`](https://tatoeba.org/) corpus

- Made available under the `Creative Commons Attribution 2.0 France (CC BY 2.0 FR)` Licence

### Tanos JLPT &rarr; JLPT Study Lists

- The JLPT vocabulary, kanji and grammar lists are sourced from [`tanos.co.uk`](http://www.tanos.co.uk/jlpt/) by Jonathan Waller

- Made available under the `Creative Commons Attribution 4.0 (CC BY 4.0)` Licence

???+ note "Tanos Processing Note"
    - The Tanos lists are distributed as PDF documents. The `JSON` shipped in the package (`kotobase/data/jlpt/`) was programmatically extracted from those PDFs and is therefore a `modified` form of the originals, as permitted under `CC BY 4.0`

    - The PDFs follow no standardised format, so the extraction is best-effort and individual entries may contain minor artifacts from PDF text recovery *(e.g. spacing in readings or glosses)*

    - The grammar lists contain only the grammar points, the source PDFs include no formation patterns or example sentences, so those fields are left empty

    - Some vocabulary and kanji entries have no English gloss or reading, reflecting omissions in the source rather than data loss during processing

    - No changes were made to the linguistic content of the source data

### Kanji Alive &rarr; Pronunciation Audio

- The optional audio pack bundles word-pronunciation clips from the [`Kanji Alive`](https://kanjialive.com/) project

- Made available under the `CC BY 4.0` Licence

- This applies only to the optional audio database

## Notable Components

| Component | Role | License |
| --- | --- | --- |
| [`SQLAlchemy`](https://www.sqlalchemy.org/) | ORM + Database Toolkit | `MIT` |
| [`Typer`](https://typer.tiangolo.com/) | CLI Framework | `MIT` |
| [`Rich`](https://github.com/Textualize/rich) | Terminal Rendering | `MIT` |
| [`Requests`](https://requests.readthedocs.io/) | Source + Database Downloads | `Apache-2.0` |
| [`python-zstandard`](https://github.com/indygreg/python-zstandard) | Database Compression | `BSD-3-Clause` |
| [`platformdirs`](https://github.com/tox-dev/platformdirs) | Cache Directory Resolution | `MIT` |
| [`lxml`](https://lxml.de/) | XML Parsing During The Build | `BSD-3-Clause` |

This list is not exhaustive

See each project's repository and the bundled metadata for complete terms
