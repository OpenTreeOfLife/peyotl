<?xml version="1.0"?>
<!-- from http://stackoverflow.com/questions/1429991/using-xsl-to-sort-attributes !-->
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="xml" encoding="UTF-8" indent="yes"/>
  <xsl:template match="*">
    <xsl:copy>
      <xsl:apply-templates select="@*">
        <xsl:sort select="name()"/>
      </xsl:apply-templates>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>
  <xsl:template match="@*|comment()|processing-instruction()">
    <xsl:copy/>
  </xsl:template>
</xsl:stylesheet>
