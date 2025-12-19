"""
KB MCP Server - API Clients
Gemensamma HTTP-klienter och hjälpfunktioner för KB:s API:er.
"""

import json
import logging
import xml.etree.ElementTree as ET
from typing import Any, Optional, Dict, List
from urllib.parse import urlencode, quote_plus

import httpx

# Konfigurera logging till stderr (viktigt för stdio-transport)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("kb_mcp")

# ============================================================================
# KONSTANTER
# ============================================================================

# API Base URLs
URLS = {
    "libris_xsearch": "https://libris.kb.se/xsearch",
    "libris_xl": "https://libris.kb.se",
    "libris_oaipmh": "https://libris.kb.se/api/oaipmh/",
    "libris_sparql": "https://libris.kb.se/api/sparql/",
    "ksamsok": "https://kulturarvsdata.se/ksamsok/api",
    "kb_data": "https://data.kb.se",
    "swepub": "https://libris.kb.se/xsearch",  # Swepub via Libris
    "idkb": "https://id.kb.se",
}

HTTP_TIMEOUT = 30.0
USER_AGENT = "KB-MCP-Server/2.0 (Model Context Protocol; Swedish National Library APIs)"


# ============================================================================
# HTTP CLIENT
# ============================================================================

class KBApiClient:
    """Gemensam HTTP-klient för alla KB API:er."""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
    
    async def get_client(self) -> httpx.AsyncClient:
        """Returnerar eller skapar HTTP-klient."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=HTTP_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT}
            )
        return self._client
    
    async def close(self):
        """Stänger HTTP-klienten."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        accept: str = "application/json"
    ) -> httpx.Response:
        """Gör GET-anrop."""
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"Accept": accept}
        )
        response.raise_for_status()
        return response
    
    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        accept: str = "application/json",
        content_type: str = "application/x-www-form-urlencoded"
    ) -> httpx.Response:
        """Gör POST-anrop."""
        client = await self.get_client()
        response = await client.post(
            url,
            data=data,
            headers={"Accept": accept, "Content-Type": content_type}
        )
        response.raise_for_status()
        return response


# Global klientinstans
api_client = KBApiClient()


# ============================================================================
# FELHANTERING
# ============================================================================

def handle_api_error(e: Exception, context: str = "") -> str:
    """Enhetlig felhantering för alla API-anrop."""
    prefix = f"[{context}] " if context else ""
    
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        error_messages = {
            400: "Ogiltiga parametrar. Kontrollera sökfrågan.",
            401: "Autentisering krävs (oväntat fel).",
            403: "Åtkomst nekad.",
            404: "Resursen hittades inte. Kontrollera ID:t.",
            429: "För många anrop. Vänta en stund.",
            500: "Serverfel hos KB. Försök igen senare.",
            502: "Gateway-fel. KB:s server är tillfälligt otillgänglig.",
            503: "Tjänsten är tillfälligt otillgänglig."
        }
        msg = error_messages.get(status, f"HTTP-fel {status}")
        return f"{prefix}Fel: {msg}"
    
    elif isinstance(e, httpx.TimeoutException):
        return f"{prefix}Fel: Tidsgräns överskriden. Försök med enklare sökning."
    
    elif isinstance(e, httpx.ConnectError):
        return f"{prefix}Fel: Kunde inte ansluta till servern."
    
    elif isinstance(e, ET.ParseError):
        return f"{prefix}Fel: Kunde inte tolka XML-svaret."
    
    elif isinstance(e, json.JSONDecodeError):
        return f"{prefix}Fel: Kunde inte tolka JSON-svaret."
    
    logger.error(f"Oväntat fel: {type(e).__name__}: {e}")
    return f"{prefix}Fel: {type(e).__name__} - {str(e)}"


# ============================================================================
# XML-PARSNING
# ============================================================================

def parse_ksamsok_xml(xml_text: str) -> Dict[str, Any]:
    """Parsar K-samsök XML-svar till dict."""
    try:
        root = ET.fromstring(xml_text)
        
        # Hitta totalt antal träffar
        total_hits_elem = root.find(".//totalHits")
        total_hits = int(total_hits_elem.text) if total_hits_elem is not None else 0
        
        records = []
        for record in root.findall(".//record"):
            item = {}
            
            # Hitta RDF-data
            rdf = record.find(".//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF")
            if rdf is not None:
                ns = {"ksam": "http://kulturarvsdata.se/ksamsok#"}
                
                # Extrahera fält
                for field, xpath in [
                    ("label", ".//ksam:itemLabel"),
                    ("description", ".//ksam:itemDescription"),
                    ("type", ".//ksam:itemType"),
                    ("url", ".//ksam:url"),
                    ("thumbnail", ".//ksam:thumbnail"),
                    ("service", ".//ksam:serviceName"),
                ]:
                    elem = rdf.find(xpath, ns)
                    if elem is not None:
                        item[field] = elem.text
                
                # Extrahera URI från Entity
                entity = rdf.find(".//{http://kulturarvsdata.se/ksamsok#}Entity")
                if entity is not None:
                    item["uri"] = entity.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about", "")
            
            if item:
                records.append(item)
        
        return {
            "total_hits": total_hits,
            "records": records
        }
    
    except ET.ParseError as e:
        logger.error(f"XML parse error: {e}")
        return {"total_hits": 0, "records": [], "error": str(e)}


