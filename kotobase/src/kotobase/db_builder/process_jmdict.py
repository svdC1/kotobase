"""
This module defines the helper function which
processes the raw JMDict XML file into a JSON
file using XSLT transform for performance.
"""

import json
import click
from lxml import etree
from typing import List
from io import BytesIO
from kotobase.db_builder.config import (RAW_JMDICT_PATH,
                                        JMDICT_PATH)


XSLT_TRANSFORM = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="text" encoding="UTF-8"/>
    <xsl:strip-space elements="*"/>

    <!-- Define delimiters -->
    <xsl:variable name="field_sep" select="'|'"/>
    <xsl:variable name="list_sep" select="'~'"/>
    <xsl:variable name="sense_sep" select="'^'"/>

    <xsl:template match="/JMdict">
        <xsl:apply-templates select="entry"/>
    </xsl:template>

    <xsl:template match="entry">
        <!-- Entry ID -->
        <xsl:value-of select="ent_seq"/>
        <xsl:value-of select="$field_sep"/>

        <!-- Kanji Elements -->
        <xsl:for-each select="k_ele">
            <xsl:value-of select="keb"/>
            <xsl:if test="position() != last()">\
                <xsl:value-of select="$list_sep"/></xsl:if>
        </xsl:for-each>
        <xsl:value-of select="$field_sep"/>

        <!-- Reading Elements -->
        <xsl:for-each select="r_ele">
            <xsl:value-of select="reb"/>
            <xsl:if test="position() != last()"><xsl:value-of select=\
                "$list_sep"/></xsl:if>
        </xsl:for-each>
        <xsl:value-of select="$field_sep"/>
        <!-- Priority Tags (ke_pri / re_pri) -->
        <xsl:for-each select="k_ele/ke_pri | r_ele/re_pri">
            <xsl:value-of select="."/>
            <xsl:if test="position() != last()">
                <xsl:value-of select="$list_sep"/>
            </xsl:if>
        </xsl:for-each>
        <xsl:value-of select="$field_sep"/>
        <!-- Sense Elements -->
        <xsl:for-each select="sense">
            <!-- Gloss -->
            <xsl:for-each select="gloss">
                <xsl:value-of select="."/>
                <xsl:if test="position() != last()"><xsl:value-of select="\
                    $list_sep"/></xsl:if>
            </xsl:for-each>
            <xsl:text>;</xsl:text>
            <!-- Part of Speech -->
            <xsl:for-each select="pos">
                <xsl:value-of select="."/>
                <xsl:if test="position() != last()"><xsl:value-of select="\
                    $list_sep"/></xsl:if>
            </xsl:for-each>
            <xsl:if test="position() != last()"><xsl:value-of select="\
                $sense_sep"/></xsl:if>
        </xsl:for-each>

        <!-- Newline for next entry -->
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

</xsl:stylesheet>
"""


def _rank(pri_list: List[str]) -> int:
    """
    Create an entry priority rank according to
    <pri> tags.

    Args:
      pri_list (List[str]): List of extracted <pri> tags

    Returns:
      int: Rank for the entry.
    """
    HIGH = {"news1",
            "ichi1",
            "spec1",
            "spec2",
            "gai1"
            }
    if any(tag in HIGH for tag in pri_list):
        return 0
    for tag in pri_list:
        if tag.startswith("nf"):
            return int(tag[2:])  # nf05 → 5
        return 99


def parse_jmdict() -> None:
    """
    Click helper function which parses JMdict_e.xml
    and saves it as a JSON file using an embedded XSLT.
    """

    raw_path = RAW_JMDICT_PATH
    processed_path = JMDICT_PATH
    # Delete if it already exists
    processed_path.unlink(missing_ok=True)

    processed_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Parsing '{raw_path.name}' with embedded XSLT ...")

    xml_doc = etree.parse(str(raw_path))
    xslt_doc = etree.parse(BytesIO(XSLT_TRANSFORM))
    transform = etree.XSLT(xslt_doc)

    result_tree = transform(xml_doc)

    entries = []
    lines = str(result_tree).splitlines()

    with click.progressbar(lines,
                           label="Assembling JSON -> ",
                           item_show_func=lambda x: "") as bar:
        for i, line in enumerate(bar):
            parts = line.split('|')
            if len(parts) != 5:
                continue

            entry_id, kanji_str, kana_str, pri_str, senses_str = parts
            pri_list = [p for p in pri_str.split('~') if p]
            entry_rank = _rank(pri_list)
            senses = []
            for j, sense_part in enumerate(senses_str.split('^')):
                if not sense_part:
                    continue
                if ';' in sense_part:
                    gloss_str, pos_str = sense_part.split(';', 1)
                else:
                    gloss_str, pos_str = sense_part, ""

                senses.append({
                    "order": j,
                    "gloss": [g for g in gloss_str.split('~') if g],
                    "pos": [p for p in pos_str.split('~') if p]
                })

                entries.append({
                    "id": int(entry_id),
                    "rank": entry_rank,
                    "kanji": [
                        {"text": k, "order": i}
                        for i, k in enumerate(kanji_str.split('~')) if k
                        ],
                    "kana": [{"text": k, "order": i}
                             for i, k in enumerate(kana_str.split('~')) if k
                             ],
                    "senses": senses
                    })

    click.echo(
        f"\nWriting {len(entries)} entries to '{processed_path.name}' ..."
        )
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False)

    click.secho("Successfully Processed JMDict.", fg="green")


__all__ = ["XSLT_TRANSFORM", "parse_jmdict"]

if __name__ == "__main__":
    parse_jmdict()
