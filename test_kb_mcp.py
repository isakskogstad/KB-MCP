#!/usr/bin/env python3
"""
KB MCP Server - Testsvit
Verifierar att alla verktygsgrupper fungerar korrekt.
"""

import asyncio
import sys
import json

# Lägg till src till path
sys.path.insert(0, '.')

from src.api_client import api_client, URLS, parse_ksamsok_xml, parse_oaipmh_xml


async def test_libris_xsearch():
    """Testar Libris Xsearch."""
    print("\n🔍 Test: Libris Xsearch...")
    try:
        params = {"query": "Astrid Lindgren", "n": 5, "format": "json"}
        response = await api_client.get(URLS["libris_xsearch"], params=params)
        data = response.json()
        records = data.get("xsearch", {}).get("records", 0)
        print(f"   ✅ OK - {records} träffar för 'Astrid Lindgren'")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def test_libris_xl():
    """Testar Libris XL REST API."""
    print("\n🔍 Test: Libris XL...")
    try:
        url = f"{URLS['libris_xl']}/find"
        params = {"q": "Strindberg", "_limit": 3}
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        items = data.get("items", [])
        print(f"   ✅ OK - {len(items)} poster för 'Strindberg'")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def test_ksamsok():
    """Testar K-samsök."""
    print("\n🔍 Test: K-samsök...")
    try:
        params = {"method": "search", "query": "text=runsten", "hitsPerPage": 5}
        response = await api_client.get(URLS["ksamsok"], params=params, accept="application/xml")
        data = parse_ksamsok_xml(response.text)
        total = data.get("total_hits", 0)
        print(f"   ✅ OK - {total} runstenar hittade")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def test_oaipmh():
    """Testar OAI-PMH."""
    print("\n🔍 Test: OAI-PMH...")
    try:
        params = {"verb": "ListSets"}
        response = await api_client.get(URLS["libris_oaipmh"], params=params, accept="application/xml")
        data = parse_oaipmh_xml(response.text)
        sets = data.get("sets", [])
        print(f"   ✅ OK - {len(sets)} sets tillgängliga")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def test_idkb():
    """Testar id.kb.se."""
    print("\n🔍 Test: id.kb.se...")
    try:
        url = f"{URLS['idkb']}/find"
        params = {"q": "Strindberg", "_limit": 5}
        response = await api_client.get(url, params=params, accept="application/ld+json")
        data = response.json()
        items = data.get("items", [])
        print(f"   ✅ OK - {len(items)} auktoriteter för 'Strindberg'")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def test_swepub():
    """Testar Swepub."""
    print("\n🔍 Test: Swepub...")
    try:
        params = {"query": "climate", "database": "swepub", "n": 5, "format": "json"}
        response = await api_client.get(URLS["swepub"], params=params)
        data = response.json()
        records = data.get("xsearch", {}).get("records", 0)
        print(f"   ✅ OK - {records} forskningspublikationer")
        return True
    except Exception as e:
        print(f"   ❌ FEL: {e}")
        return False


async def run_all_tests():
    """Kör alla tester."""
    print("=" * 60)
    print("KB MCP Server - Testsvit")
    print("=" * 60)
    
    tests = [
        test_libris_xsearch,
        test_libris_xl,
        test_ksamsok,
        test_oaipmh,
        test_idkb,
        test_swepub,
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
    
    await api_client.close()
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Resultat: {passed}/{total} tester godkända")
    print("=" * 60)
    
    return all(results)


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
