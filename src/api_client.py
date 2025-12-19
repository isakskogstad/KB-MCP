"""
KB MCP Server - API Clients
Gemensamma HTTP-klienter och hjälpfunktioner för KB:s API:er.

Version: 2.2.0
- Retry-logik med exponentiell backoff
- Enkel in-memory cache
- Förbättrad felhantering
- Miljövariabel-konfiguration
"""

import asyncio
import json
import logging
import os
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Tuple
from urllib.parse import urlencode, quote_plus
from functools import wraps

import httpx

# Konfigurera logging till stderr (viktigt för stdio-transport)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("kb_mcp")

# ============================================================================
# KONFIGURATION VIA MILJÖVARIABLER
# ============================================================================

class Config:
    """Konfiguration som kan överskridas via miljövariabler."""

    # Timeouts
    HTTP_TIMEOUT: float = float(os.environ.get("KB_HTTP_TIMEOUT", "30.0"))
    CONNECT_TIMEOUT: float = float(os.environ.get("KB_CONNECT_TIMEOUT", "10.0"))

    # Retry
    MAX_RETRIES: int = int(os.environ.get("KB_MAX_RETRIES", "3"))
    RETRY_BASE_DELAY: float = float(os.environ.get("KB_RETRY_BASE_DELAY", "1.0"))
    RETRY_MAX_DELAY: float = float(os.environ.get("KB_RETRY_MAX_DELAY", "30.0"))

    # Cache
    CACHE_ENABLED: bool = os.environ.get("KB_CACHE_ENABLED", "true").lower() == "true"
    CACHE_TTL: int = int(os.environ.get("KB_CACHE_TTL", "300"))  # 5 minuter
    CACHE_MAX_SIZE: int = int(os.environ.get("KB_CACHE_MAX_SIZE", "1000"))

    # Identifikation
    USER_AGENT: str = os.environ.get(
        "KB_USER_AGENT",
        "KB-MCP-Server/2.2.0 (Model Context Protocol; Swedish National Library APIs)"
    )


# ============================================================================
# KONSTANTER - API URLs
# ============================================================================

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

# För bakåtkompatibilitet
HTTP_TIMEOUT = Config.HTTP_TIMEOUT
USER_AGENT = Config.USER_AGENT


# ============================================================================
# CACHE IMPLEMENTATION
# ============================================================================

@dataclass
class CacheEntry:
    """En cache-post med data och tidsstämpel."""
    data: Any
    timestamp: float
    hits: int = 0