def parse_oaipmh_xml(xml_text: str) -> Dict[str, Any]:
    """Parsar OAI-PMH XML-svar."""
    try:
        root = ET.fromstring(xml_text)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}
        
        result = {"records": [], "resumption_token": None}
        
        # Hitta records
        for record in root.findall(".//oai:record", ns):
            item = {}
            
            header = record.find("oai:header", ns)
            if header is not None:
                identifier = header.find("oai:identifier", ns)
                datestamp = header.find("oai:datestamp", ns)
                if identifier is not None:
                    item["identifier"] = identifier.text
                if datestamp is not None:
                    item["datestamp"] = datestamp.text
            
            metadata = record.find("oai:metadata", ns)
            if metadata is not None:
                item["has_metadata"] = True
            
            if item:
                result["records"].append(item)
        
        # Hitta sets
        for set_elem in root.findall(".//oai:set", ns):
            spec = set_elem.find("oai:setSpec", ns)
            name = set_elem.find("oai:setName", ns)
            if "sets" not in result:
                result["sets"] = []
            result["sets"].append({
                "spec": spec.text if spec is not None else "",
                "name": name.text if name is not None else ""
            })
        
        # Hitta resumption token
        token = root.find(".//oai:resumptionToken", ns)
        if token is not None and token.text:
            result["resumption_token"] = token.text
        
        return result
    
    except ET.ParseError as e:
        return {"error": str(e)}


# ============================================================================
# FORMATERING
# ============================================================================

def format_libris_results(data: dict, format_type: str = "markdown") -> str:
    """Formaterar Libris-sökresultat."""
    xsearch = data.get("xsearch", {})
    records = xsearch.get("records", 0)
    items = xsearch.get("list", [])
    
    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    lines = [
        f"## Libris Sökresultat",
        f"**Totalt:** {records} träffar",
        f"**Visar:** {xsearch.get('from', 1)}-{xsearch.get('to', len(items))}",
        ""
    ]
    
    for i, item in enumerate(items, 1):
        title = item.get("title", "Utan titel")
        creator = item.get("creator", "Okänd")
        date = item.get("date", "u.å.")
        publisher = item.get("publisher", "")
        isbn = item.get("isbn", [])
        identifier = item.get("identifier", "")
        
        lines.append(f"### {i}. {title}")
        lines.append(f"- **Författare:** {creator}")
        lines.append(f"- **År:** {date}")
        if publisher:
            lines.append(f"- **Förlag:** {publisher}")
        if isbn:
            isbn_str = ", ".join(isbn) if isinstance(isbn, list) else isbn
            lines.append(f"- **ISBN:** {isbn_str}")
        if identifier:
            lines.append(f"- **Länk:** {identifier}")
        lines.append("")
    
    return "\n".join(lines)


def format_ksamsok_results(data: dict, format_type: str = "markdown") -> str:
    """Formaterar K-samsök-resultat."""
    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    lines = [
        f"## K-samsök Sökresultat",
        f"**Totalt:** {data.get('total_hits', 0)} objekt",
        ""
    ]
    
    for i, record in enumerate(data.get("records", [])[:20], 1):
        label = record.get("label", "Utan benämning")
        obj_type = record.get("type", "Okänd typ")
        description = record.get("description", "")
        url = record.get("url", "")
        uri = record.get("uri", "")
        
        lines.append(f"### {i}. {label}")
        lines.append(f"- **Typ:** {obj_type}")
        if description:
            desc_short = description[:200] + "..." if len(description) > 200 else description
            lines.append(f"- **Beskrivning:** {desc_short}")
        if url:
            lines.append(f"- **Webbsida:** {url}")
        if uri:
            lines.append(f"- **URI:** {uri}")
        lines.append("")
    
    return "\n".join(lines)


def format_sparql_results(data: dict, format_type: str = "markdown") -> str:
    """Formaterar SPARQL-resultat."""
    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    results = data.get("results", {}).get("bindings", [])
    variables = data.get("head", {}).get("vars", [])
    
    if not results:
        return "Inga resultat från SPARQL-frågan."
    
    lines = [
        f"## SPARQL Resultat",
        f"**Antal rader:** {len(results)}",
        ""
    ]
    
    # Skapa tabell-header
    if variables:
        lines.append("| " + " | ".join(variables) + " |")
        lines.append("| " + " | ".join(["---"] * len(variables)) + " |")
    
    # Lägg till rader
    for row in results[:50]:  # Max 50 rader
        cells = []
        for var in variables:
            value = row.get(var, {}).get("value", "")
            # Förkorta långa värden
            if len(value) > 50:
                value = value[:47] + "..."
            cells.append(value)
        lines.append("| " + " | ".join(cells) + " |")
    
    if len(results) > 50:
        lines.append(f"\n*... och {len(results) - 50} rader till*")
    
    return "\n".join(lines)
