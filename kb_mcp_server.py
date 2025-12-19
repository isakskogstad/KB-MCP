#!/usr/bin/env python3
"""
KB MCP Server - Kungliga bibliotekets öppna API:er
Model Context Protocol server för åtkomst till Sveriges kulturarvsdata.

Stöder:
- Lokal installation (stdio) för Claude Desktop, Claude Code
- Remote deployment (HTTP) för ChatGPT, Render hosting

Version: 2.1.0

Nya funktioner i 2.1.0:
- MCP Resources för read-only dokumentation och exempel
- MCP Prompts för vanliga användningsfall
- Nya verktyg: combined_search, quick_stats, historical_periods_search, find_related_works
- Svenska län-referens
"""

import asyncio
import json
import os
import sys
import logging
from typing import Any, Optional
from urllib.parse import urlencode, quote_plus

# MCP imports
from mcp.server.fastmcp import FastMCP
from pydantic import Field

# API client imports
from src.api_client import (
    api_client, 
    URLS, 
    handle_api_error,
    parse_ksamsok_xml,
    parse_oaipmh_xml,
    format_libris_results,
    format_ksamsok_results,
    format_sparql_results
)

# Konfigurera logging till stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger("kb_mcp")

# ============================================================================
# MCP SERVER SETUP
# ============================================================================

mcp = FastMCP(
    "kb-api",
    instructions="Kungliga bibliotekets öppna API:er - tillgång till 20M+ bibliografiska poster, 10M+ kulturarvsobjekt, svensk forskningspublicering och länkad data."
)


# ============================================================================
# MCP RESOURCES - Read-only data för kontext
# ============================================================================

@mcp.resource("kb://api/overview")
def resource_api_overview() -> str:
    """Översikt över alla KB API:er och deras kapacitet."""
    return """# Kungliga bibliotekets öppna API:er

## Tillgängliga datakällor

### 1. Libris - Nationell bibliotekskatalog
- **20+ miljoner** bibliografiska poster
- Böcker, tidskrifter, artiklar, e-resurser
- Sökbar via Xsearch (enkel) eller XL REST (avancerad)
- Stöd för JSON, JSON-LD, MARC

### 2. K-samsök - Kulturarvsaggregator
- **10+ miljoner** objekt från 83 institutioner
- Fotografier, konstverk, föremål, runstenar, kartor
- CQL-söksyntax för avancerade frågor
- Geografisk och temporal filtrering

### 3. Swepub - Svensk forskning
- **2+ miljoner** forskningspublikationer
- Avhandlingar, artiklar, rapporter
- Alla svenska lärosäten
- Export till RIS/BibTeX

### 4. id.kb.se - Auktoriteter
- **500 000+** kontrollerade termer
- Svenska ämnesord (SAO)
- Personauktoriteter
- Genre/form-termer

### 5. SPARQL - Länkad data
- RDF-baserade frågor
- Komplexa analyser
- Aggregeringar och statistik

## Ingen autentisering krävs
Alla API:er är öppna och gratis att använda.
"""


@mcp.resource("kb://search/syntax")
def resource_search_syntax() -> str:
    """Komplett guide till söksyntax för alla API:er."""
    return """# Söksyntax för KB:s API:er

## Libris - Sökoperatorer

### Fältsökning
- `titel:Röda rummet` - Sök i titelfältet
- `författare:Strindberg` - Sök efter författare
- `ämne:historia` - Sök på ämnesord
- `isbn:9789113084718` - Exakt ISBN-matchning
- `år:1879` - Utgivningsår

### Booleska operatorer
- `Strindberg AND Stockholm` - Båda termerna krävs
- `kaffe OR te` - Någon av termerna
- `Sverige NOT Norge` - Exkludera term
- `"exakt fras"` - Frassökning med citattecken

### Trunkering och wildcards
- `histor*` - Matchar historia, historisk, historien
- `wom?n` - Matchar woman, women

### Intervall
- `år:[1900 TO 1950]` - Årtalsintervall
- `år:[1800 TO *]` - Från 1800 och framåt

---

## K-samsök - CQL-syntax

### Grundläggande sökning
- `text=runsten` - Fritext i alla fält
- `itemType=Photograph` - Objekttyp
- `itemLabel=vikingasvärd` - Benämning

### Geografisk filtrering
- `countyName="Uppsala län"` - Län
- `municipalityName=Stockholm` - Kommun
- `parishName=Alsike` - Socken/församling

### Tidsfiltrering
- `fromTime>=1700` - Från år
- `toTime<=1800` - Till år
- `fromTime>=1600 AND toTime<=1700` - Period

### Bildfilter
- `thumbnailExists=true` - Har miniatyrbild
- `geoDataExists=true` - Har koordinater

### Kombinera filter
- `itemType=Photograph AND countyName="Gotlands län"`
- `text=kyrka AND fromTime>=1200 AND toTime<=1300`

---

## SPARQL - Prefix

```sparql
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
```
"""


@mcp.resource("kb://examples/libris")
def resource_examples_libris() -> str:
    """Exempelfrågor för Libris-sökning."""
    return """# Libris - Exempelfrågor

## Hitta böcker av en författare
```
libris_search_author(author_name="Lagerlöf, Selma")
libris_search_author(author_name="Lindgren, Astrid", limit=50)
```

## Söka efter titel
```
libris_search_title(title="Röda rummet")
libris_search_title(title="Pippi Långstrump", exact_match=True)
```

## Ämnesbaserad sökning
```
libris_search_subject(subject="vikingatiden")
libris_search_subject(subject="klimatförändringar", limit=25)
```

## ISBN-sökning
```
libris_search_isbn(isbn="9789113084718")
```

## Avancerad sökning med operatorer
```
libris_find(query="författare:Strindberg AND år:[1880 TO 1900]")
libris_find(query="titel:Stockholm AND ämne:historia")
libris_find(query="(feminism OR genus) AND år:[2010 TO 2024]")
```

## Hämta specifik post
```
libris_get_record(record_id="bib/12345")
libris_get_holdings(record_id="bib/12345")
```

## Exportera bibliografi
```
export_author_bibliography(author_name="Strindberg, August", format="ris")
export_subject_bibliography(subject="svensk litteratur", format="bibtex")
```
"""


@mcp.resource("kb://examples/ksamsok")
def resource_examples_ksamsok() -> str:
    """Exempelfrågor för K-samsök kulturarvssökning."""
    return """# K-samsök - Exempelfrågor

## Sök kulturarvsobjekt

### Runstenar
```
ksamsok_search(query="text=runsten")
ksamsok_search(query="itemType=Runestone AND countyName=\\"Uppsala län\\"")
```

### Fotografier
```
ksamsok_search_type(item_type="Photograph", has_image=True)
ksamsok_search_location(county="Stockholms län", item_type="Photograph")
```

### Konst och målningar
```
ksamsok_search_type(item_type="Painting")
ksamsok_search(query="text=porträtt AND itemType=Painting")
```

### Historiska byggnader
```
ksamsok_search_type(item_type="Building", has_coordinates=True)
ksamsok_search_time(from_year=1600, to_year=1700, item_type="Building")
```

## Geografisk sökning

### Per län
```
ksamsok_search_location(county="Gotlands län")
ksamsok_search_location(county="Skåne län", item_type="Photograph")
```

### Per kommun
```
ksamsok_search_location(municipality="Uppsala")
ksamsok_search_location(municipality="Lund", item_type="Building")
```

### Per socken (för släktforskning)
```
ksamsok_search_location(parish="Alsike")
```

## Tidsperioder

### Vikingatid
```
ksamsok_search_time(from_year=800, to_year=1100)
```

### Medeltid
```
ksamsok_search_time(from_year=1100, to_year=1500)
```

### Stormaktstid
```
ksamsok_search_time(from_year=1611, to_year=1721)
```

## Statistik
```
ksamsok_statistics(index="itemType")
ksamsok_statistics(index="serviceOrganization")
ksamsok_statistics(index="county")
```
"""


@mcp.resource("kb://examples/sparql")
def resource_examples_sparql() -> str:
    """SPARQL-frågeexempel för länkad data-analys."""
    return """# SPARQL - Exempelfrågor

## Grundläggande frågor

### Räkna böcker per år
```sparql
SELECT ?year (COUNT(?book) AS ?count)
WHERE {
  ?book a <http://purl.org/ontology/bibo/Book> ;
        <http://purl.org/dc/terms/date> ?year .
}
GROUP BY ?year
ORDER BY ?year
LIMIT 100
```

### Mest produktiva författare
```sparql
SELECT ?author (COUNT(?work) AS ?count)
WHERE {
  ?work <http://purl.org/dc/terms/creator> ?author .
}
GROUP BY ?author
ORDER BY DESC(?count)
LIMIT 50
```

### Populäraste ämnesorden
```sparql
SELECT ?subject (COUNT(?work) AS ?count)
WHERE {
  ?work <http://purl.org/dc/terms/subject> ?subject .
}
GROUP BY ?subject
ORDER BY DESC(?count)
LIMIT 50
```

## Använda verktygen

### Kör SELECT-fråga
```
sparql_query(query="SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10")
```

### Beskriv en resurs
```
sparql_describe(resource_uri="https://libris.kb.se/bib/12345")
```

### Räkna resultat
```
sparql_count(query="?s a <http://purl.org/ontology/bibo/Book>")
```

### Visa mallar
```
sparql_templates(category="authors")
sparql_templates(category="statistics")
```
"""


@mcp.resource("kb://examples/research")
def resource_examples_research() -> str:
    """Exempelfrågor för forskningspublikationer (Swepub)."""
    return """# Swepub - Forskningspublikationer

## Sök publikationer

### Fritextsökning
```
swepub_search(query="machine learning")
swepub_search(query="klimatförändringar", limit=50)
```

### Sök efter forskare
```
swepub_search_author(author_name="Andersson, Anna")
swepub_search_author(orcid="0000-0002-1825-0097")
```

### Sök efter lärosäte
```
swepub_search_affiliation(organization="Uppsala universitet")
swepub_search_affiliation(organization="KTH")
swepub_search_affiliation(organization="Karolinska Institutet")
```

### Sök efter forskningsämne
```
swepub_search_subject(subject_code="medicin")
swepub_search_subject(subject_code="datavetenskap")
swepub_search_subject(subject_code="historia")
```

## Exportera för referenshantering

### Till Zotero/EndNote (RIS)
```
swepub_export(query="artificial intelligence", format="ris")
```

### Till LaTeX (BibTeX)
```
swepub_export(query="quantum computing", format="bibtex")
```

## SCB forskningsämnen (urval)
- 1 Naturvetenskap
- 2 Teknik
- 3 Medicin och hälsovetenskap
- 4 Lantbruksvetenskap
- 5 Samhällsvetenskap
- 6 Humaniora
"""


@mcp.resource("kb://data/objecttypes")
def resource_object_types() -> str:
    """Lista över objekttyper i K-samsök."""
    return """# K-samsök - Objekttyper (itemType)

## Vanliga objekttyper

| Typ | Beskrivning |
|-----|-------------|
| `Photograph` | Fotografier |
| `Painting` | Målningar |
| `Drawing` | Teckningar |
| `Print` | Grafik, tryck |
| `Sculpture` | Skulpturer |
| `Building` | Byggnader |
| `Runestone` | Runstenar |
| `Map` | Kartor |
| `Coin` | Mynt |
| `Medal` | Medaljer |
| `Seal` | Sigill |
| `Document` | Dokument |
| `Letter` | Brev |
| `Book` | Böcker |
| `Manuscript` | Handskrifter |
| `Music` | Musikalier |
| `Film` | Filmer |
| `Sound` | Ljudinspelningar |
| `Object` | Föremål (generellt) |
| `Textile` | Textilier |
| `Furniture` | Möbler |
| `Tool` | Verktyg |
| `Weapon` | Vapen |
| `Ship` | Skepp, båtar |
| `Vehicle` | Fordon |

## Användning
```
ksamsok_search_type(item_type="Photograph")
ksamsok_search(query="itemType=Runestone")
```

## Kombinera med andra filter
```
ksamsok_search(query="itemType=Photograph AND countyName=\\"Uppsala län\\"")
ksamsok_search(query="itemType=Building AND fromTime>=1600")
```
"""


