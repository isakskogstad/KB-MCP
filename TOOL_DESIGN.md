# KB MCP Server - Verktygsdesign

## Översikt

10 API-endpoints × 3-8 verktyg = **52 verktyg totalt**

---

## 1. LIBRIS XSEARCH (5 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `libris_search` | Enkel fritextsökning i bibliotekskatalogen | query, limit, offset, format |
| `libris_search_author` | Sök verk av specifik författare | author_name, limit, sort_order |
| `libris_search_title` | Sök efter titel | title, exact_match, limit |
| `libris_search_subject` | Sök efter ämnesord/kategori | subject, limit |
| `libris_search_isbn` | Sök efter ISBN-nummer | isbn |

---

## 2. LIBRIS XL REST (6 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `libris_get_record` | Hämta en specifik post via ID | record_id, format |
| `libris_find` | Avancerad sökning med operatorer | query, limit, offset |
| `libris_get_holdings` | Hämta biblioteksbestånd för en post | record_id |
| `libris_get_work` | Hämta verkinformation (alla utgåvor) | work_id |
| `libris_autocomplete` | Föreslå söktermer | prefix, type |
| `libris_related` | Hitta relaterade verk | record_id, relation_type |

---

## 3. K-SAMSÖK (7 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `ksamsok_search` | Sök kulturarvsobjekt med CQL | query, limit, start_record |
| `ksamsok_search_location` | Sök objekt i geografiskt område | county, municipality, parish |
| `ksamsok_search_type` | Sök efter objekttyp | item_type, has_image, has_coordinates |
| `ksamsok_search_time` | Sök efter tidsperiod | from_year, to_year, item_type |
| `ksamsok_get_object` | Hämta enskilt objekt | uri, format |
| `ksamsok_get_relations` | Hämta relationer för objekt | uri, relation_type |
| `ksamsok_statistics` | Hämta statistik för index | index_name, query |

---

## 4. OAI-PMH (5 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `oaipmh_list_records` | Lista poster från en delmängd | set_spec, metadata_prefix, from_date, until_date |
| `oaipmh_get_record` | Hämta enskild post | identifier, metadata_prefix |
| `oaipmh_list_sets` | Lista tillgängliga delmängder | - |
| `oaipmh_list_formats` | Lista metadataformat | - |
| `oaipmh_resume` | Fortsätt paginering | resumption_token |

---

## 5. DATA.KB.SE (5 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `kb_data_list_collections` | Lista digitala samlingar | path |
| `kb_data_get_item` | Hämta enskilt digitalt objekt | item_id |
| `kb_data_search` | Sök i digitaliserat material | query, collection |
| `kb_data_get_manifest` | Hämta IIIF-manifest | item_id |
| `kb_data_get_metadata` | Hämta objektmetadata | item_id, format |

---

## 6. SWEPUB (6 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `swepub_search` | Sök forskningspublikationer | query, limit, offset |
| `swepub_search_author` | Sök efter forskare/författare | author_name, orcid |
| `swepub_search_affiliation` | Sök efter lärosäte | organization, limit |
| `swepub_search_subject` | Sök efter forskningsämne | subject_code, limit |
| `swepub_get_publication` | Hämta enskild publikation | publication_id |
| `swepub_export` | Exportera sökresultat | query, format |

---

## 7. ID.KB.SE - Vokabulär (4 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `idkb_get_entity` | Hämta entitet/begrepp | entity_path, format |
| `idkb_search` | Sök auktoriteter och begrepp | query, entity_type, limit |
| `idkb_get_vocab_term` | Hämta vokabulärterm | vocab, term |
| `idkb_list_vocab` | Lista termer i vokabulär | vocab, limit |

---

## 8. SPARQL (4 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `sparql_query` | Kör SPARQL SELECT-fråga | query, format |
| `sparql_describe` | Beskriv en resurs | resource_uri |
| `sparql_count` | Räkna resultat | query |
| `sparql_templates` | Visa fördefinierade frågemallar | category |

---

## 9. BIBLIOGRAFI-EXPORT (5 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `export_author_bibliography` | Exportera författarbibliografi | author_name, format, max_results |
| `export_subject_bibliography` | Exportera ämnesbibliografi | subject, format, max_results |
| `export_search_results` | Exportera sökresultat | query, format |
| `export_publication_list` | Skapa publikationslista | record_ids, format |
| `export_formats_info` | Visa tillgängliga exportformat | - |

---

## 10. HJÄLP & METADATA (5 verktyg)

| Verktyg | Beskrivning | Parametrar |
|---------|-------------|------------|
| `kb_api_info` | Översikt över alla API:er | - |
| `kb_api_status` | Kontrollera API-status | api_name |
| `kb_search_tips` | Söktips och syntax | api_name |
| `kb_data_dictionary` | Datadefinitioner och fält | entity_type |
| `kb_example_queries` | Exempel på sökfrågor | api_name, use_case |

---

## TOTALT: 52 verktyg

### Fördelning per endpoint:
1. Libris Xsearch: 5 verktyg
2. Libris XL REST: 6 verktyg  
3. K-samsök: 7 verktyg
4. OAI-PMH: 5 verktyg
5. data.kb.se: 5 verktyg
6. Swepub: 6 verktyg
7. id.kb.se: 4 verktyg
8. SPARQL: 4 verktyg
9. Export: 5 verktyg
10. Hjälp: 5 verktyg

---

## Transport-stöd

- **Lokal (stdio)**: För Claude Desktop, Claude Code, etc.
- **HTTP (Streamable HTTP)**: För remote access via Render deployment
- **Ingen autentisering krävs** (KB:s API:er är öppna)