class SimpleCache:
    """Enkel in-memory cache med TTL och LRU-liknande eviction."""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._hits = 0
        self._misses = 0

    def _make_key(self, url: str, params: Optional[Dict] = None, accept: str = "") -> str:
        """Skapa en unik nyckel för cache."""
        parts = [url]
        if params:
            parts.append(json.dumps(params, sort_keys=True))
        parts.append(accept)
        return "|".join(parts)

    def get(self, url: str, params: Optional[Dict] = None, accept: str = "") -> Optional[Any]:
        """Hämta från cache om det finns och inte har gått ut."""
        if not Config.CACHE_ENABLED:
            return None

        key = self._make_key(url, params, accept)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        # Kontrollera TTL
        if time.time() - entry.timestamp > self._ttl:
            del self._cache[key]
            self._misses += 1
            return None

        entry.hits += 1
        self._hits += 1
        return entry.data

    def set(self, url: str, data: Any, params: Optional[Dict] = None, accept: str = "") -> None:
        """Spara i cache."""
        if not Config.CACHE_ENABLED:
            return

        key = self._make_key(url, params, accept)

        # Rensa gamla poster om cachen är full
        if len(self._cache) >= self._max_size:
            self._evict()

        self._cache[key] = CacheEntry(
            data=data,
            timestamp=time.time()
        )

    def _evict(self) -> None:
        """Ta bort gamla och sällan använda poster."""
        now = time.time()

        # Ta först bort utgångna
        expired = [k for k, v in self._cache.items() if now - v.timestamp > self._ttl]
        for key in expired:
            del self._cache[key]

        # Om fortfarande full, ta bort de minst använda
        if len(self._cache) >= self._max_size:
            # Sortera efter hits (lägst först)
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: (self._cache[k].hits, self._cache[k].timestamp)
            )
            # Ta bort 20% av de minst använda
            to_remove = len(sorted_keys) // 5 or 1
            for key in sorted_keys[:to_remove]:
                del self._cache[key]

    def clear(self) -> None:
        """Rensa hela cachen."""
        self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        """Returnera cache-statistik."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "N/A"
        }


# Global cache-instans
cache = SimpleCache(ttl=Config.CACHE_TTL, max_size=Config.CACHE_MAX_SIZE)


# ============================================================================
# RETRY LOGIC
# ============================================================================

# HTTP-statuskoder som ska triggera retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# Exceptions som ska triggera retry
RETRYABLE_EXCEPTIONS = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.ConnectTimeout,
)


async def retry_with_backoff(
    func,
    *args,
    max_retries: int = None,
    base_delay: float = None,
    max_delay: float = None,
    **kwargs
) -> Any:
    """
    Kör en async funktion med exponentiell backoff vid fel.

    Args:
        func: Async funktion att köra
        max_retries: Max antal försök
        base_delay: Basfördröjning i sekunder
        max_delay: Maximal fördröjning i sekunder

    Returns:
        Resultatet från func om lyckat

    Raises:
        Senaste exception om alla försök misslyckas
    """
    max_retries = max_retries or Config.MAX_RETRIES
    base_delay = base_delay or Config.RETRY_BASE_DELAY
    max_delay = max_delay or Config.RETRY_MAX_DELAY

    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)

        except httpx.HTTPStatusError as e:
            last_exception = e
            status = e.response.status_code

            if status not in RETRYABLE_STATUS_CODES:
                raise

            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"HTTP {status}, försök {attempt + 1}/{max_retries + 1}, "
                    f"väntar {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        except RETRYABLE_EXCEPTIONS as e:
            last_exception = e

            if attempt < max_retries:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning(
                    f"{type(e).__name__}, försök {attempt + 1}/{max_retries + 1}, "
                    f"väntar {delay:.1f}s"
                )
                await asyncio.sleep(delay)

    raise last_exception


# ============================================================================
# HTTP CLIENT
# ============================================================================

class KBApiClient:
    """
    Gemensam HTTP-klient för alla KB API:er.

    Features:
    - Automatisk retry med exponentiell backoff
    - In-memory caching
    - Connection pooling
    - Konfigurerbar via miljövariabler
    """

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Returnerar eller skapar HTTP-klient med connection pooling."""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                Config.HTTP_TIMEOUT,
                connect=Config.CONNECT_TIMEOUT
            )
            limits = httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                follow_redirects=True,
                headers={"User-Agent": Config.USER_AGENT}
            )
        return self._client

    async def close(self):
        """Stänger HTTP-klienten."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _do_get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        accept: str = "application/json"
    ) -> httpx.Response:
        """Intern GET utan retry/cache."""
        client = await self.get_client()
        response = await client.get(
            url,
            params=params,
            headers={"Accept": accept}
        )
        response.raise_for_status()
        return response

    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        accept: str = "application/json",
        use_cache: bool = True,
        retry: bool = True
    ) -> httpx.Response:
        """
        Gör GET-anrop med automatisk retry och caching.

        Args:
            url: URL att hämta
            params: Query-parametrar
            accept: Accept-header
            use_cache: Använd cache (default True)
            retry: Använd retry vid fel (default True)

        Returns:
            httpx.Response
        """
        # Kolla cache först
        if use_cache:
            cached = cache.get(url, params, accept)
            if cached is not None:
                logger.debug(f"Cache hit: {url}")
                return cached

        # Gör anropet med eller utan retry
        if retry:
            response = await retry_with_backoff(
                self._do_get, url, params=params, accept=accept
            )
        else:
            response = await self._do_get(url, params=params, accept=accept)

        # Spara i cache
        if use_cache:
            cache.set(url, response, params, accept)

        return response

    async def _do_post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        accept: str = "application/json",
        content_type: str = "application/x-www-form-urlencoded"
    ) -> httpx.Response:
        """Intern POST utan retry."""
        client = await self.get_client()
        response = await client.post(
            url,
            data=data,
            headers={"Accept": accept, "Content-Type": content_type}
        )
        response.raise_for_status()
        return response

    async def post(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        accept: str = "application/json",
        content_type: str = "application/x-www-form-urlencoded",
        retry: bool = True
    ) -> httpx.Response:
        """
        Gör POST-anrop med automatisk retry.

        Args:
            url: URL att posta till
            data: POST-data
            accept: Accept-header
            content_type: Content-Type header
            retry: Använd retry vid fel (default True)

        Returns:
            httpx.Response
        """
        if retry:
            return await retry_with_backoff(
                self._do_post, url, data=data, accept=accept, content_type=content_type
            )
        return await self._do_post(url, data=data, accept=accept, content_type=content_type)


# Global klientinstans
api_client = KBApiClient()


# ============================================================================
# FELHANTERING
# ============================================================================

def handle_api_error(e: Exception, context: str = "") -> str:
    """
    Enhetlig felhantering för alla API-anrop.

    Args:
        e: Exception som uppstod
        context: Kontext för felet (t.ex. verktygsnamn)

    Returns:
        Användarvänligt felmeddelande på svenska
    """
    prefix = f"[{context}] " if context else ""

    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        error_messages = {
            400: "Ogiltiga parametrar. Kontrollera sökfrågan.",
            401: "Autentisering krävs (oväntat fel).",
            403: "Åtkomst nekad.",
            404: "Resursen hittades inte. Kontrollera ID:t.",
            429: "För många anrop. Försök igen om en stund.",
            500: "Serverfel hos KB. Försök igen senare.",
            502: "Gateway-fel. KB:s server är tillfälligt otillgänglig.",
            503: "Tjänsten är tillfälligt otillgänglig.",
            504: "Timeout från servern. Försök med enklare sökning."
        }
        msg = error_messages.get(status, f"HTTP-fel {status}")
        return f"{prefix}Fel: {msg}"

    elif isinstance(e, httpx.TimeoutException):
        return f"{prefix}Fel: Tidsgräns överskriden. Försök med enklare sökning."

    elif isinstance(e, httpx.ConnectError):
        return f"{prefix}Fel: Kunde inte ansluta till servern. Kontrollera nätverket."

    elif isinstance(e, ET.ParseError):
        return f"{prefix}Fel: Kunde inte tolka XML-svaret från servern."

    elif isinstance(e, json.JSONDecodeError):
        return f"{prefix}Fel: Kunde inte tolka JSON-svaret från servern."

    logger.error(f"Oväntat fel: {type(e).__name__}: {e}")
    return f"{prefix}Fel: {type(e).__name__} - {str(e)}"


# ============================================================================
# XML-PARSNING
# ============================================================================

def parse_ksamsok_xml(xml_text: str) -> Dict[str, Any]:
    """
    Parsar K-samsök XML-svar till dict.

    Args:
        xml_text: XML-svar från K-samsök API

    Returns:
        Dict med total_hits och records-lista
    """
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
                for field_name, xpath in [
                    ("label", ".//ksam:itemLabel"),
                    ("description", ".//ksam:itemDescription"),
                    ("type", ".//ksam:itemType"),
                    ("url", ".//ksam:url"),
                    ("thumbnail", ".//ksam:thumbnail"),
                    ("service", ".//ksam:serviceName"),
                    ("time_label", ".//ksam:timeLabel"),
                    ("place_label", ".//ksam:placeLabel"),
                ]:
                    elem = rdf.find(xpath, ns)
                    if elem is not None:
                        item[field_name] = elem.text

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
    """
    Parsar OAI-PMH XML-svar.

    Args:
        xml_text: XML-svar från OAI-PMH endpoint

    Returns:
        Dict med records, sets och resumption_token
    """
    try:
        root = ET.fromstring(xml_text)
        ns = {"oai": "http://www.openarchives.org/OAI/2.0/"}

        result: Dict[str, Any] = {"records": [], "resumption_token": None}

        # Hitta records
        for record in root.findall(".//oai:record", ns):
            item: Dict[str, Any] = {}

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

        # Hitta metadata formats
        for format_elem in root.findall(".//oai:metadataFormat", ns):
            prefix = format_elem.find("oai:metadataPrefix", ns)
            schema = format_elem.find("oai:schema", ns)
            if "formats" not in result:
                result["formats"] = []
            result["formats"].append({
                "prefix": prefix.text if prefix is not None else "",
                "schema": schema.text if schema is not None else ""
            })

        # Hitta resumption token
        token = root.find(".//oai:resumptionToken", ns)
        if token is not None and token.text:
            result["resumption_token"] = token.text
            # Extrahera attribut om de finns
            if token.get("completeListSize"):
                result["total_size"] = int(token.get("completeListSize"))
            if token.get("cursor"):
                result["cursor"] = int(token.get("cursor"))

        return result

    except ET.ParseError as e:
        return {"error": str(e)}


# ============================================================================
# FORMATERING
# ============================================================================

def format_libris_results(data: dict, format_type: str = "markdown") -> str:
    """
    Formaterar Libris-sökresultat.

    Args:
        data: JSON-data från Libris xsearch
        format_type: 'markdown' eller 'json'

    Returns:
        Formaterad sträng
    """
    xsearch = data.get("xsearch", {})
    records = xsearch.get("records", 0)
    items = xsearch.get("list", [])

    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)

    lines = [
        f"## Libris Sökresultat",
        f"**Totalt:** {records:,} träffar",
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
        item_type = item.get("type", "")

        lines.append(f"### {i}. {title}")
        lines.append(f"- **Författare:** {creator}")
        lines.append(f"- **År:** {date}")
        if item_type:
            lines.append(f"- **Typ:** {item_type}")
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
    """
    Formaterar K-samsök-resultat.

    Args:
        data: Parsad K-samsök data
        format_type: 'markdown' eller 'json'

    Returns:
        Formaterad sträng
    """
    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)

    total = data.get('total_hits', 0)
    records = data.get("records", [])

    lines = [
        f"## K-samsök Sökresultat",
        f"**Totalt:** {total:,} objekt",
        f"**Visar:** {len(records)} objekt",
        ""
    ]

    for i, record in enumerate(records[:50], 1):
        label = record.get("label", "Utan benämning")
        obj_type = record.get("type", "Okänd typ")
        description = record.get("description", "")
        url = record.get("url", "")
        uri = record.get("uri", "")
        time_label = record.get("time_label", "")
        place_label = record.get("place_label", "")
        thumbnail = record.get("thumbnail", "")

        lines.append(f"### {i}. {label}")
        lines.append(f"- **Typ:** {obj_type}")
        if time_label:
            lines.append(f"- **Tid:** {time_label}")
        if place_label:
            lines.append(f"- **Plats:** {place_label}")
        if description:
            desc_short = description[:300] + "..." if len(description) > 300 else description
            lines.append(f"- **Beskrivning:** {desc_short}")
        if thumbnail:
            lines.append(f"- **Bild:** {thumbnail}")
        if url:
            lines.append(f"- **Webbsida:** {url}")
        if uri:
            lines.append(f"- **URI:** {uri}")
        lines.append("")

    if len(records) > 50:
        lines.append(f"*... och {len(records) - 50} objekt till*")

    return "\n".join(lines)


def format_sparql_results(data: dict, format_type: str = "markdown") -> str:
    """
    Formaterar SPARQL-resultat.

    Args:
        data: JSON-resultat från SPARQL endpoint
        format_type: 'markdown' eller 'json'

    Returns:
        Formaterad sträng
    """
    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)

    results = data.get("results", {}).get("bindings", [])
    variables = data.get("head", {}).get("vars", [])

    if not results:
        return "Inga resultat från SPARQL-frågan."

    lines = [
        f"## SPARQL Resultat",
        f"**Antal rader:** {len(results):,}",
        ""
    ]

    # Skapa tabell-header
    if variables:
        lines.append("| " + " | ".join(variables) + " |")
        lines.append("| " + " | ".join(["---"] * len(variables)) + " |")

    # Lägg till rader
    for row in results[:100]:  # Max 100 rader
        cells = []
        for var in variables:
            value = row.get(var, {}).get("value", "")
            # Förkorta långa värden
            if len(value) > 60:
                value = value[:57] + "..."
            # Escape pipe-tecken
            value = value.replace("|", "\\|")
            cells.append(value)
        lines.append("| " + " | ".join(cells) + " |")

    if len(results) > 100:
        lines.append(f"\n*... och {len(results) - 100:,} rader till*")

    return "\n".join(lines)


def format_swepub_results(data: dict, format_type: str = "markdown") -> str:
    """
    Formaterar Swepub-sökresultat.

    Args:
        data: JSON-data från Swepub/Libris xsearch
        format_type: 'markdown' eller 'json'

    Returns:
        Formaterad sträng
    """
    xsearch = data.get("xsearch", {})
    records = xsearch.get("records", 0)
    items = xsearch.get("list", [])

    if format_type == "json":
        return json.dumps(data, indent=2, ensure_ascii=False)

    lines = [
        f"## Swepub Sökresultat",
        f"**Totalt:** {records:,} publikationer",
        f"**Visar:** {xsearch.get('from', 1)}-{xsearch.get('to', len(items))}",
        ""
    ]

    for i, item in enumerate(items, 1):
        title = item.get("title", "Utan titel")
        creator = item.get("creator", "Okänd")
        date = item.get("date", "u.å.")
        publisher = item.get("publisher", "")
        pub_type = item.get("type", "")
        identifier = item.get("identifier", "")

        lines.append(f"### {i}. {title}")
        lines.append(f"- **Författare:** {creator}")
        lines.append(f"- **År:** {date}")
        if pub_type:
            lines.append(f"- **Typ:** {pub_type}")
        if publisher:
            lines.append(f"- **Utgivare:** {publisher}")
        if identifier:
            lines.append(f"- **Länk:** {identifier}")
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# EXPORTFORMAT
# ============================================================================

def format_ris(records: List[Dict[str, Any]]) -> str:
    """
    Formaterar poster till RIS-format (för Zotero, EndNote).

    Args:
        records: Lista med bibliografiska poster

    Returns:
        RIS-formaterad sträng
    """
    lines = []

    for record in records:
        lines.append("TY  - BOOK")  # Default till bok

        if record.get("title"):
            lines.append(f"TI  - {record['title']}")

        if record.get("creator"):
            # Hantera flera författare
            creators = record["creator"]
            if isinstance(creators, list):
                for creator in creators:
                    lines.append(f"AU  - {creator}")
            else:
                lines.append(f"AU  - {creators}")

        if record.get("date"):
            lines.append(f"PY  - {record['date']}")

        if record.get("publisher"):
            lines.append(f"PB  - {record['publisher']}")

        if record.get("isbn"):
            isbn = record["isbn"]
            if isinstance(isbn, list):
                isbn = isbn[0] if isbn else ""
            lines.append(f"SN  - {isbn}")

        if record.get("identifier"):
            lines.append(f"UR  - {record['identifier']}")

        lines.append("ER  - ")
        lines.append("")

    return "\n".join(lines)


def format_bibtex(records: List[Dict[str, Any]]) -> str:
    """
    Formaterar poster till BibTeX-format (för LaTeX).

    Args:
        records: Lista med bibliografiska poster

    Returns:
        BibTeX-formaterad sträng
    """
    lines = []

    for i, record in enumerate(records, 1):
        # Skapa cite-key
        author_key = ""
        if record.get("creator"):
            creator = record["creator"]
            if isinstance(creator, list):
                creator = creator[0]
            # Ta efternamn
            parts = creator.split(",")
            if parts:
                author_key = parts[0].strip().lower().replace(" ", "_")

        year = record.get("date", "nodate")[:4]
        cite_key = f"{author_key}{year}_{i}" if author_key else f"ref{i}"

        lines.append(f"@book{{{cite_key},")

        if record.get("title"):
            lines.append(f"  title = {{{record['title']}}},")

        if record.get("creator"):
            creators = record["creator"]
            if isinstance(creators, list):
                author_str = " and ".join(creators)
            else:
                author_str = creators
            lines.append(f"  author = {{{author_str}}},")

        if record.get("date"):
            lines.append(f"  year = {{{record['date'][:4]}}},")

        if record.get("publisher"):
            lines.append(f"  publisher = {{{record['publisher']}}},")

        if record.get("isbn"):
            isbn = record["isbn"]
            if isinstance(isbn, list):
                isbn = isbn[0] if isbn else ""
            lines.append(f"  isbn = {{{isbn}}},")

        if record.get("identifier"):
            lines.append(f"  url = {{{record['identifier']}}},")

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_cache_stats() -> Dict[str, Any]:
    """Returnerar cache-statistik."""
    return cache.stats()


def clear_cache() -> None:
    """Rensar cachen."""
    cache.clear()


def get_config() -> Dict[str, Any]:
    """Returnerar aktuell konfiguration."""
    return {
        "http_timeout": Config.HTTP_TIMEOUT,
        "connect_timeout": Config.CONNECT_TIMEOUT,
        "max_retries": Config.MAX_RETRIES,
        "retry_base_delay": Config.RETRY_BASE_DELAY,
        "retry_max_delay": Config.RETRY_MAX_DELAY,
        "cache_enabled": Config.CACHE_ENABLED,
        "cache_ttl": Config.CACHE_TTL,
        "cache_max_size": Config.CACHE_MAX_SIZE,
        "user_agent": Config.USER_AGENT
    }