# ============================================================================
# MCP PROMPTS - Fördefinierade promptmallar
# ============================================================================

@mcp.prompt()
def prompt_find_books_by_author(author_name: str) -> str:
    """Hitta alla böcker av en specifik författare."""
    return f"""Jag vill hitta alla böcker av författaren {author_name}.

Gör följande:
1. Använd `libris_search_author` för att söka efter författaren
2. Visa de viktigaste verken med titel, år och förlag
3. Om det finns många träffar, sammanfatta de mest betydelsefulla verken
4. Nämn om det finns översättningar eller olika utgåvor

Börja sökningen nu."""


@mcp.prompt()
def prompt_research_topic(topic: str) -> str:
    """Utforska ett ämne med hjälp av KB:s resurser."""
    return f"""Jag vill utforska ämnet "{topic}" genom KB:s databaser.

Gör en omfattande sökning:

1. **Böcker (Libris)**
   - Sök efter böcker om ämnet med `libris_search_subject`
   - Notera viktiga författare och verk

2. **Kulturarv (K-samsök)**
   - Sök efter relaterade kulturarvsobjekt med `ksamsok_search`
   - Leta efter fotografier, konstverk eller föremål

3. **Forskning (Swepub)**
   - Sök efter akademiska publikationer med `swepub_search`
   - Identifiera ledande forskare inom området

4. **Sammanfattning**
   - Ge en översikt av vad som finns tillgängligt
   - Rekommendera de mest relevanta källorna

Börja utforskningen nu."""


@mcp.prompt()
def prompt_genealogy_search(parish: str, county: str = "") -> str:
    """Sök släktforskningsrelaterat material."""
    location_info = f"socknen {parish}"
    if county:
        location_info += f" i {county}"

    return f"""Jag bedriver släktforskning och söker material från {location_info}.

Hjälp mig hitta:

1. **Historiska fotografier**
   ```
   ksamsok_search_location(parish="{parish}", item_type="Photograph")
   ```

2. **Kartor över området**
   ```
   ksamsok_search(query='itemType=Map AND parishName="{parish}"')
   ```

3. **Kyrkliga dokument och byggnader**
   ```
   ksamsok_search(query='text=kyrka AND parishName="{parish}"')
   ```

4. **Gravstenar och minnesmärken**
   ```
   ksamsok_search(query='text=grav AND parishName="{parish}"')
   ```

Visa resultat med bilder när det finns tillgängligt. Fokusera på material som kan vara relevant för släktforskning."""


@mcp.prompt()
def prompt_cultural_heritage_location(county: str) -> str:
    """Utforska kulturarvet i ett specifikt län."""
    return f"""Jag vill utforska kulturarvet i {county}.

Gör en systematisk genomgång:

1. **Översikt - Vad finns?**
   - Använd `ksamsok_statistics(index="itemType", query='countyName="{county}"')`
   - Visa fördelningen av olika objekttyper

2. **Runstenar och fornminnen**
   ```
   ksamsok_search_location(county="{county}", item_type="Runestone")
   ```

3. **Historiska byggnader**
   ```
   ksamsok_search_location(county="{county}", item_type="Building")
   ```

4. **Fotografier och bilder**
   ```
   ksamsok_search_type(item_type="Photograph", has_image=True)
   ```
   Filtrera på {county}

5. **Konst och målningar**
   ```
   ksamsok_search_location(county="{county}", item_type="Painting")
   ```

Sammanfatta de mest intressanta fynden och ge rekommendationer för vidare utforskning."""


@mcp.prompt()
def prompt_export_bibliography(topic: str, format: str = "ris") -> str:
    """Skapa en bibliografi för ett ämne."""
    format_info = "RIS (för Zotero/EndNote)" if format == "ris" else "BibTeX (för LaTeX)"

    return f"""Jag behöver en bibliografi om "{topic}" i {format_info}-format.

Gör följande:

1. **Sök litteratur**
   - Sök i Libris med `libris_search_subject(subject="{topic}")`
   - Identifiera de viktigaste verken

2. **Inkludera forskning**
   - Sök i Swepub med `swepub_search(query="{topic}")`
   - Hitta relevanta akademiska publikationer

3. **Exportera**
   - Använd `export_subject_bibliography(subject="{topic}", format="{format}")`
   - Alternativt `swepub_export(query="{topic}", format="{format}")`

4. **Leverera**
   - Visa den exporterade bibliografin
   - Förklara hur man importerar till referenshanterare

Skapa bibliografin nu."""


@mcp.prompt()
def prompt_sparql_analysis(analysis_type: str = "statistics") -> str:
    """Utför dataanalys med SPARQL."""
    return f"""Jag vill göra en {analysis_type}-analys av Libris data med SPARQL.

## Tillgängliga analystyper

1. **Visa mallar först**
   ```
   sparql_templates(category="{analysis_type}")
   ```

2. **Kör analysen**
   - Använd lämplig mall eller skapa egen fråga
   - Använd `sparql_query()` för att köra

3. **Tolka resultaten**
   - Förklara vad datan visar
   - Identifiera mönster och trender

## Förslag på analyser
- `books` - Böcker per år
- `authors` - Mest produktiva författare
- `subjects` - Populäraste ämnesorden
- `statistics` - Övergripande databasstatistik

Börja med att visa relevanta mallar och sedan köra analysen."""


@mcp.prompt()
def prompt_time_period_search(from_year: int, to_year: int) -> str:
    """Utforska en specifik tidsperiod."""
    return f"""Jag vill utforska perioden {from_year}-{to_year} i svenska samlingar.

## Sökplan

1. **Litteratur från perioden (Libris)**
   ```
   libris_find(query="år:[{from_year} TO {to_year}]", limit=20)
   ```

2. **Kulturarvsobjekt (K-samsök)**
   ```
   ksamsok_search_time(from_year={from_year}, to_year={to_year}, limit=20)
   ```

3. **Fotografier (om relevant)**
   ```
   ksamsok_search_time(from_year={from_year}, to_year={to_year}, item_type="Photograph")
   ```

4. **Byggnader från perioden**
   ```
   ksamsok_search_time(from_year={from_year}, to_year={to_year}, item_type="Building")
   ```

5. **Sammanfattning**
   - Beskriv de viktigaste fynden
   - Ge historisk kontext
   - Rekommendera fördjupning

Starta utforskningen av perioden {from_year}-{to_year}."""


@mcp.prompt()
def prompt_compare_institutions(institution1: str, institution2: str) -> str:
    """Jämför forskningsproduktion mellan två lärosäten."""
    return f"""Jämför forskningsproduktionen mellan {institution1} och {institution2}.

## Analys

1. **{institution1}**
   ```
   swepub_search_affiliation(organization="{institution1}", limit=30)
   ```

2. **{institution2}**
   ```
   swepub_search_affiliation(organization="{institution2}", limit=30)
   ```

3. **Jämförelse**
   - Antal publikationer
   - Forskningsområden
   - Framstående forskare
   - Publikationstyper

4. **Sammanfattning**
   - Likheter och skillnader
   - Styrkeområden för respektive lärosäte

Genomför jämförelsen nu."""


# ============================================================================
# 1. LIBRIS XSEARCH (5 verktyg)
# ============================================================================

