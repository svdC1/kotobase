import json
import click
from lxml import etree
from io import BytesIO
from kotobase.db_builder.config import (RAW_JMNEDICT_PATH, JMNEDICT_PATH)

# XSLT content is embedded directly into the script
XSLT_TRANSFORM = b"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="text" encoding="UTF-8"/>
    <xsl:strip-space elements="*"/>

    <!-- Define delimiters -->
    <xsl:variable name="field_sep" select="'|'"/>
    <xsl:variable name="list_sep" select="'~'"/>
    <xsl:variable name="trans_sep" select="'^'"/>

    <xsl:template match="/JMnedict">
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
            <xsl:if test="position() != last()">\
                <xsl:value-of select="$list_sep"/></xsl:if>
        </xsl:for-each>
        <xsl:value-of select="$field_sep"/>

        <!-- Translation Elements -->
        <xsl:for-each select="trans">
            <!-- Type -->
            <xsl:for-each select="name_type">
                <xsl:value-of select="."/>
                <xsl:if test="position() != last()">\
                    <xsl:value-of select="$list_sep"/></xsl:if>
            </xsl:for-each>
            <xsl:text>;</xsl:text>
            <!-- Translation Detail -->
            <xsl:for-each select="trans_det">
                <xsl:value-of select="."/>
                <xsl:if test="position() != last()">\
                    <xsl:value-of select="$list_sep"/></xsl:if>
            </xsl:for-each>
            <xsl:if test="position() != last()">\
                <xsl:value-of select="$trans_sep"/></xsl:if>
        </xsl:for-each>

        <!-- Newline for next entry -->
        <xsl:text>&#10;</xsl:text>
    </xsl:template>

</xsl:stylesheet>
"""


def parse_jmnedict():
    """
    Parses JMnedict.xml and saves it as a JSON file using an embedded XSLT.
    """

    raw_path = RAW_JMNEDICT_PATH
    processed_path = JMNEDICT_PATH

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

            entry_id, kanji_str, kana_str, trans_str = parts
            translations = []
            for trans_part in trans_str.split('^'):
                if not trans_part:
                    continue
                if ';' in trans_part:
                    type_str, detail_str = trans_part.split(';', 1)
                else:
                    type_str, detail_str = trans_part, ""
                translations.append({
                    "type": [t for t in type_str.split('~') if t],
                    "translation": [d for d in detail_str.split('~') if d]
                })

            entries.append({
                "id": int(entry_id),
                "kanji": [{"text": k} for k in kanji_str.split('~') if k],
                "kana": [{"text": k} for k in kana_str.split('~') if k],
                "translations": translations
            })

    click.echo(f"\nWriting {len(entries)} entries to {processed_path.name}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False)

    click.secho("Successfully processed JMnedict.", fg="green")


__all__ = ["XSLT_TRANSFORM", "parse_jmnedict"]

if __name__ == "__main__":
    parse_jmnedict()
