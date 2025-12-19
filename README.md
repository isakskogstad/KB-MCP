# KB MCP Server

MCP-server för åtkomst till **Kungliga bibliotekets öppna API:er** - Sveriges nationella biblioteksdata, kulturarv, forskning och länkad data.

## 📊 Översikt

| Datakälla | Beskrivning | Antal poster |
|-----------|-------------|--------------|
| **Libris** | Bibliografiska poster | 20M+ |
| **K-samsök** | Kulturarvsobjekt | 10M+ |
| **Swepub** | Forskningspublikationer | 2M+ |
| **id.kb.se** | Auktoriteter & vokabulär | 500K+ |

**52 verktyg** fördelade på 10 API-endpoints.

## 🚀 Installation

### Lokal installation (Claude Desktop, Claude Code)

```bash
# Klona eller ladda ner
cd kb-mcp-server

# Skapa virtuell miljö (rekommenderat)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# eller: venv\Scripts\activate  # Windows

# Installera dependencies
pip install -r requirements.txt

# Testa
python test_kb_mcp.py
```

### Claude Desktop-konfiguration

Lägg till i `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) eller motsvarande:

```json
{
  "mcpServers": {
    "kb-api": {
      "command": "python",
      "args": ["kb_mcp_server.py"],
      "cwd": "/full/path/to/kb-mcp-server"
    }
  }
}
```

Starta om Claude Desktop.

### Remote deployment (Render)

1. **Push till GitHub**
2. **Skapa ny Web Service på Render:**
   - Välj repository
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python kb_mcp_server.py --http --port $PORT`
3. **Hämta URL:** `https://your-service.onrender.com`

Alternativt, använd Blueprint:
```bash
render blueprint sync
```

### Docker

```bash
docker build -t kb-mcp-server .
docker run -p 8000:8000 kb-mcp-server
```

## 🔧 Verktyg per Endpoint

### 1. Libris Xsearch (5 verktyg)
Enkel bibliotekssökning med 20M+ poster.

| Verktyg | Beskrivning |
|---------|-------------|
| `libris_search` | Fritextsökning |
| `libris_search_author` | Sök efter författare |
| `libris_search_title` | Sök efter titel |
| `libris_search_subject` | Sök efter ämne |
| `libris_search_isbn` | Sök efter ISBN |

### 2. Libris XL REST (6 verktyg)
Avancerad åtkomst till bibliografisk data.

| Verktyg | Beskrivning |
|---------|-------------|
| `libris_get_record` | Hämta specifik post |
| `libris_find` | Avancerad sökning med operatorer |
| `libris_get_holdings` | Biblioteksbestånd |
| `libris_get_work` | Alla utgåvor av ett verk |
| `libris_autocomplete` | Sökförslag |
| `libris_related` | Relaterade verk |

### 3. K-samsök (7 verktyg)
Kulturarv från 83 institutioner.

| Verktyg | Beskrivning |
|---------|-------------|
| `ksamsok_search` | CQL-sökning |
| `ksamsok_search_location` | Geografisk sökning |
| `ksamsok_search_type` | Sök efter objekttyp |
| `ksamsok_search_time` | Sök efter tidsperiod |
| `ksamsok_get_object` | Hämta specifikt objekt |
| `ksamsok_get_relations` | Objektrelationer |
| `ksamsok_statistics` | Statistik och facetter |

### 4. OAI-PMH (5 verktyg)
Bulkexport av metadata.

| Verktyg | Beskrivning |
|---------|-------------|
| `oaipmh_list_records` | Lista poster |
| `oaipmh_get_record` | Hämta enskild post |
| `oaipmh_list_sets` | Tillgängliga sets |
| `oaipmh_list_formats` | Metadataformat |
| `oaipmh_resume` | Paginering |

### 5. data.kb.se (5 verktyg)
Digitaliserat material.

| Verktyg | Beskrivning |
|---------|-------------|
| `kb_data_list_collections` | Lista samlingar |
| `kb_data_get_item` | Hämta objekt |
| `kb_data_search` | Sök digitaliserat |
| `kb_data_get_manifest` | IIIF-manifest |
| `kb_data_get_metadata` | Metadata i olika format |

### 6. Swepub (6 verktyg)
Svensk forskningspublicering.

| Verktyg | Beskrivning |
|---------|-------------|
| `swepub_search` | Sök publikationer |
| `swepub_search_author` | Sök efter forskare |
| `swepub_search_affiliation` | Sök efter lärosäte |
| `swepub_search_subject` | Sök efter ämne |
| `swepub_get_publication` | Hämta publikation |
| `swepub_export` | Exportera till RIS/BibTeX |

