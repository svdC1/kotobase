## Python API Usage

Example Python Usage

```python
from kotobase import Kotobase

kb = Kotobase()

# Comprehensive lookup
result = kb.lookup("日本語")
print(result.to_json())

# Get info for a single kanji
kanji_info = kb.kanji("語")
print(kanji_info)

# Get example sentences
sentences = kb.sentences("勉強")
for sentence in sentences:
    print(sentence.text)
```
