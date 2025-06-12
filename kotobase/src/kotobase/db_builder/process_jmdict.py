import json
import click
from lxml import etree
from io import BytesIO
from kotobase.db_builder.config import (RAW_JMDICT_PATH,
                                        JMDICT_PATH)

# XSLT content is embedded directly into the script
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


def parse_jmdict():
    """
    Parses JMdict_e.xml and saves it as a JSON file using an embedded XSLT.
    """

    raw_path = RAW_JMDICT_PATH
    processed_path = JMDICT_PATH

    processed_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Parsing {raw_path.name} with embedded XSLT...")

    # Load XML from file and XSLT from our embedded string
    xml_doc = etree.parse(str(raw_path))
    xslt_doc = etree.parse(BytesIO(XSLT_TRANSFORM))
    transform = etree.XSLT(xslt_doc)

    # Apply transformation at C-level for speed
    result_tree = transform(xml_doc)

    # Process the simplified text output
    entries = []
    lines = str(result_tree).splitlines()

    with click.progressbar(lines,
                           label="  -> Assembling JSON...",
                           item_show_func=lambda x: "") as bar:
        for i, line in enumerate(bar):
            parts = line.split('|')
            if len(parts) != 4:
                continue

            entry_id, kanji_str, kana_str, senses_str = parts

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
                "kanji": [{"text": k} for k in kanji_str.split('~') if k],
                "kana": [{"text": k} for k in kana_str.split('~') if k],
                "senses": senses
            })

    click.echo(f"\nWriting {len(entries)} entries to {processed_path.name}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False)

    click.secho("Successfully processed JMDict.", fg="green")


__all__ = ["XSLT_TRANSFORM", "parse_jmdict"]

if __name__ == "__main__":
    parse_jmdict()