### 7. id.kb.se (4 verktyg)
Auktoriteter och vokabulär.

| Verktyg | Beskrivning |
|---------|-------------|
| `idkb_get_entity` | Hämta entitet |
| `idkb_search` | Sök auktoriteter |
| `idkb_get_vocab_term` | Hämta vokabulärterm |
| `idkb_list_vocab` | Lista vokabulär |

### 8. SPARQL (4 verktyg)
Länkad data-frågor.

| Verktyg | Beskrivning |
|---------|-------------|
| `sparql_query` | Kör SPARQL SELECT |
| `sparql_describe` | Beskriv resurs |
| `sparql_count` | Räkna resultat |
| `sparql_templates` | Frågemallar |

### 9. Export (5 verktyg)
Bibliografi och referenshantering.

| Verktyg | Beskrivning |
|---------|-------------|
| `export_author_bibliography` | Författarbibliografi |
| `export_subject_bibliography` | Ämnesbibliografi |
| `export_search_results` | Exportera sökresultat |
| `export_publication_list` | Skapa publikationslista |
| `export_formats_info` | Information om format |

### 10. Hjälp (5 verktyg)
Dokumentation och metadata.

| Verktyg | Beskrivning |
|---------|-------------|
| `kb_api_info` | Översikt alla API:er |
| `kb_api_status` | Kontrollera status |
| `kb_search_tips` | Söktips och syntax |
| `kb_data_dictionary` | Datadefinitioner |
| `kb_example_queries` | Exempelfrågor |

## 📖 Användningsexempel

### Hitta böcker av en författare
```
libris_search_author(author_name="Lagerlöf, Selma")
```

### Sök kulturarvsobjekt
```
ksamsok_search(query='itemType=Photograph AND countyName="Uppsala län"')
```

### Exportera bibliografi till Zotero
```
export_author_bibliography(author_name="Strindberg, August", format="ris")
```

### SPARQL-analys
```
sparql_query(query="SELECT ?author (COUNT(?work) AS ?count) WHERE { ?work dc:creator ?author } GROUP BY ?author ORDER BY DESC(?count) LIMIT 10")
```

## 🌐 Remote URL (efter Render-deployment)

Använd i ChatGPT eller andra MCP-klienter:

```
https://your-service.onrender.com/sse
```

### Endpoints

| Endpoint | Beskrivning |
|----------|-------------|
| `/health` | Health check |
| `/info` | Server-information |
| `/sse` | SSE-transport (MCP) |
| `/messages/` | Meddelanden (POST) |

## 🔒 Säkerhet

- **Ingen autentisering krävs** - KB:s API:er är öppna
- **Ingen API-nyckel** - Inga hemligheter att hantera
- **Rate limiting** - Respektera KB:s servrar

## 📁 Projektstruktur

```
kb-mcp-server/
├── kb_mcp_server.py      # Huvudserver med alla 52 verktyg
├── src/
│   ├── __init__.py
│   └── api_client.py     # HTTP-klient och hjälpfunktioner
├── requirements.txt      # Python-dependencies
├── Procfile             # Render startkommando
├── render.yaml          # Render Blueprint
├── Dockerfile           # Docker-image
├── test_kb_mcp.py       # Testsvit
├── claude_desktop_config.example.json
├── TOOL_DESIGN.md       # Verktygsdesign
└── README.md            # Denna fil
```

## 🧪 Testa

```bash
python test_kb_mcp.py
```

Förväntat resultat:
```
KB MCP Server - Testsvit
============================================================
🔍 Test: Libris Xsearch...
   ✅ OK - 7432 träffar för 'Astrid Lindgren'
🔍 Test: Libris XL...
   ✅ OK - 3 poster för 'Strindberg'
🔍 Test: K-samsök...
   ✅ OK - 12023 runstenar hittade
🔍 Test: OAI-PMH...
   ✅ OK - 5 sets tillgängliga
🔍 Test: id.kb.se...
   ✅ OK - 5 auktoriteter för 'Strindberg'
🔍 Test: Swepub...
   ✅ OK - 15234 forskningspublikationer
============================================================
Resultat: 6/6 tester godkända
```

## 📚 Dokumentation

- [KB:s API-dokumentation](https://kb.se/samverkan-och-utveckling/libris/teknisk-information.html)
- [Libris](https://libris.kb.se/)
- [K-samsök](https://kulturarvsdata.se/)
- [MCP Specification](https://modelcontextprotocol.io/)

## 📄 Licens

MIT License - Använd fritt för alla ändamål.

## 👤 Författare

Utvecklad för åtkomst till Sveriges nationella biblioteksdata via Model Context Protocol.
