"""
This module defines the `SentenceRepo` class used for querying
data extracted from the Japanese Tatoeba example sentences
in the database.
"""


from __future__ import annotations
from typing import List
from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm
__all__ = ["SentenceRepo"]


class SentenceRepo:
    """
    Query database for Tatoeba example senteces Tables.
    """

    @staticmethod
    def search_containing(
        text: str,
        /,
        limit: int = 50,
        wildcard: bool = False,
    ) -> List[dt.SentenceDTO]:
        """
        Basic LIKE search.  If `wildcard=True` every non-space char is wrapped
        in '%' to simulate a *contains all chars in order* fuzzy search.

        Args:
          text (str): Text to look for in sentences

          limit (int): Limit how many sentences are returned.

          wildcard (bool): If True every non-space char is wrapped
                           in '%' to simulate a `contains all chars in order`
                           fuzzy search.

        Returns:
          List[SentenceDTO]: List of Sentence data objects.
        """
        if wildcard:
            text = text.replace("*", "%")
            text = '%'.join(text)

        pattern = f"%{text}%"

        with get_db() as s:
            rows = (
                s.query(orm.TatoebaSentence)
                .filter(orm.TatoebaSentence.text.like(pattern, escape="\\"))
                .limit(limit)
                .all()
            )
        return dt.map_many(dt.map_sentence, rows)