@mcp.tool()
async def libris_search(
    query: str = Field(description="Sökfråga, t.ex. 'Astrid Lindgren' eller 'Pippi Långstrump'"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat (1-200)"),
    offset: int = Field(default=0, ge=0, description="Börja från resultat nummer"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Enkel fritextsökning i Libris bibliotekskatalog.
    Söker i titel, författare, ämnesord etc. Returnerar bibliografiska poster.
    """
    try:
        params = {
            "query": query,
            "n": limit,
            "start": offset,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        return format_libris_results(data, format)
        
    except Exception as e:
        return handle_api_error(e, "libris_search")


@mcp.tool()
async def libris_search_author(
    author_name: str = Field(description="Författarens namn, t.ex. 'Strindberg, August' eller 'Lagerlöf'"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat"),
    sort_order: str = Field(default="date_desc", description="Sortering: 'date_desc', 'date_asc', 'title'")
) -> str:
    """
    Sök verk av en specifik författare i Libris.
    Använder författarfältet för exakt matchning.
    """
    try:
        query = f"författare:{author_name}"
        params = {
            "query": query,
            "n": limit,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        return format_libris_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "libris_search_author")


@mcp.tool()
async def libris_search_title(
    title: str = Field(description="Verkets titel, t.ex. 'Röda rummet' eller 'Nils Holgersson'"),
    exact_match: bool = Field(default=False, description="Kräv exakt titelmatchning"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat")
) -> str:
    """
    Sök efter en specifik boktitel i Libris.
    Hittar alla utgåvor och översättningar av verket.
    """
    try:
        if exact_match:
            query = f'titel:"{title}"'
        else:
            query = f"titel:{title}"
        
        params = {
            "query": query,
            "n": limit,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        return format_libris_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "libris_search_title")


@mcp.tool()
async def libris_search_subject(
    subject: str = Field(description="Ämnesord, t.ex. 'vikingatiden', 'klimatförändringar', 'svenska språket'"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat")
) -> str:
    """
    Sök efter böcker inom ett specifikt ämne.
    Använder kontrollerade ämnesord från Svenska ämnesord.
    """
    try:
        query = f"ämne:{subject}"
        params = {
            "query": query,
            "n": limit,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        return format_libris_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "libris_search_subject")


@mcp.tool()
async def libris_search_isbn(
    isbn: str = Field(description="ISBN-nummer (10 eller 13 siffror), t.ex. '9789113084718'")
) -> str:
    """
    Sök efter en bok via dess ISBN-nummer.
    Returnerar exakt den bok som matchar ISBN.
    """
    try:
        # Rensa ISBN från bindestreck och mellanslag
        isbn_clean = isbn.replace("-", "").replace(" ", "")
        
        params = {
            "query": f"isbn:{isbn_clean}",
            "n": 1,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        return format_libris_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "libris_search_isbn")


# ============================================================================
# 2. LIBRIS XL REST (6 verktyg)
# ============================================================================

@mcp.tool()
async def libris_get_record(
    record_id: str = Field(description="Libris post-ID, t.ex. 'bib/12345' eller bara '12345'"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Hämta en specifik bibliografisk post från Libris via dess ID.
    Returnerar fullständig metadata i JSON-LD format.
    """
    try:
        # Normalisera ID
        if not record_id.startswith(("http", "/")):
            record_id = f"/{record_id}"
        
        url = f"{URLS['libris_xl']}{record_id}"
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        # Markdown-formatering
        main_entity = data.get("mainEntity", data.get("@graph", [{}])[0] if "@graph" in data else data)
        
        lines = ["## Libris Post"]
        
        if "hasTitle" in main_entity:
            titles = main_entity["hasTitle"]
            if isinstance(titles, list) and titles:
                title = titles[0].get("mainTitle", "Utan titel")
            else:
                title = titles.get("mainTitle", "Utan titel") if isinstance(titles, dict) else str(titles)
            lines.append(f"**Titel:** {title}")
        
        if "contribution" in main_entity:
            contribs = main_entity["contribution"]
            if isinstance(contribs, list):
                for contrib in contribs[:3]:
                    agent = contrib.get("agent", {})
                    name = agent.get("name", agent.get("@id", ""))
                    role = contrib.get("role", [{}])
                    if isinstance(role, list) and role:
                        role_name = role[0].get("@id", "").split("/")[-1]
                    else:
                        role_name = ""
                    lines.append(f"**{role_name or 'Bidrag'}:** {name}")
        
        if "publication" in main_entity:
            pubs = main_entity["publication"]
            if isinstance(pubs, list) and pubs:
                pub = pubs[0]
                year = pub.get("year", "")
                place = pub.get("place", {}).get("label", "")
                agent = pub.get("agent", {}).get("label", "")
                lines.append(f"**Utgivning:** {place} : {agent}, {year}")
        
        if "identifiedBy" in main_entity:
            for ident in main_entity["identifiedBy"][:5]:
                id_type = ident.get("@type", "")
                value = ident.get("value", "")
                if value:
                    lines.append(f"**{id_type}:** {value}")
        
        lines.append(f"\n**Källa:** {url}")
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_get_record")


@mcp.tool()
async def libris_find(
    query: str = Field(description="Avancerad sökning. Stödjer: AND, OR, NOT, fält:värde. Ex: 'author:Strindberg AND year:[1890 TO 1900]'"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat"),
    offset: int = Field(default=0, ge=0, description="Börja från resultat nummer")
) -> str:
    """
    Avancerad sökning i Libris med boolska operatorer och fältspecifik sökning.
    Stödjer: AND, OR, NOT, parenteser, fält:värde, intervall [min TO max].
    """
    try:
        url = f"{URLS['libris_xl']}/find"
        params = {
            "q": query,
            "_limit": limit,
            "_offset": offset
        }
        
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        total = data.get("totalItems", len(items))
        
        lines = [
            "## Libris Avancerad Sökning",
            f"**Fråga:** `{query}`",
            f"**Totalt:** {total} träffar",
            f"**Visar:** {offset + 1}-{offset + len(items)}",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = "Utan titel"
            if "hasTitle" in item:
                titles = item["hasTitle"]
                if isinstance(titles, list) and titles:
                    title = titles[0].get("mainTitle", "Utan titel")
            
            item_type = item.get("@type", "Okänd")
            item_id = item.get("@id", "")
            
            lines.append(f"### {i}. {title}")
            lines.append(f"- **Typ:** {item_type}")
            lines.append(f"- **ID:** {item_id}")
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_find")


@mcp.tool()
async def libris_get_holdings(
    record_id: str = Field(description="Libris post-ID för att hitta vilka bibliotek som har boken")
) -> str:
    """
    Hämta biblioteksbestånd för en Libris-post.
    Visar vilka bibliotek som har exemplar av boken och tillgänglighet.
    """
    try:
        url = f"{URLS['libris_xl']}/find"
        params = {
            "itemOf.@id": f"https://libris.kb.se/{record_id}",
            "_limit": 50
        }
        
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        
        if not items:
            return f"Inga beståndsposter hittades för {record_id}."
        
        lines = [
            f"## Biblioteksbestånd för {record_id}",
            f"**Antal bibliotek:** {len(items)}",
            ""
        ]
        
        for item in items:
            held_by = item.get("heldBy", {})
            lib_name = held_by.get("name", held_by.get("@id", "Okänt bibliotek"))
            sigel = held_by.get("sigel", "")
            
            lines.append(f"- **{lib_name}** ({sigel})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_get_holdings")


@mcp.tool()
async def libris_get_work(
    work_id: str = Field(description="Verk-ID från Libris, t.ex. 'fnl123456' för att hitta alla utgåvor")
) -> str:
    """
    Hämta information om ett verk och alla dess utgåvor/manifestationer.
    Visar alla tryckningar, översättningar och format av samma verk.
    """
    try:
        url = f"{URLS['libris_xl']}/find"
        params = {
            "instanceOf.@id": f"https://libris.kb.se/{work_id}",
            "_limit": 50
        }
        
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        
        lines = [
            f"## Verk: {work_id}",
            f"**Antal utgåvor:** {len(items)}",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = "Utan titel"
            if "hasTitle" in item:
                titles = item["hasTitle"]
                if isinstance(titles, list) and titles:
                    title = titles[0].get("mainTitle", title)
            
            pub_year = ""
            if "publication" in item:
                pubs = item["publication"]
                if isinstance(pubs, list) and pubs:
                    pub_year = pubs[0].get("year", "")
            
            lines.append(f"{i}. **{title}** ({pub_year})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_get_work")


@mcp.tool()
async def libris_autocomplete(
    prefix: str = Field(description="Början av söktermen för förslag, t.ex. 'strin' → 'Strindberg'"),
    entity_type: str = Field(default="Person", description="Entitetstyp: 'Person', 'Work', 'Subject', 'Organization'")
) -> str:
    """
    Få sökförslag baserat på en prefix-sträng.
    Använd för att hitta rätt namn, titlar eller ämnesord.
    """
    try:
        url = f"{URLS['idkb']}/find"
        params = {
            "q": f"{prefix}*",
            "@type": entity_type,
            "_limit": 10
        }
        
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        
        if not items:
            return f"Inga förslag för '{prefix}' av typen {entity_type}."
        
        lines = [
            f"## Sökförslag för '{prefix}'",
            f"**Typ:** {entity_type}",
            ""
        ]
        
        for item in items:
            name = item.get("prefLabel", item.get("name", item.get("@id", "")))
            lines.append(f"- {name}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_autocomplete")


@mcp.tool()
async def libris_related(
    record_id: str = Field(description="Post-ID för att hitta relaterade verk"),
    relation_type: str = Field(default="all", description="Relationstyp: 'all', 'subject', 'author', 'series'")
) -> str:
    """
    Hitta relaterade verk baserat på ämne, författare eller serie.
    Användbart för att upptäcka liknande litteratur.
    """
    try:
        # Hämta posten först
        url = f"{URLS['libris_xl']}/{record_id}"
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        main = data.get("mainEntity", data.get("@graph", [{}])[0] if "@graph" in data else data)
        
        related_items = []
        
        # Extrahera subjects
        if relation_type in ["all", "subject"]:
            subjects = main.get("subject", [])
            for subj in subjects[:3]:
                subj_id = subj.get("@id", "")
                if subj_id:
                    related_items.append({
                        "type": "Ämne",
                        "id": subj_id,
                        "label": subj.get("prefLabel", subj_id.split("/")[-1])
                    })
        
        # Extrahera författare
        if relation_type in ["all", "author"]:
            contribs = main.get("contribution", [])
            for contrib in contribs[:2]:
                agent = contrib.get("agent", {})
                agent_id = agent.get("@id", "")
                if agent_id:
                    related_items.append({
                        "type": "Författare",
                        "id": agent_id,
                        "label": agent.get("name", agent_id.split("/")[-1])
                    })
        
        if not related_items:
            return f"Inga relaterade poster hittades för {record_id}."
        
        lines = [
            f"## Relaterat till {record_id}",
            ""
        ]
        
        for item in related_items:
            lines.append(f"- **{item['type']}:** {item['label']}")
            lines.append(f"  ID: `{item['id']}`")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "libris_related")


# ============================================================================
# 3. K-SAMSÖK (7 verktyg)
# ============================================================================

@mcp.tool()
async def ksamsok_search(
    query: str = Field(description="CQL-sökning, t.ex. 'text=runsten' eller 'itemType=Photograph'"),
    limit: int = Field(default=10, ge=1, le=500, description="Max antal resultat"),
    start_record: int = Field(default=1, ge=1, description="Börja från post nummer"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Sök kulturarvsobjekt i K-samsök (83 institutioner, 10M+ objekt).
    Använder CQL-syntax. Enkla sökningar: text=värde.
    """
    try:
        params = {
            "method": "search",
            "query": query,
            "hitsPerPage": limit,
            "startRecord": start_record
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        
        return format_ksamsok_results(data, format)
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_search")


@mcp.tool()
async def ksamsok_search_location(
    county: str = Field(default="", description="Län, t.ex. 'Uppsala län', 'Stockholms län'"),
    municipality: str = Field(default="", description="Kommun, t.ex. 'Uppsala', 'Stockholm'"),
    parish: str = Field(default="", description="Socken/Församling"),
    item_type: str = Field(default="", description="Objekttyp, t.ex. 'Photograph', 'Building', 'Runestone'"),
    limit: int = Field(default=20, ge=1, le=500, description="Max antal resultat")
) -> str:
    """
    Sök kulturarvsobjekt inom ett geografiskt område.
    Filtrera på län, kommun, socken och objekttyp.
    """
    try:
        parts = []
        if county:
            parts.append(f'countyName="{county}"')
        if municipality:
            parts.append(f'municipalityName="{municipality}"')
        if parish:
            parts.append(f'parishName="{parish}"')
        if item_type:
            parts.append(f"itemType={item_type}")
        
        if not parts:
            return "Ange minst ett filter: county, municipality, parish eller item_type."
        
        query = " AND ".join(parts)
        
        params = {
            "method": "search",
            "query": query,
            "hitsPerPage": limit,
            "startRecord": 1
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        
        return format_ksamsok_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_search_location")


@mcp.tool()
async def ksamsok_search_type(
    item_type: str = Field(description="Objekttyp: 'Photograph', 'Painting', 'Building', 'Runestone', 'Coin', 'Map', etc."),
    has_image: bool = Field(default=False, description="Kräv att objektet har en bild"),
    has_coordinates: bool = Field(default=False, description="Kräv att objektet har koordinater"),
    limit: int = Field(default=20, ge=1, le=500, description="Max antal resultat")
) -> str:
    """
    Sök kulturarvsobjekt efter typ med möjlighet att filtrera på bild/koordinater.
    Returnerar objekt från museer, arkiv och andra kulturarvsinstitutioner.
    """
    try:
        query = f"itemType={item_type}"
        
        if has_image:
            query += " AND thumbnailExists=true"
        if has_coordinates:
            query += " AND geoDataExists=true"
        
        params = {
            "method": "search",
            "query": query,
            "hitsPerPage": limit,
            "startRecord": 1
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        
        return format_ksamsok_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_search_type")


@mcp.tool()
async def ksamsok_search_time(
    from_year: int = Field(description="Startår, t.ex. 1700"),
    to_year: int = Field(description="Slutår, t.ex. 1800"),
    item_type: str = Field(default="", description="Objekttyp (valfritt)"),
    limit: int = Field(default=20, ge=1, le=500, description="Max antal resultat")
) -> str:
    """
    Sök kulturarvsobjekt från en specifik tidsperiod.
    Hittar föremål, fotografier, byggnader m.m. daterade till angiven period.
    """
    try:
        query = f"fromTime>={from_year} AND toTime<={to_year}"
        
        if item_type:
            query += f" AND itemType={item_type}"
        
        params = {
            "method": "search",
            "query": query,
            "hitsPerPage": limit,
            "startRecord": 1
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        
        return format_ksamsok_results(data, "markdown")
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_search_time")


@mcp.tool()
async def ksamsok_get_object(
    uri: str = Field(description="Objekt-URI, t.ex. 'raa/fmi/10028500550001' eller full URL"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Hämta fullständig information om ett specifikt kulturarvsobjekt.
    Inkluderar beskrivning, bilder, koordinater och relationer.
    """
    try:
        # Normalisera URI
        if not uri.startswith("http"):
            full_uri = f"http://kulturarvsdata.se/{uri}"
        else:
            full_uri = uri
        
        params = {
            "method": "getObject",
            "objectId": full_uri
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        
        # Parsning av enskilt objekt
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        ns = {"ksam": "http://kulturarvsdata.se/ksamsok#"}
        
        rdf = root.find(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")
        if rdf is None:
            return f"Objektet {uri} hittades inte."
        
        obj = {}
        for field, xpath in [
            ("label", ".//ksam:itemLabel"),
            ("description", ".//ksam:itemDescription"),
            ("type", ".//ksam:itemType"),
            ("time_label", ".//ksam:timeLabel"),
            ("place_label", ".//ksam:placeLabel"),
            ("url", ".//ksam:url"),
            ("thumbnail", ".//ksam:thumbnail"),
            ("service", ".//ksam:serviceName"),
        ]:
            elem = rdf.find(xpath, ns)
            if elem is not None:
                obj[field] = elem.text
        
        if format == "json":
            return json.dumps(obj, indent=2, ensure_ascii=False)
        
        lines = [
            f"## {obj.get('label', 'Kulturarvsobjekt')}",
            f"**URI:** {full_uri}",
            ""
        ]
        
        if obj.get("type"):
            lines.append(f"**Typ:** {obj['type']}")
        if obj.get("time_label"):
            lines.append(f"**Tid:** {obj['time_label']}")
        if obj.get("place_label"):
            lines.append(f"**Plats:** {obj['place_label']}")
        if obj.get("description"):
            lines.append(f"\n**Beskrivning:**\n{obj['description']}")
        if obj.get("url"):
            lines.append(f"\n**Webbsida:** {obj['url']}")
        if obj.get("thumbnail"):
            lines.append(f"**Bild:** {obj['thumbnail']}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_get_object")


@mcp.tool()
async def ksamsok_get_relations(
    uri: str = Field(description="Objekt-URI för att hitta relationer"),
    relation_type: str = Field(default="all", description="Relationstyp: 'all', 'sameAs', 'isPartOf', 'isContainedIn'")
) -> str:
    """
    Hämta relationer för ett kulturarvsobjekt.
    Visar kopplingar till andra objekt, personer, platser och händelser.
    """
    try:
        if not uri.startswith("http"):
            full_uri = f"http://kulturarvsdata.se/{uri}"
        else:
            full_uri = uri
        
        params = {
            "method": "getRelations",
            "objectId": full_uri,
            "maxDepth": 1
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        relations = []
        for rel in root.findall(".//relation"):
            rel_type = rel.get("type", "")
            target = rel.get("target", "")
            if relation_type == "all" or rel_type == relation_type:
                relations.append({"type": rel_type, "target": target})
        
        if not relations:
            return f"Inga relationer hittades för {uri}."
        
        lines = [
            f"## Relationer för {uri}",
            f"**Antal:** {len(relations)}",
            ""
        ]
        
        for rel in relations:
            lines.append(f"- **{rel['type']}** → {rel['target']}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_get_relations")


@mcp.tool()
async def ksamsok_statistics(
    index: str = Field(description="Index att visa statistik för: 'serviceOrganization', 'itemType', 'county', 'municipality'"),
    query: str = Field(default="*", description="Begränsa statistiken till en delmängd")
) -> str:
    """
    Hämta statistik och facetter för K-samsök.
    Visar fördelning av objekt per institution, typ, geografiskt område.
    """
    try:
        params = {
            "method": "statistic",
            "index": index,
            "query": query if query != "*" else ""
        }
        
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        
        stats = []
        for term in root.findall(".//term"):
            value = term.get("value", "")
            count = term.get("count", "0")
            stats.append({"value": value, "count": int(count)})
        
        # Sortera efter antal
        stats.sort(key=lambda x: x["count"], reverse=True)
        
        lines = [
            f"## K-samsök Statistik: {index}",
            ""
        ]
        
        for stat in stats[:30]:
            lines.append(f"- **{stat['value']}**: {stat['count']:,} objekt")
        
        if len(stats) > 30:
            lines.append(f"\n*... och {len(stats) - 30} kategorier till*")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "ksamsok_statistics")


# ============================================================================
# 4. OAI-PMH (5 verktyg)
# ============================================================================

@mcp.tool()
async def oaipmh_list_records(
    set_spec: str = Field(default="", description="Delmängd, t.ex. 'bib', 'auth', 'hold'. Lämna tom för alla."),
    metadata_prefix: str = Field(default="oai_dc", description="Metadataformat: 'oai_dc', 'marcxml', 'mods'"),
    from_date: str = Field(default="", description="Från datum (YYYY-MM-DD), t.ex. '2024-01-01'"),
    until_date: str = Field(default="", description="Till datum (YYYY-MM-DD)"),
    limit: int = Field(default=10, ge=1, le=100, description="Max antal poster att visa")
) -> str:
    """
    Hämta poster från Libris via OAI-PMH för bulkexport.
    Använd för att samla stora mängder metadata för analys eller arkivering.
    """
    try:
        params = {
            "verb": "ListRecords",
            "metadataPrefix": metadata_prefix
        }
        
        if set_spec:
            params["set"] = set_spec
        if from_date:
            params["from"] = from_date
        if until_date:
            params["until"] = until_date
        
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        data = parse_oaipmh_xml(response.text)
        
        records = data.get("records", [])[:limit]
        token = data.get("resumption_token")
        
        lines = [
            "## OAI-PMH Poster",
            f"**Set:** {set_spec or 'alla'}",
            f"**Format:** {metadata_prefix}",
            f"**Visar:** {len(records)} poster",
            ""
        ]
        
        for rec in records:
            lines.append(f"- {rec.get('identifier', 'Okänt ID')} ({rec.get('datestamp', '')})")
        
        if token:
            lines.append(f"\n*Fler poster tillgängliga. Resumption token: `{token[:50]}...`*")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "oaipmh_list_records")


@mcp.tool()
async def oaipmh_get_record(
    identifier: str = Field(description="OAI-identifier, t.ex. 'https://libris.kb.se/bib/12345'"),
    metadata_prefix: str = Field(default="oai_dc", description="Metadataformat: 'oai_dc', 'marcxml'")
) -> str:
    """
    Hämta en specifik post via OAI-PMH.
    Returnerar fullständig metadata i valt format.
    """
    try:
        params = {
            "verb": "GetRecord",
            "identifier": identifier,
            "metadataPrefix": metadata_prefix
        }
        
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        
        # Returnera rå XML för GetRecord
        return f"## OAI-PMH Post\n**ID:** {identifier}\n**Format:** {metadata_prefix}\n\n```xml\n{response.text[:3000]}\n```"
        
    except Exception as e:
        return handle_api_error(e, "oaipmh_get_record")


@mcp.tool()
async def oaipmh_list_sets() -> str:
    """
    Lista tillgängliga delmängder (sets) i OAI-PMH.
    Visar vilka samlingar som kan hämtas separat.
    """
    try:
        params = {"verb": "ListSets"}
        
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        data = parse_oaipmh_xml(response.text)
        
        sets = data.get("sets", [])
        
        lines = [
            "## OAI-PMH Tillgängliga Sets",
            f"**Antal:** {len(sets)}",
            ""
        ]
        
        for s in sets:
            lines.append(f"- **{s['spec']}**: {s['name']}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "oaipmh_list_sets")


@mcp.tool()
async def oaipmh_list_formats() -> str:
    """
    Lista tillgängliga metadataformat i OAI-PMH.
    Visar vilka format som stöds för export.
    """
    try:
        params = {"verb": "ListMetadataFormats"}
        
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}
        
        formats = []
        for fmt in root.findall(".//oai:metadataFormat", ns):
            prefix = fmt.find("oai:metadataPrefix", ns)
            schema = fmt.find("oai:schema", ns)
            if prefix is not None:
                formats.append({
                    "prefix": prefix.text,
                    "schema": schema.text if schema is not None else ""
                })
        
        lines = [
            "## OAI-PMH Metadataformat",
            ""
        ]
        
        for fmt in formats:
            lines.append(f"- **{fmt['prefix']}**")
            if fmt['schema']:
                lines.append(f"  Schema: {fmt['schema']}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "oaipmh_list_formats")


@mcp.tool()
async def oaipmh_resume(
    resumption_token: str = Field(description="Resumption token från tidigare anrop för att hämta nästa sida")
) -> str:
    """
    Fortsätt paginering av OAI-PMH-resultat.
    Använd token från tidigare svar för att hämta nästa batch.
    """
    try:
        params = {
            "verb": "ListRecords",
            "resumptionToken": resumption_token
        }
        
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        data = parse_oaipmh_xml(response.text)
        
        records = data.get("records", [])
        next_token = data.get("resumption_token")
        
        lines = [
            "## OAI-PMH Fortsättning",
            f"**Antal poster:** {len(records)}",
            ""
        ]
        
        for rec in records[:20]:
            lines.append(f"- {rec.get('identifier', 'Okänt ID')}")
        
        if len(records) > 20:
            lines.append(f"\n*... och {len(records) - 20} poster till*")
        
        if next_token:
            lines.append(f"\n**Nästa token:** `{next_token[:50]}...`")
        else:
            lines.append("\n*Inga fler poster.*")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "oaipmh_resume")


# ============================================================================
# 5. DATA.KB.SE (5 verktyg)
# ============================================================================

@mcp.tool()
async def kb_data_list_collections(
    path: str = Field(default="", description="Samlingssökväg, t.ex. 'smdb' för ljud/video, 'dark' för webarkiv")
) -> str:
    """
    Lista digitala samlingar på data.kb.se.
    Visar tillgängliga digitaliserade material från KB.
    """
    try:
        url = f"{URLS['kb_data']}/{path}" if path else URLS['kb_data']
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        items = data.get("@graph", [data]) if "@graph" in data else [data]
        
        lines = [
            "## KB Digitala Samlingar",
            f"**Sökväg:** {path or '/'}",
            ""
        ]
        
        for item in items[:20]:
            label = item.get("rdfs:label", item.get("@id", ""))
            item_type = item.get("@type", "")
            if label:
                lines.append(f"- **{label}** ({item_type})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "kb_data_list_collections")


@mcp.tool()
async def kb_data_get_item(
    item_id: str = Field(description="Objekt-ID från data.kb.se, t.ex. 'bib/12345'")
) -> str:
    """
    Hämta ett specifikt digitalt objekt från data.kb.se.
    Returnerar metadata och länkar till digitaliserat innehåll.
    """
    try:
        url = f"{URLS['kb_data']}/{item_id}"
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        lines = [
            f"## Digitalt Objekt: {item_id}",
            ""
        ]
        
        for key, value in data.items():
            if not key.startswith("@") and value:
                if isinstance(value, str):
                    lines.append(f"**{key}:** {value}")
                elif isinstance(value, dict):
                    lines.append(f"**{key}:** {json.dumps(value, ensure_ascii=False)[:100]}")
        
        return "\n".join(lines) if len(lines) > 2 else f"Ingen data hittades för {item_id}."
        
    except Exception as e:
        return handle_api_error(e, "kb_data_get_item")


@mcp.tool()
async def kb_data_search(
    query: str = Field(description="Sökterm för digitaliserat material"),
    collection: str = Field(default="", description="Begränsa till samling: 'smdb', 'dark', etc.")
) -> str:
    """
    Sök i KB:s digitaliserade samlingar.
    Hittar digitaliserade böcker, tidningar, kartor, bilder m.m.
    """
    try:
        # data.kb.se använder SPARQL för sökning
        sparql_query = f"""
        PREFIX dcterms: <http://purl.org/dc/terms/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?item ?title ?description WHERE {{
            ?item dcterms:title ?title .
            OPTIONAL {{ ?item dcterms:description ?description }}
            FILTER(CONTAINS(LCASE(?title), LCASE("{query}")))
        }} LIMIT 20
        """
        
        response = await api_client.post(
            f"{URLS['kb_data']}/sparql",
            data={"query": sparql_query},
            accept="application/sparql-results+json"
        )
        
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        
        lines = [
            f"## Sökning i KB Digitala Samlingar",
            f"**Sökterm:** {query}",
            f"**Resultat:** {len(bindings)}",
            ""
        ]
        
        for binding in bindings:
            title = binding.get("title", {}).get("value", "")
            item = binding.get("item", {}).get("value", "")
            lines.append(f"- **{title}**")
            lines.append(f"  {item}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "kb_data_search")


@mcp.tool()
async def kb_data_get_manifest(
    item_id: str = Field(description="Objekt-ID för att hämta IIIF-manifest")
) -> str:
    """
    Hämta IIIF-manifest för ett digitaliserat objekt.
    Manifestet kan användas för att visa bilder i IIIF-kompatibla visare.
    """
    try:
        url = f"{URLS['kb_data']}/{item_id}/manifest"
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        lines = [
            f"## IIIF Manifest",
            f"**ID:** {data.get('@id', item_id)}",
            f"**Typ:** {data.get('@type', '')}",
            f"**Label:** {data.get('label', '')}",
            ""
        ]
        
        sequences = data.get("sequences", [])
        if sequences:
            canvases = sequences[0].get("canvases", [])
            lines.append(f"**Antal sidor/bilder:** {len(canvases)}")
        
        lines.append(f"\n**Manifest-URL:** {url}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "kb_data_get_manifest")


@mcp.tool()
async def kb_data_get_metadata(
    item_id: str = Field(description="Objekt-ID"),
    format: str = Field(default="jsonld", description="Format: 'jsonld', 'rdf', 'turtle'")
) -> str:
    """
    Hämta metadata för ett digitalt objekt i olika format.
    Stödjer JSON-LD, RDF/XML och Turtle.
    """
    try:
        accept_map = {
            "jsonld": "application/ld+json",
            "rdf": "application/rdf+xml",
            "turtle": "text/turtle"
        }
        
        url = f"{URLS['kb_data']}/{item_id}"
        accept = accept_map.get(format, "application/ld+json")
        
        response = await api_client.get(url, accept=accept)
        
        if format == "jsonld":
            return json.dumps(response.json(), indent=2, ensure_ascii=False)
        else:
            return f"```{format}\n{response.text[:5000]}\n```"
        
    except Exception as e:
        return handle_api_error(e, "kb_data_get_metadata")


# ============================================================================
# 6. SWEPUB (6 verktyg)
# ============================================================================

@mcp.tool()
async def swepub_search(
    query: str = Field(description="Sökterm för svenska forskningspublikationer"),
    limit: int = Field(default=10, ge=1, le=200, description="Max antal resultat"),
    offset: int = Field(default=0, ge=0, description="Börja från resultat nummer")
) -> str:
    """
    Sök svenska forskningspublikationer i Swepub.
    Innehåller avhandlingar, artiklar, rapporter från svenska lärosäten.
    """
    try:
        params = {
            "query": query,
            "database": "swepub",
            "n": limit,
            "start": offset,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        
        xsearch = data.get("xsearch", {})
        records = xsearch.get("records", 0)
        items = xsearch.get("list", [])
        
        lines = [
            "## Swepub Sökresultat",
            f"**Sökterm:** {query}",
            f"**Totalt:** {records} publikationer",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = item.get("title", "Utan titel")
            creator = item.get("creator", "Okänd")
            date = item.get("date", "")
            publisher = item.get("publisher", "")
            
            lines.append(f"### {i}. {title}")
            lines.append(f"- **Författare:** {creator}")
            if date:
                lines.append(f"- **År:** {date}")
            if publisher:
                lines.append(f"- **Lärosäte:** {publisher}")
            lines.append("")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "swepub_search")


@mcp.tool()
async def swepub_search_author(
    author_name: str = Field(description="Forskarens namn, t.ex. 'Johansson, Anna'"),
    orcid: str = Field(default="", description="ORCID-ID (valfritt), t.ex. '0000-0002-1825-0097'")
) -> str:
    """
    Sök publikationer av en specifik forskare.
    Kan använda namn eller ORCID för exakt matchning.
    """
    try:
        if orcid:
            query = f"orcid:{orcid}"
        else:
            query = f"författare:{author_name}"
        
        params = {
            "query": query,
            "database": "swepub",
            "n": 20,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        
        xsearch = data.get("xsearch", {})
        items = xsearch.get("list", [])
        
        lines = [
            f"## Publikationer av {author_name or orcid}",
            f"**Antal:** {len(items)}",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = item.get("title", "Utan titel")
            date = item.get("date", "")
            lines.append(f"{i}. **{title}** ({date})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "swepub_search_author")


@mcp.tool()
async def swepub_search_affiliation(
    organization: str = Field(description="Lärosäte, t.ex. 'Uppsala universitet', 'KTH', 'Karolinska Institutet'"),
    limit: int = Field(default=20, ge=1, le=200, description="Max antal resultat")
) -> str:
    """
    Sök publikationer från ett specifikt lärosäte.
    Visar forskningsoutput från svenska universitet och högskolor.
    """
    try:
        query = f"organisation:{organization}"
        
        params = {
            "query": query,
            "database": "swepub",
            "n": limit,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        
        xsearch = data.get("xsearch", {})
        records = xsearch.get("records", 0)
        items = xsearch.get("list", [])
        
        lines = [
            f"## Publikationer från {organization}",
            f"**Totalt:** {records}",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = item.get("title", "Utan titel")
            creator = item.get("creator", "")
            date = item.get("date", "")
            lines.append(f"{i}. **{title}**")
            if creator:
                lines.append(f"   {creator} ({date})")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "swepub_search_affiliation")


@mcp.tool()
async def swepub_search_subject(
    subject_code: str = Field(description="Ämnesklassning (SCB-kod eller text), t.ex. '101' för matematik eller 'medicin'"),
    limit: int = Field(default=20, ge=1, le=200, description="Max antal resultat")
) -> str:
    """
    Sök publikationer inom ett forskningsämne.
    Använder Sveriges standard för forskningsämnen (SCB-klassning).
    """
    try:
        query = f"ämne:{subject_code}"
        
        params = {
            "query": query,
            "database": "swepub",
            "n": limit,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        
        xsearch = data.get("xsearch", {})
        records = xsearch.get("records", 0)
        items = xsearch.get("list", [])
        
        lines = [
            f"## Publikationer inom {subject_code}",
            f"**Totalt:** {records}",
            ""
        ]
        
        for i, item in enumerate(items, 1):
            title = item.get("title", "Utan titel")
            creator = item.get("creator", "")
            lines.append(f"{i}. **{title}** - {creator}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "swepub_search_subject")


@mcp.tool()
async def swepub_get_publication(
    publication_id: str = Field(description="Publikations-ID eller URL från Swepub")
) -> str:
    """
    Hämta fullständig information om en forskningspublikation.
    Inkluderar abstract, nyckelord, DOI och citatinformation.
    """
    try:
        # Försök hämta via Libris XL
        url = f"{URLS['libris_xl']}/{publication_id}"
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        main = data.get("mainEntity", data.get("@graph", [{}])[0] if "@graph" in data else data)
        
        lines = [
            "## Publikationsdetaljer",
            ""
        ]
        
        if "hasTitle" in main:
            titles = main["hasTitle"]
            if isinstance(titles, list) and titles:
                lines.append(f"**Titel:** {titles[0].get('mainTitle', '')}")
        
        if "summary" in main:
            summary = main["summary"]
            if isinstance(summary, list) and summary:
                lines.append(f"\n**Abstract:**\n{summary[0].get('label', '')[:500]}...")
        
        if "identifiedBy" in main:
            for ident in main["identifiedBy"]:
                id_type = ident.get("@type", "")
                value = ident.get("value", "")
                if id_type in ["DOI", "ISBN", "ISSN"]:
                    lines.append(f"**{id_type}:** {value}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "swepub_get_publication")


@mcp.tool()
async def swepub_export(
    query: str = Field(description="Sökfråga för att exportera publikationer"),
    format: str = Field(default="ris", description="Exportformat: 'ris' (Zotero), 'bibtex' (LaTeX)")
) -> str:
    """
    Exportera Swepub-sökresultat till referenshanteringsformat.
    Använd RIS för Zotero/EndNote eller BibTeX för LaTeX.
    """
    try:
        params = {
            "query": query,
            "database": "swepub",
            "n": 50,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        
        items = data.get("xsearch", {}).get("list", [])
        
        if format == "bibtex":
            return _format_bibtex(items)
        else:
            return _format_ris(items)
        
    except Exception as e:
        return handle_api_error(e, "swepub_export")


def _format_ris(items: list) -> str:
    """Formatera till RIS-format."""
    ris_lines = []
    
    for item in items:
        ris_lines.extend([
            "TY  - JOUR",
            f"TI  - {item.get('title', '')}",
            f"AU  - {item.get('creator', '')}",
            f"PY  - {item.get('date', '')[:4] if item.get('date') else ''}",
            f"PB  - {item.get('publisher', '')}",
            "ER  - ",
            ""
        ])
    
    return "\n".join(ris_lines)


def _format_bibtex(items: list) -> str:
    """Formatera till BibTeX-format."""
    bibtex_lines = []
    
    for i, item in enumerate(items):
        author = item.get('creator', 'Unknown')
        year = item.get('date', '')[:4] if item.get('date') else '0000'
        key = f"{author.split(',')[0].lower() if ',' in author else author.split()[0].lower()}{year}_{i}"
        
        bibtex_lines.extend([
            f"@article{{{key},",
            f"  title = {{{item.get('title', '')}}},",
            f"  author = {{{author}}},",
            f"  year = {{{year}}},",
            f"  publisher = {{{item.get('publisher', '')}}}",
            "}",
            ""
        ])
    
    return "\n".join(bibtex_lines)


# ============================================================================
# 7. ID.KB.SE - Vokabulär (4 verktyg)
# ============================================================================

@mcp.tool()
async def idkb_get_entity(
    entity_path: str = Field(description="Entitetssökväg, t.ex. 'vocab/Person', 'term/sao/Politik'"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Hämta en entitet/begrepp från id.kb.se.
    Returnerar definition, egenskaper och relationer.
    """
    try:
        url = f"{URLS['idkb']}/{entity_path}"
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        
        lines = [
            f"## Entitet: {entity_path}",
            ""
        ]
        
        if "@graph" in data:
            for item in data["@graph"][:5]:
                item_id = item.get("@id", "")
                item_type = item.get("@type", "")
                label = item.get("prefLabel", item.get("label", ""))
                
                if label:
                    lines.append(f"**{label}**")
                    lines.append(f"- Typ: {item_type}")
                    lines.append(f"- ID: {item_id}")
                    lines.append("")
        else:
            for key, value in data.items():
                if not key.startswith("@"):
                    lines.append(f"**{key}:** {value}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "idkb_get_entity")


@mcp.tool()
async def idkb_search(
    query: str = Field(description="Sökterm för auktoriteter och begrepp"),
    entity_type: str = Field(default="", description="Entitetstyp: 'Person', 'Organization', 'Subject', 'Work'"),
    limit: int = Field(default=20, ge=1, le=200, description="Max antal resultat")
) -> str:
    """
    Sök auktoriteter, ämnesord och begrepp i id.kb.se.
    Hittar standardiserade termer för katalogisering.
    """
    try:
        params = {
            "q": query,
            "_limit": limit
        }
        
        if entity_type:
            params["@type"] = entity_type
        
        url = f"{URLS['idkb']}/find"
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        total = data.get("totalItems", len(items))
        
        lines = [
            f"## id.kb.se Sökning",
            f"**Sökterm:** {query}",
            f"**Totalt:** {total} träffar",
            ""
        ]
        
        for item in items[:20]:
            label = item.get("prefLabel", item.get("name", item.get("@id", "").split("/")[-1]))
            item_type = item.get("@type", "")
            item_id = item.get("@id", "")
            
            lines.append(f"- **{label}** ({item_type})")
            lines.append(f"  {item_id}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "idkb_search")


@mcp.tool()
async def idkb_get_vocab_term(
    vocab: str = Field(description="Vokabulär, t.ex. 'sao' (Svenska ämnesord), 'saogf' (Genre/form)"),
    term: str = Field(description="Term att slå upp, t.ex. 'Historia', 'Romaner'")
) -> str:
    """
    Hämta en specifik term från ett kontrollerat vokabulär.
    Visar definition, bredare/smalare termer och relaterade begrepp.
    """
    try:
        url = f"{URLS['idkb']}/term/{vocab}/{term}"
        
        response = await api_client.get(url, accept="application/ld+json")
        data = response.json()
        
        lines = [
            f"## Term: {term}",
            f"**Vokabulär:** {vocab}",
            ""
        ]
        
        if "@graph" in data:
            for item in data["@graph"]:
                if item.get("prefLabel"):
                    lines.append(f"**Föredragen term:** {item['prefLabel']}")
                
                if "altLabel" in item:
                    alt = item["altLabel"]
                    if isinstance(alt, list):
                        lines.append(f"**Alternativa termer:** {', '.join(alt)}")
                    else:
                        lines.append(f"**Alternativ term:** {alt}")
                
                if "broader" in item:
                    broader = item["broader"]
                    if isinstance(broader, dict):
                        lines.append(f"**Bredare term:** {broader.get('@id', '').split('/')[-1]}")
                
                if "narrower" in item:
                    narrower = item["narrower"]
                    if isinstance(narrower, list):
                        terms = [n.get("@id", "").split("/")[-1] for n in narrower[:5]]
                        lines.append(f"**Smalare termer:** {', '.join(terms)}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "idkb_get_vocab_term")


@mcp.tool()
async def idkb_list_vocab(
    vocab: str = Field(description="Vokabulär att lista, t.ex. 'sao', 'saogf', 'barn'"),
    limit: int = Field(default=50, ge=1, le=500, description="Max antal termer")
) -> str:
    """
    Lista termer i ett kontrollerat vokabulär.
    Visar tillgängliga ämnesord, genrer eller andra klassificeringar.
    """
    try:
        url = f"{URLS['idkb']}/find"
        params = {
            "inScheme.@id": f"https://id.kb.se/term/{vocab}",
            "_limit": limit
        }
        
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        
        items = data.get("items", [])
        
        lines = [
            f"## Vokabulär: {vocab}",
            f"**Antal termer:** {len(items)}",
            ""
        ]
        
        for item in items:
            label = item.get("prefLabel", item.get("@id", "").split("/")[-1])
            lines.append(f"- {label}")
        
        return "\n".join(lines)
        
    except Exception as e:
        return handle_api_error(e, "idkb_list_vocab")


# ============================================================================
# 8. SPARQL (4 verktyg)
# ============================================================================

@mcp.tool()
async def sparql_query(
    query: str = Field(description="SPARQL SELECT-fråga för att hämta data från Libris länkade data"),
    format: str = Field(default="markdown", description="Utdataformat: 'markdown' eller 'json'")
) -> str:
    """
    Kör en SPARQL SELECT-fråga mot Libris länkade data.
    Kraftfullt verktyg för komplexa analyser och datautvinning.
    """
    try:
        response = await api_client.post(
            URLS["libris_sparql"],
            data={"query": query},
            accept="application/sparql-results+json"
        )
        
        data = response.json()
        return format_sparql_results(data, format)
        
    except Exception as e:
        return handle_api_error(e, "sparql_query")


@mcp.tool()
async def sparql_describe(
    resource_uri: str = Field(description="URI för resursen att beskriva, t.ex. 'https://libris.kb.se/bib/12345'")
) -> str:
    """
    Beskriv en resurs i RDF-format via SPARQL DESCRIBE.
    Returnerar alla triplar som involverar resursen.
    """
    try:
        query = f"DESCRIBE <{resource_uri}>"
        
        response = await api_client.post(
            URLS["libris_sparql"],
            data={"query": query},
            accept="application/ld+json"
        )
        
        data = response.json()
        return json.dumps(data, indent=2, ensure_ascii=False)[:5000]
        
    except Exception as e:
        return handle_api_error(e, "sparql_describe")


@mcp.tool()
async def sparql_count(
    query: str = Field(description="SPARQL WHERE-klausul att räkna, t.ex. '?s a <http://purl.org/ontology/bibo/Book>'")
) -> str:
    """
    Räkna antal resultat för en SPARQL-pattern.
    Snabbt sätt att få statistik utan att hämta all data.
    """
    try:
        count_query = f"""
        SELECT (COUNT(*) AS ?count) WHERE {{
            {query}
        }}
        """
        
        response = await api_client.post(
            URLS["libris_sparql"],
            data={"query": count_query},
            accept="application/sparql-results+json"
        )
        
        data = response.json()
        bindings = data.get("results", {}).get("bindings", [])
        
        if bindings:
            count = bindings[0].get("count", {}).get("value", "0")
            return f"**Antal:** {int(count):,}"
        
        return "Kunde inte räkna resultat."
        
    except Exception as e:
        return handle_api_error(e, "sparql_count")


@mcp.tool()
async def sparql_templates(
    category: str = Field(default="all", description="Kategori: 'all', 'books', 'authors', 'subjects', 'statistics'")
) -> str:
    """
    Visa fördefinierade SPARQL-frågemallar.
    Använd som utgångspunkt för egna analyser.
    """
    templates = {
        "books": {
            "name": "Böcker per år",
            "query": """SELECT ?year (COUNT(?book) AS ?count)
WHERE {
  ?book a <http://purl.org/ontology/bibo/Book> ;
        <http://purl.org/dc/terms/date> ?year .
}
GROUP BY ?year
ORDER BY ?year
LIMIT 100"""
        },
        "authors": {
            "name": "Mest produktiva författare",
            "query": """SELECT ?author (COUNT(?work) AS ?count)
WHERE {
  ?work <http://purl.org/dc/terms/creator> ?author .
}
GROUP BY ?author
ORDER BY DESC(?count)
LIMIT 50"""
        },
        "subjects": {
            "name": "Populära ämnesord",
            "query": """SELECT ?subject (COUNT(?work) AS ?count)
WHERE {
  ?work <http://purl.org/dc/terms/subject> ?subject .
}
GROUP BY ?subject
ORDER BY DESC(?count)
LIMIT 50"""
        },
        "statistics": {
            "name": "Databasstatistik",
            "query": """SELECT ?type (COUNT(?s) AS ?count)
WHERE {
  ?s a ?type .
}
GROUP BY ?type
ORDER BY DESC(?count)
LIMIT 20"""
        }
    }
    
    if category != "all" and category in templates:
        t = templates[category]
        return f"## {t['name']}\n\n```sparql\n{t['query']}\n```"
    
    lines = ["## SPARQL Frågemallar", ""]
    
    for key, t in templates.items():
        lines.append(f"### {t['name']} (`{key}`)")
        lines.append(f"```sparql\n{t['query']}\n```")
        lines.append("")
    
    return "\n".join(lines)


# ============================================================================
# 9. BIBLIOGRAFI-EXPORT (5 verktyg)
# ============================================================================

@mcp.tool()
async def export_author_bibliography(
    author_name: str = Field(description="Författarens namn, t.ex. 'Lindgren, Astrid'"),
    format: str = Field(default="ris", description="Exportformat: 'ris', 'bibtex', 'markdown'"),
    max_results: int = Field(default=50, ge=1, le=200, description="Max antal verk")
) -> str:
    """
    Exportera en författarbibliografi i referenshanteringsformat.
    Perfekt för att skapa litteraturlistor för akademiskt arbete.
    """
    try:
        params = {
            "query": f"författare:{author_name}",
            "n": max_results,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        items = data.get("xsearch", {}).get("list", [])
        
        if format == "bibtex":
            return _format_bibtex(items)
        elif format == "markdown":
            lines = [f"## Bibliografi: {author_name}", f"**Antal verk:** {len(items)}", ""]
            for i, item in enumerate(items, 1):
                lines.append(f"{i}. {item.get('creator', '')}: *{item.get('title', '')}* ({item.get('date', '')})")
            return "\n".join(lines)
        else:
            return _format_ris(items)
        
    except Exception as e:
        return handle_api_error(e, "export_author_bibliography")


@mcp.tool()
async def export_subject_bibliography(
    subject: str = Field(description="Ämnesord, t.ex. 'klimatförändringar', 'svensk historia'"),
    format: str = Field(default="ris", description="Exportformat: 'ris', 'bibtex'"),
    max_results: int = Field(default=50, ge=1, le=200, description="Max antal verk")
) -> str:
    """
    Exportera en ämnesbibliografi för ett forskningsområde.
    Samlar litteratur inom ett specifikt ämne.
    """
    try:
        params = {
            "query": f"ämne:{subject}",
            "n": max_results,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        items = data.get("xsearch", {}).get("list", [])
        
        if format == "bibtex":
            return _format_bibtex(items)
        else:
            return _format_ris(items)
        
    except Exception as e:
        return handle_api_error(e, "export_subject_bibliography")


@mcp.tool()
async def export_search_results(
    query: str = Field(description="Libris-sökfråga"),
    format: str = Field(default="ris", description="Exportformat: 'ris', 'bibtex', 'json'")
) -> str:
    """
    Exportera godtyckliga sökresultat till referenshanteringsformat.
    Flexibel export för anpassade sökningar.
    """
    try:
        params = {
            "query": query,
            "n": 100,
            "format": "json",
            "format_extended": "true"
        }
        
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        items = data.get("xsearch", {}).get("list", [])
        
        if format == "json":
            return json.dumps(items, indent=2, ensure_ascii=False)
        elif format == "bibtex":
            return _format_bibtex(items)
        else:
            return _format_ris(items)
        
    except Exception as e:
        return handle_api_error(e, "export_search_results")


@mcp.tool()
async def export_publication_list(
    record_ids: str = Field(description="Kommaseparerade post-ID:n, t.ex. '12345,67890,11111'"),
    format: str = Field(default="ris", description="Exportformat: 'ris', 'bibtex'")
) -> str:
    """
    Skapa en publikationslista från specifika post-ID:n.
    Använd för att sammanställa handplockade referenser.
    """
    try:
        ids = [id.strip() for id in record_ids.split(",")]
        items = []
        
        for record_id in ids[:20]:  # Max 20 poster
            try:
                params = {
                    "query": f"id:{record_id}",
                    "n": 1,
                    "format": "json",
                    "format_extended": "true"
                }
                response = await api_client.get(URLS["libris_xsearch"], params=params)
                data = response.json()
                item_list = data.get("xsearch", {}).get("list", [])
                if item_list:
                    items.append(item_list[0])
            except Exception:
                continue
        
        if not items:
            return "Inga poster hittades för angivna ID:n."
        
        if format == "bibtex":
            return _format_bibtex(items)
        else:
            return _format_ris(items)
        
    except Exception as e:
        return handle_api_error(e, "export_publication_list")


@mcp.tool()
async def export_formats_info() -> str:
    """
    Visa information om tillgängliga exportformat.
    Beskriver RIS, BibTeX och andra format samt deras användningsområden.
    """
    return """## Exportformat

### RIS (Research Information Systems)
- **Användning:** Zotero, EndNote, Mendeley
- **Filtyp:** .ris
- **Fördel:** Brett stöd i referenshanterare

### BibTeX
- **Användning:** LaTeX-dokument
- **Filtyp:** .bib
- **Fördel:** Standard för akademisk publicering

### JSON
- **Användning:** Programmatisk bearbetning
- **Filtyp:** .json
- **Fördel:** Maskinläsbar, full metadata

### Markdown
- **Användning:** Dokumentation, webbsidor
- **Filtyp:** .md
- **Fördel:** Läsbar, enkelt att formatera

---

**Verktyg för export:**
- `export_author_bibliography` - Författarbibliografi
- `export_subject_bibliography` - Ämnesbibliografi  
- `export_search_results` - Anpassad sökning
- `export_publication_list` - Handplockade ID:n
"""


# ============================================================================
# NYA FÖRBÄTTRADE VERKTYG
# ============================================================================

@mcp.tool()
async def combined_search(
    query: str = Field(description="Sökterm för sökning i flera databaser samtidigt"),
    include_libris: bool = Field(default=True, description="Inkludera Libris (böcker)"),
    include_ksamsok: bool = Field(default=True, description="Inkludera K-samsök (kulturarv)"),
    include_swepub: bool = Field(default=True, description="Inkludera Swepub (forskning)"),
    limit_per_source: int = Field(default=5, ge=1, le=20, description="Max resultat per källa")
) -> str:
    """
    Sök i flera KB-databaser samtidigt med en enda fråga.
    Perfekt för att få en snabb överblick över vad som finns tillgängligt.
    """
    results = []

    # Libris
    if include_libris:
        try:
            params = {"query": query, "n": limit_per_source, "format": "json", "format_extended": "true"}
            response = await api_client.get(URLS["libris_xsearch"], params=params)
            data = response.json()
            xsearch = data.get("xsearch", {})
            total = xsearch.get("records", 0)
            items = xsearch.get("list", [])

            results.append(f"## 📚 Libris (böcker & media)")
            results.append(f"**Totalt:** {total} träffar\n")
            for i, item in enumerate(items, 1):
                title = item.get("title", "Utan titel")
                creator = item.get("creator", "Okänd")
                date = item.get("date", "")
                results.append(f"{i}. **{title}** - {creator} ({date})")
            results.append("")
        except Exception as e:
            results.append(f"## 📚 Libris\n❌ Fel: {e}\n")

    # K-samsök
    if include_ksamsok:
        try:
            params = {"method": "search", "query": f"text={query}", "hitsPerPage": limit_per_source}
            response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
            data = parse_ksamsok_xml(response.text)
            total = data.get("total_hits", 0)
            records = data.get("records", [])

            results.append(f"## 🏛️ K-samsök (kulturarv)")
            results.append(f"**Totalt:** {total} objekt\n")
            for i, record in enumerate(records, 1):
                label = record.get("label", "Utan benämning")
                obj_type = record.get("type", "Okänd typ")
                results.append(f"{i}. **{label}** ({obj_type})")
            results.append("")
        except Exception as e:
            results.append(f"## 🏛️ K-samsök\n❌ Fel: {e}\n")

    # Swepub
    if include_swepub:
        try:
            params = {"query": query, "database": "swepub", "n": limit_per_source, "format": "json"}
            response = await api_client.get(URLS["swepub"], params=params)
            data = response.json()
            xsearch = data.get("xsearch", {})
            total = xsearch.get("records", 0)
            items = xsearch.get("list", [])

            results.append(f"## 🎓 Swepub (forskning)")
            results.append(f"**Totalt:** {total} publikationer\n")
            for i, item in enumerate(items, 1):
                title = item.get("title", "Utan titel")
                creator = item.get("creator", "Okänd")
                results.append(f"{i}. **{title}** - {creator}")
            results.append("")
        except Exception as e:
            results.append(f"## 🎓 Swepub\n❌ Fel: {e}\n")

    if not results:
        return "Inga sökningar utförda. Aktivera minst en datakälla."

    return f"# Kombinerad sökning: \"{query}\"\n\n" + "\n".join(results)


@mcp.tool()
async def swedish_counties_info() -> str:
    """
    Visa lista över alla svenska län med K-samsök-kompatibla namn.
    Användbart för geografiska sökningar i kulturarvsdata.
    """
    return """## Svenska län (för K-samsök)

| Län | Sökterm |
|-----|---------|
| Blekinge | `countyName="Blekinge län"` |
| Dalarna | `countyName="Dalarnas län"` |
| Gotland | `countyName="Gotlands län"` |
| Gävleborg | `countyName="Gävleborgs län"` |
| Halland | `countyName="Hallands län"` |
| Jämtland | `countyName="Jämtlands län"` |
| Jönköping | `countyName="Jönköpings län"` |
| Kalmar | `countyName="Kalmar län"` |
| Kronoberg | `countyName="Kronobergs län"` |
| Norrbotten | `countyName="Norrbottens län"` |
| Skåne | `countyName="Skåne län"` |
| Stockholm | `countyName="Stockholms län"` |
| Södermanland | `countyName="Södermanlands län"` |
| Uppsala | `countyName="Uppsala län"` |
| Värmland | `countyName="Värmlands län"` |
| Västerbotten | `countyName="Västerbottens län"` |
| Västernorrland | `countyName="Västernorrlands län"` |
| Västmanland | `countyName="Västmanlands län"` |
| Västra Götaland | `countyName="Västra Götalands län"` |
| Örebro | `countyName="Örebro län"` |
| Östergötland | `countyName="Östergötlands län"` |

## Exempel
```
ksamsok_search_location(county="Uppsala län")
ksamsok_search(query='countyName="Gotlands län" AND itemType=Runestone')
```
"""


@mcp.tool()
async def quick_stats() -> str:
    """
    Hämta snabbstatistik från alla KB-databaser.
    Visar aktuell status och datavolym för varje API.
    """
    lines = ["## KB API Snabbstatistik\n"]

    # Test Libris
    try:
        params = {"query": "*", "n": 1, "format": "json"}
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        total = data.get("xsearch", {}).get("records", 0)
        lines.append(f"📚 **Libris:** {total:,} bibliografiska poster ✅")
    except Exception:
        lines.append("📚 **Libris:** Otillgänglig ❌")

    # Test K-samsök
    try:
        params = {"method": "search", "query": "*", "hitsPerPage": 1}
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        total = data.get("total_hits", 0)
        lines.append(f"🏛️ **K-samsök:** {total:,} kulturarvsobjekt ✅")
    except Exception:
        lines.append("🏛️ **K-samsök:** Otillgänglig ❌")

    # Test Swepub
    try:
        params = {"query": "*", "database": "swepub", "n": 1, "format": "json"}
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        total = data.get("xsearch", {}).get("records", 0)
        lines.append(f"🎓 **Swepub:** {total:,} forskningspublikationer ✅")
    except Exception:
        lines.append("🎓 **Swepub:** Otillgänglig ❌")

    # Test id.kb.se
    try:
        params = {"q": "*", "_limit": 1}
        response = await api_client.get(f"{URLS['idkb']}/find", params=params, accept="application/ld+json")
        data = response.json()
        total = data.get("totalItems", 0)
        lines.append(f"📖 **id.kb.se:** {total:,} auktoriteter ✅")
    except Exception:
        lines.append("📖 **id.kb.se:** Otillgänglig ❌")

    lines.append("\n---")
    lines.append("*Statistik hämtad i realtid från KB:s servrar*")

    return "\n".join(lines)


@mcp.tool()
async def find_related_works(
    title: str = Field(description="Titel på verket att hitta relaterade verk till"),
    relation_type: str = Field(default="subject", description="Typ av relation: 'subject' (samma ämne), 'author' (samma författare), 'both'")
) -> str:
    """
    Hitta verk som är relaterade till ett givet verk baserat på ämne eller författare.
    Bra för att upptäcka liknande litteratur.
    """
    try:
        # Först hitta originalverket
        params = {"query": f"titel:{title}", "n": 1, "format": "json", "format_extended": "true"}
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        items = data.get("xsearch", {}).get("list", [])

        if not items:
            return f"Hittade inget verk med titeln '{title}'."

        original = items[0]
        original_title = original.get("title", title)
        original_creator = original.get("creator", "")
        original_subject = original.get("subject", [])

        lines = [
            f"## Relaterade verk till: {original_title}",
            f"**Författare:** {original_creator}",
            ""
        ]

        related_items = []

        # Sök på ämne
        if relation_type in ["subject", "both"] and original_subject:
            first_subject = original_subject[0] if isinstance(original_subject, list) else original_subject
            params = {"query": f"ämne:{first_subject}", "n": 10, "format": "json", "format_extended": "true"}
            response = await api_client.get(URLS["libris_xsearch"], params=params)
            data = response.json()
            subject_items = data.get("xsearch", {}).get("list", [])

            lines.append(f"### Samma ämne ({first_subject})")
            for item in subject_items[:5]:
                if item.get("title") != original_title:
                    lines.append(f"- **{item.get('title')}** - {item.get('creator', 'Okänd')} ({item.get('date', '')})")
            lines.append("")

        # Sök på författare
        if relation_type in ["author", "both"] and original_creator:
            params = {"query": f"författare:{original_creator}", "n": 10, "format": "json", "format_extended": "true"}
            response = await api_client.get(URLS["libris_xsearch"], params=params)
            data = response.json()
            author_items = data.get("xsearch", {}).get("list", [])

            lines.append(f"### Samma författare ({original_creator})")
            for item in author_items[:5]:
                if item.get("title") != original_title:
                    lines.append(f"- **{item.get('title')}** ({item.get('date', '')})")
            lines.append("")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "find_related_works")


@mcp.tool()
async def historical_periods_search(
    period: str = Field(description="Historisk period: 'vikingatid', 'medeltid', 'vasatid', 'stormaktstid', 'frihetstid', 'gustaviansk', '1800-tal', '1900-tal'"),
    item_type: str = Field(default="", description="Objekttyp att filtrera på (valfritt)"),
    limit: int = Field(default=20, ge=1, le=100, description="Max antal resultat")
) -> str:
    """
    Sök kulturarvsobjekt från specifika historiska perioder i svensk historia.
    Använder fördefinierade årtal för varje period.
    """
    periods = {
        "vikingatid": (800, 1100, "Vikingatiden"),
        "medeltid": (1100, 1520, "Medeltiden"),
        "vasatid": (1520, 1611, "Vasatiden"),
        "stormaktstid": (1611, 1721, "Stormaktstiden"),
        "frihetstid": (1721, 1772, "Frihetstiden"),
        "gustaviansk": (1772, 1809, "Gustavianska tiden"),
        "1800-tal": (1800, 1899, "1800-talet"),
        "1900-tal": (1900, 1999, "1900-talet")
    }

    period_lower = period.lower()
    if period_lower not in periods:
        available = ", ".join(periods.keys())
        return f"Okänd period: '{period}'. Tillgängliga: {available}"

    from_year, to_year, period_name = periods[period_lower]

    try:
        query = f"fromTime>={from_year} AND toTime<={to_year}"
        if item_type:
            query += f" AND itemType={item_type}"

        params = {
            "method": "search",
            "query": query,
            "hitsPerPage": limit,
            "startRecord": 1
        }

        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)

        total = data.get("total_hits", 0)
        records = data.get("records", [])

        lines = [
            f"## {period_name} ({from_year}-{to_year})",
            f"**Totalt:** {total:,} objekt",
            ""
        ]

        if item_type:
            lines.insert(2, f"**Objekttyp:** {item_type}")

        for i, record in enumerate(records, 1):
            label = record.get("label", "Utan benämning")
            obj_type = record.get("type", "")
            service = record.get("service", "")
            lines.append(f"{i}. **{label}**")
            if obj_type:
                lines.append(f"   Typ: {obj_type}")
            if service:
                lines.append(f"   Källa: {service}")

        return "\n".join(lines)

    except Exception as e:
        return handle_api_error(e, "historical_periods_search")


# ============================================================================
# 10. HJÄLP & METADATA (5 verktyg)
# ============================================================================

@mcp.tool()
async def kb_api_info() -> str:
    """
    Visa översikt över alla tillgängliga KB API:er och verktyg.
    Startpunkt för att förstå vad som finns tillgängligt.
    """
    return """## Kungliga bibliotekets öppna API:er

### 📚 Biblioteksdata (Libris)
- **libris_search**: Enkel sökning i 20M+ poster
- **libris_search_author/title/subject/isbn**: Specifik sökning
- **libris_find**: Avancerad sökning med operatorer
- **libris_get_record/holdings/work**: Hämta specifik data

### 🏛️ Kulturarv (K-samsök)
- **ksamsok_search**: Sök 10M+ objekt från 83 institutioner
- **ksamsok_search_location/type/time**: Filtrerad sökning
- **ksamsok_get_object/relations/statistics**: Detaljerad data

### 📥 Bulkexport (OAI-PMH)
- **oaipmh_list_records/sets/formats**: Hämta metadata i bulk
- **oaipmh_get_record/resume**: Enskilda poster och paginering

### 🎞️ Digitalt (data.kb.se)
- **kb_data_list_collections/get_item/search**: Digitaliserat material
- **kb_data_get_manifest/metadata**: IIIF och metadata

### 🎓 Forskning (Swepub)
- **swepub_search**: Svenska forskningspublikationer
- **swepub_search_author/affiliation/subject**: Specifik sökning
- **swepub_export**: Export till Zotero/BibTeX

### 📖 Vokabulär (id.kb.se)
- **idkb_search/get_entity**: Auktoriteter och begrepp
- **idkb_get_vocab_term/list_vocab**: Kontrollerade termer

### 🔍 Länkad Data (SPARQL)
- **sparql_query/describe/count**: RDF-frågor
- **sparql_templates**: Fördefinierade frågor

### 📤 Export
- **export_author/subject_bibliography**: Bibliografier
- **export_search_results/publication_list**: Anpassad export

---
**Totalt:** 52 verktyg | **Data:** 20M+ bibliografiska poster, 10M+ kulturarvsobjekt
"""


@mcp.tool()
async def kb_api_status(
    api_name: str = Field(default="all", description="API att kontrollera: 'libris', 'ksamsok', 'idkb', 'all'")
) -> str:
    """
    Kontrollera status för KB:s API:er.
    Verifierar att tjänsterna är tillgängliga.
    """
    statuses = []
    
    apis_to_check = {
        "libris": (URLS["libris_xsearch"], {"query": "test", "n": 1, "format": "json"}),
        "ksamsok": (URLS["ksamsok"], {"method": "search", "query": "text=test", "hitsPerPage": 1}),
        "idkb": (f"{URLS['idkb']}/find", {"q": "test", "_limit": 1}),
    }
    
    if api_name != "all":
        if api_name in apis_to_check:
            apis_to_check = {api_name: apis_to_check[api_name]}
        else:
            return f"Okänt API: {api_name}. Välj bland: libris, ksamsok, idkb, all"
    
    for name, (url, params) in apis_to_check.items():
        try:
            await api_client.get(url, params=params, accept="application/json")
            statuses.append(f"✅ **{name}**: Tillgänglig")
        except Exception as e:
            statuses.append(f"❌ **{name}**: Otillgänglig ({type(e).__name__})")
    
    return "## API Status\n\n" + "\n".join(statuses)


@mcp.tool()
async def kb_search_tips(
    api_name: str = Field(default="libris", description="API: 'libris', 'ksamsok', 'sparql'")
) -> str:
    """
    Visa söktips och syntax för ett specifikt API.
    Hjälper till att formulera effektiva sökfrågor.
    """
    tips = {
        "libris": """## Libris Söktips

### Fältsökning
- `titel:Röda rummet` - Sök i titel
- `författare:Strindberg` - Sök författare
- `ämne:historia` - Sök ämnesord
- `isbn:9789113084718` - Exakt ISBN

### Operatorer
- `AND` / `OCH` - Båda termerna krävs
- `OR` / `ELLER` - Någon av termerna
- `NOT` / `INTE` - Exkludera term
- `"exakt fras"` - Exakt matchning

### Trunkering
- `histor*` - Matchar historia, historisk, etc.

### Exempel
- `författare:Lindgren AND titel:Pippi`
- `ämne:"svensk historia" NOT krig`
""",
        "ksamsok": """## K-samsök Söktips (CQL)

### Enkel sökning
- `text=runsten` - Fritext
- `itemType=Photograph` - Objekttyp

### Geografisk
- `countyName="Uppsala län"` - Län
- `municipalityName=Stockholm` - Kommun
- `parishName=Alsike` - Socken

### Tid
- `fromTime>=1700` - Från år
- `toTime<=1800` - Till år

### Filter
- `thumbnailExists=true` - Har bild
- `geoDataExists=true` - Har koordinater

### Operatorer
- `AND` - Båda krävs
- `OR` - Någon av

### Exempel
- `text=vikingasvärd AND countyName="Gotlands län"`
- `itemType=Building AND fromTime>=1600 AND toTime<=1700`
""",
        "sparql": """## SPARQL Tips

### Grundläggande
```sparql
SELECT ?s ?p ?o WHERE {
  ?s ?p ?o .
} LIMIT 10
```

### Prefix
```sparql
PREFIX dc: <http://purl.org/dc/terms/>
PREFIX bibo: <http://purl.org/ontology/bibo/>
```

### Filter
```sparql
FILTER(CONTAINS(?title, "Stockholm"))
FILTER(?year > 2020)
```

### Aggregering
```sparql
SELECT ?author (COUNT(?book) AS ?count)
GROUP BY ?author
ORDER BY DESC(?count)
```

### Tips
- Börja enkelt, bygg på komplexitet
- Använd LIMIT för att testa
- Utnyttja sparql_templates för exempel
"""
    }
    
    return tips.get(api_name, f"Söktips finns för: libris, ksamsok, sparql")


@mcp.tool()
async def kb_data_dictionary(
    entity_type: str = Field(default="book", description="Entitetstyp: 'book', 'person', 'subject', 'cultural_object'")
) -> str:
    """
    Visa datadefinitioner och fältbeskrivningar.
    Hjälper att förstå metadata-strukturen.
    """
    dicts = {
        "book": """## Datadefinition: Bok (Libris)

| Fält | Beskrivning | Exempel |
|------|-------------|---------|
| title | Huvudtitel | "Röda rummet" |
| creator | Upphovsperson | "Strindberg, August" |
| date | Utgivningsår | "1879" |
| publisher | Förlag | "Bonniers" |
| isbn | ISBN-nummer | "9789113084718" |
| identifier | Libris-URI | "https://libris.kb.se/bib/123" |
| subject | Ämnesord | ["Svensk litteratur"] |
| language | Språk | "swe" |
""",
        "person": """## Datadefinition: Person (Auktoritet)

| Fält | Beskrivning | Exempel |
|------|-------------|---------|
| name | Namn | "Lindgren, Astrid" |
| birthYear | Födelseår | "1907" |
| deathYear | Dödsår | "2002" |
| nationality | Nationalitet | "Sverige" |
| occupation | Yrke | "Författare" |
| sameAs | Andra ID | ["VIAF:123", "Wikidata:Q123"] |
""",
        "subject": """## Datadefinition: Ämnesord (SAO)

| Fält | Beskrivning | Exempel |
|------|-------------|---------|
| prefLabel | Föredragen term | "Klimatförändringar" |
| altLabel | Alternativa termer | ["Global uppvärmning"] |
| broader | Bredare term | "Miljöförändringar" |
| narrower | Smalare termer | ["Havsnivåhöjning"] |
| related | Relaterade termer | ["Växthusgaser"] |
| scopeNote | Definition | "Avser..." |
""",
        "cultural_object": """## Datadefinition: Kulturarvsobjekt (K-samsök)

| Fält | Beskrivning | Exempel |
|------|-------------|---------|
| itemLabel | Benämning | "Runsten U 123" |
| itemType | Objekttyp | "Runestone" |
| itemDescription | Beskrivning | "Runsten från..." |
| timeLabel | Tidsperiod | "Vikingatid" |
| placeLabel | Plats | "Uppsala" |
| thumbnailExists | Har bild | true/false |
| geoDataExists | Har koordinater | true/false |
| serviceName | Institution | "Riksantikvarieämbetet" |
"""
    }
    
    return dicts.get(entity_type, f"Datadefinitioner finns för: book, person, subject, cultural_object")


@mcp.tool()
async def kb_example_queries(
    api_name: str = Field(description="API: 'libris', 'ksamsok', 'swepub', 'sparql'"),
    use_case: str = Field(default="general", description="Användningsfall: 'general', 'genealogy', 'research', 'culture'")
) -> str:
    """
    Visa exempelfrågor för vanliga användningsfall.
    Inspiration och startpunkt för egna sökningar.
    """
    examples = {
        ("libris", "general"): """## Libris Exempel

**Hitta alla böcker av en författare:**
```
libris_search_author(author_name="Lagerlöf, Selma")
```

**Sök böcker om ett ämne:**
```
libris_search_subject(subject="vikingatiden")
```

**Avancerad sökning:**
```
libris_find(query="titel:Stockholm AND år:[1900 TO 1950]")
```
""",
        ("ksamsok", "genealogy"): """## K-samsök för Släktforskning

**Fotografier från en socken:**
```
ksamsok_search(query='itemType=Photograph AND parishName="Alsike"')
```

**Historiska kartor över en kommun:**
```
ksamsok_search(query='itemType=Map AND municipalityName="Uppsala"')
```

**Gravstenar med bild:**
```
ksamsok_search(query='text=gravsten AND thumbnailExists=true')
```
""",
        ("swepub", "research"): """## Swepub för Forskning

**Hitta publikationer inom ett fält:**
```
swepub_search_subject(subject_code="medicin")
```

**En forskares publikationer:**
```
swepub_search_author(author_name="Andersson, Anna")
```

**Exportera till Zotero:**
```
swepub_export(query="ämne:AI", format="ris")
```
""",
        ("sparql", "general"): """## SPARQL Exempel

**Räkna böcker per år:**
```
sparql_query(query='''
SELECT ?year (COUNT(?book) AS ?count)
WHERE {
  ?book a <http://purl.org/ontology/bibo/Book> ;
        <http://purl.org/dc/terms/date> ?year .
}
GROUP BY ?year ORDER BY ?year
''')
```

**Författare med flest verk:**
```
sparql_templates(category="authors")
```
"""
    }
    
    key = (api_name, use_case)
    if key in examples:
        return examples[key]
    
    # Fallback
    general_key = (api_name, "general")
    if general_key in examples:
        return examples[general_key]
    
    return f"Exempel finns för kombinationer av api_name (libris, ksamsok, swepub, sparql) och use_case (general, genealogy, research, culture)"


# ============================================================================
# SERVER RUNNERS
# ============================================================================

def run_stdio():
    """Kör servern med stdio-transport (för Claude Desktop, Claude Code)."""
    mcp.run(transport="stdio")


def run_http(host: str = "0.0.0.0", port: int = 8000):
    """Kör servern med HTTP-transport (för remote access, Render deployment)."""
    import uvicorn
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.responses import JSONResponse
    
    async def health(request):
        return JSONResponse({"status": "healthy", "server": "kb-api", "version": "2.0.0"})
    
    async def info(request):
        return JSONResponse({
            "name": "kb-api",
            "version": "2.0.0",
            "description": "Kungliga bibliotekets öppna API:er via MCP",
            "tools": 52,
            "endpoints": ["libris", "ksamsok", "oaipmh", "data.kb.se", "swepub", "id.kb.se", "sparql"]
        })
    
    # Hämta FastMCP:s SSE-app
    sse_app = mcp.sse_app()
    
    # Skapa Starlette-app med egna routes och mount SSE
    app = Starlette(
        debug=False,
        routes=[
            Route("/health", health),
            Route("/info", info),
            Mount("/", app=sse_app),
        ]
    )
    
    logger.info(f"Starting KB MCP Server on http://{host}:{port}")
    logger.info(f"SSE endpoint: http://{host}:{port}/sse")
    uvicorn.run(app, host=host, port=port)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="KB MCP Server - Kungliga bibliotekets API:er")
    parser.add_argument("--http", action="store_true", help="Kör med HTTP-transport (för remote access)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)), help="HTTP port (default: 8000)")
    
    args = parser.parse_args()
    
    if args.http:
        run_http(args.host, args.port)
    else:
        run_stdio()
