# -*- coding: utf-8 -*-
"""03 — Normaliza DNS + geo em um grafo tipado (nós/arestas) e exporta formatos.

Entradas : data/raw/dns_records.json, data/raw/geo.json
Saídas   : data/nodes.json, data/edges.json, data/hosts.csv, data/graph.graphml,
           data/graph_core.json (payload pronto para o three.js)
"""
import csv, html, json, os, re, sys, time, zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)
from seeds import RESOLVER_IPS, SERVICES, ROOT_OPERATORS

CONTINENT_PT = {
    "AF": "África", "AN": "Antártida", "AS": "Ásia", "EU": "Europa",
    "NA": "América do Norte", "OC": "Oceania", "SA": "América do Sul",
}

nodes = {}          # id -> dict
edges = []          # {source,target,type,layer}


def norm(nid):
    """FQDN é case-insensitive: canoniza em minúsculas (Windows/Obsidian também são
    case-insensitive em nomes de arquivo e colidiriam em notas distintas)."""
    if isinstance(nid, str) and " " not in nid and "." in nid and not nid.startswith("."):
        return nid.lower()
    return nid


def node(nid, **kw):
    nid = norm(nid)
    n = nodes.get(nid)
    if n is None:
        nodes[nid] = {"id": nid, **kw}
        return nodes[nid]
    n.update({k: v for k, v in kw.items() if v not in (None, "", [])})
    return n


def edge(a, b, etype, layer):
    a, b = norm(a), norm(b)
    if a and b:
        edges.append({"source": a, "target": b, "type": etype, "layer": layer})


def main():
    dns = json.load(open(os.path.join(RAW, "dns_records.json"), encoding="utf-8"))
    geo = json.load(open(os.path.join(RAW, "geo.json"), encoding="utf-8"))
    try:
        ptr_map = json.load(open(os.path.join(RAW, "ptr.json"), encoding="utf-8"))["ptr"]
    except Exception:
        ptr_map = {}
    recs, g = dns["records"], geo["geo"]

    # ---------- hubs ------------------------------------------------------
    node("Zona Raiz (.)", kind="hub", layer=0, title="Zona Raiz (.)")
    node("Zona raiz — servidores homing", kind="hub", layer=0)

    # ---------- A) roots --------------------------------------------------
    for letter, host in dns.get("roots", {}).items():
        op, cc, oname = ROOT_OPERATORS.get(letter, ("?", "?", "?"))
        r = recs.get(host, {})
        node(host, kind="root", layer=1, letter=letter, operator=op,
             operator_kind=oname, operator_cc=cc,
             ipv4=len(r.get("A", [])), ipv6=len(r.get("AAAA", [])))
        edge("Zona Raiz (.)", host, "zona raiz servida por", 1)

    # ---------- B) TLDs ---------------------------------------------------
    for tld, nsl in dns.get("tld_ns", {}).items():
        nid = f"TLD .{tld}"
        node(nid, kind="tld", layer=2, tld=tld, ns_count=len(nsl))
        edge("Zona Raiz (.)", nid, "delegação da raiz", 2)
        for ns in nsl:
            node(ns, kind="ns", layer=4)
            edge(nid, ns, "nameserver autoritativo", 4)
            for ip in recs.get(ns, {}).get("A", []):
                node(ip, kind="ip", layer=5, ipv6=False)
                edge(ns, ip, "resolve para (A)", 5)
            for ip in recs.get(ns, {}).get("AAAA", []):
                node(ip, kind="ip", layer=5, ipv6=True)
                edge(ns, ip, "resolve para (AAAA)", 5)

    # ---------- C) serviços ----------------------------------------------
    for dom, nsl in dns.get("service_ns", {}).items():
        org, cc = SERVICES.get(dom, ("", ""))
        r = recs.get(dom, {})
        node(dom, kind="service", layer=3, org=org, org_cc=cc,
             ipv4=len(r.get("A", [])), ipv6=len(r.get("AAAA", [])))
        tld = dom.rsplit(".", 1)[-1]
        if f"TLD .{tld}" in nodes:
            edge(dom, f"TLD .{tld}", "registrado sob", 3)
            nodes[f"TLD .{tld}"].setdefault("domains", 0)
            nodes[f"TLD .{tld}"]["domains"] += 1
        for ns in nsl:
            node(ns, kind="ns", layer=4)
            edge(dom, ns, "nameserver autoritativo", 4)
            for ip in recs.get(ns, {}).get("A", []):
                node(ip, kind="ip", layer=5, ipv6=False)
                edge(ns, ip, "resolve para (A)", 5)
            for ip in recs.get(ns, {}).get("AAAA", []):
                node(ip, kind="ip", layer=5, ipv6=True)
                edge(ns, ip, "resolve para (AAAA)", 5)
        for ip in r.get("A", []):
            node(ip, kind="ip", layer=5, ipv6=False)
            edge(dom, ip, "endpoint (A)", 5)
        for ip in r.get("AAAA", []):
            node(ip, kind="ip", layer=5, ipv6=True)
            edge(dom, ip, "endpoint (AAAA)", 5)

    # ---------- D) resolvedores públicos ---------------------------------
    for ip, (desc, org) in dns.get("resolver_ips", {}).items():
        node(ip, kind="ip", layer=5, ipv6=(":" in ip), resolver=True,
             resolver_desc=desc, resolver_org=org)
        os_node = f"Resolvedor {org}"
        node(os_node, kind="resolver_org", layer=4)
        edge(os_node, ip, "resolve consultas em", 5)

    # ---------- enriquecimento geográfico --------------------------------
    # a ip-api às vezes devolve nomes diferentes para o mesmo país ("Netherlands"
    # e "The Netherlands"): canoniza por código ISO.
    cc_canon = {}
    for ip, meta in g.items():
        cc0 = meta.get("countryCode") or "??"
        nm0 = meta.get("country") or "Desconhecido"
        cur = cc_canon.get(cc0)
        if cur is None or (len(nm0), nm0) < (len(cur), cur):
            cc_canon[cc0] = nm0

    for ip, meta in g.items():
        if ip not in nodes:
            node(ip, kind="ip", layer=5, ipv6=(":" in ip))
        cc = meta.get("countryCode") or "??"
        country = cc_canon.get(cc, "Desconhecido")
        cont = CONTINENT_PT.get(meta.get("continentCode") or "", "Desconhecido")
        city = meta.get("city") or None
        asn_raw = meta.get("as") or ""
        asn_id = asn_raw.split(" ", 1)[0] if asn_raw else None
        asn_name = asn_raw.split(" ", 1)[1] if " " in asn_raw else asn_raw

        nodes[ip].update({
            "country": country, "country_cc": cc, "continent": cont,
            "region": meta.get("regionName"), "city": city,
            "lat": meta.get("lat"), "lon": meta.get("lon"),
            "timezone": meta.get("timezone"), "asn": asn_id, "asn_name": asn_name,
            "asn_full": asn_raw if asn_id else None,
            "isp": meta.get("isp"), "org": meta.get("org"),
            "ptr": ptr_map.get(ip) or None,
            "hosting": meta.get("hosting", False), "mobile": meta.get("mobile", False),
            "proxy": meta.get("proxy", False), "geolocated": True,
        })

        node(country, kind="country", layer=7, cc=cc, continent=cont)
        node(cont, kind="continent", layer=8)
        edge(country, cont, "localizado em", 8)
        edge(ip, country, "geolocalizado em", 7)

        if city:
            cid = f"{city}, {cc}"
            node(cid, kind="city", layer=6, city=city, cc=cc, country=country,
                 continent=cont, lat=meta.get("lat"), lon=meta.get("lon"))
            edge(cid, country, "pertence a", 7)
            edge(ip, cid, "ponto de presença em", 6)

        if asn_id:
            aid = asn_raw
            node(aid, kind="asn", layer=6, asn=asn_id, asn_name=asn_name,
                 isp=meta.get("isp"), org=meta.get("org"))
            edge(ip, aid, "anunciado por", 6)
        ptr = ptr_map.get(ip)
        if ptr:
            if ptr not in nodes:
                node(ptr, kind="ptr", layer=4)
            edge(ip, ptr, "PTR", 4)

    # hostnames de resolvedores conhecidos
    for h in ["one.one.one.one", "dns.google", "dns.quad9.net", "dns0.eu"]:
        if h in recs and recs[h].get("A"):
            node(h, kind="resolver_host", layer=4)
            for ip in recs[h]["A"]:
                edge(h, ip, "resolve para (A)", 5)

    # ---------- deduplica arestas (mesma origem, destino e tipo) ----------
    _uniq = {}
    for e in edges:
        _uniq[(e["source"], e["target"], e["type"])] = e
    edges[:] = _uniq.values()

    # ---------- pendura órfãos no hub ------------------------------------
    linked = {e["source"] for e in edges} | {e["target"] for e in edges}
    for nid, n in nodes.items():
        if nid not in linked and n.get("kind") != "hub":
            edge("Zona raiz — servidores homing", nid, "sem aresta DNS direta", 0)

    # ---------- estatísticas ---------------------------------------------
    kinds = Counter(n["kind"] for n in nodes.values())
    etypes = Counter(e["type"] for e in edges)
    ips = [n for n in nodes.values() if n["kind"] == "ip"]
    asns = Counter(n["asn"] for n in ips if n.get("asn"))
    cities = Counter(f"{n.get('city')}, {n.get('country_cc')}" for n in ips if n.get("city"))
    countries = Counter(n.get("country_cc") for n in ips if n.get("country_cc"))
    layers = Counter(n.get("layer", 0) for n in nodes.values())

    stats = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "nodes": len(nodes), "edges": len(edges),
        "nodes_by_kind": dict(kinds.most_common()),
        "nodes_by_layer": {str(k): v for k, v in sorted(layers.items())},
        "edges_by_type": dict(etypes.most_common()),
        "ips_total": len(ips),
        "ips_geolocated": sum(1 for n in ips if n.get("geolocated")),
        "ips_v4": sum(1 for n in ips if not n.get("ipv6")),
        "ips_v6": sum(1 for n in ips if n.get("ipv6")),
        "ips_hosting": sum(1 for n in ips if n.get("hosting")),
        "ptr_coverage": sum(1 for n in nodes.values()
                            if n["kind"] == "ip" and n.get("ptr")),
        "countries": len(countries), "cities": len(cities), "asns": len(asns),
        "top_countries": countries.most_common(15),
        "top_cities": cities.most_common(15),
        "top_asns": [(a, c) for a, c in asns.most_common(15)],
        "dns_queries": dns.get("counts", {}),
        "geo_api": geo.get("counts", {}),
    }

    json.dump({"stats": stats, "nodes": list(nodes.values()), "edges": edges},
              open(os.path.join(DATA, "nodes_edges_full.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(list(nodes.values()),
              open(os.path.join(DATA, "nodes.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(edges, open(os.path.join(DATA, "edges.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(stats, open(os.path.join(DATA, "stats.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ---------- CSV de hosts ---------------------------------------------
    with open(os.path.join(DATA, "hosts.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ip", "familia", "ptr", "asn", "asn_name", "isp", "org", "cidade",
                    "regiao", "pais", "pais_cc", "continente", "lat", "lon", "timezone",
                    "datacenter", "resolvedor_publico"])
        for n in sorted(ips, key=lambda x: (x.get("country_cc") or "", x.get("city") or "")):
            w.writerow([n["id"], "IPv6" if n.get("ipv6") else "IPv4", n.get("ptr", ""),
                        n.get("asn", ""), n.get("asn_name", ""), n.get("isp", ""),
                        n.get("org", ""), n.get("city", ""), n.get("region", ""),
                        n.get("country", ""), n.get("country_cc", ""),
                        n.get("continent", ""), n.get("lat", ""), n.get("lon", ""),
                        n.get("timezone", ""), "sim" if n.get("hosting") else "não",
                        "sim" if n.get("resolver") else "não"])

    # ---------- GraphML (Gephi / yEd / Cytoscape) ------------------------
    def esc(s):
        return html.escape(str(s), quote=True)

    with open(os.path.join(DATA, "graph.graphml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n'
                '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">\n')
        for k, t in [("kind", "string"), ("layer", "int"), ("country_cc", "string"),
                     ("city", "string"), ("asn", "string"), ("lat", "double"),
                     ("lon", "double"), ("ipv6", "boolean")]:
            f.write(f'  <key id="{k}" for="node" attr.name="{k}" attr.type="{t}"/>\n')
        f.write('  <key id="etype" for="edge" attr.name="type" attr.type="string"/>\n')
        f.write('  <graph id="G" edgedefault="undirected">\n')
        for n in nodes.values():
            f.write(f'    <node id="{esc(n["id"])}">\n')
            for k in ("kind", "layer", "country_cc", "city", "asn", "lat", "lon", "ipv6"):
                if n.get(k) is not None:
                    v = str(n[k]).lower() if k == "ipv6" else n[k]
                    f.write(f'      <data key="{k}">{esc(v)}</data>\n')
            f.write("    </node>\n")
        for i, e in enumerate(edges):
            f.write(f'    <edge id="e{i}" source="{esc(e["source"])}" '
                    f'target="{esc(e["target"])}"><data key="etype">{esc(e["type"])}'
                    f'</data></edge>\n')
        f.write("  </graph>\n</graphml>\n")

    # ---------- payload para three.js ------------------------------------
    # posição 3D determinística: camada -> Y, lat/lon -> X/Z (equiretangular),
    # e um anel por categoria quando não há geo (nós de infraestrutura).
    import math

    def sh(s):
        """CRC32 no lugar de hash(): hash() de str é salgado por processo
        (PYTHONHASHSEED), o que mudava a posição dos nós sem geo a cada execução
        e quebrava a reprodutibilidade prometida pelo projeto."""
        return zlib.crc32(s.encode("utf-8"))

    ring = defaultdict(int)
    core_nodes = []
    for n in nodes.values():
        lat, lon = n.get("lat"), n.get("lon")
        y = (n.get("layer", 0) - 4) * 1.70
        if lat is not None and lon is not None:
            x = math.radians(lon) * 5.2
            z = -math.radians(lat) * 5.2
        else:
            k = n.get("kind", "x")
            i = ring[k]
            ring[k] += 1
            angle = (i * 0.7 + sh(k) % 7) % (2 * math.pi)
            r = 7.0 + (sh(k) % 5) * 0.6
            x, z = r * math.cos(angle), r * math.sin(angle)
        core_nodes.append({
            "id": n["id"], "kind": n.get("kind"), "layer": n.get("layer"),
            "x": round(x, 4), "y": round(y, 4), "z": round(z, 4),
            "lat": lat, "lon": lon, "country": n.get("country") or "",
            "cc": n.get("country_cc") or n.get("cc") or "",
            "city": n.get("city") or "", "asn": n.get("asn") or "",
            "ptr": n.get("ptr") or "", "resolver": bool(n.get("resolver")),
        })
    json.dump({
        "generated_at": stats["generated_at"],
        "note": "camada -> Y (eixo hierárquico), lat/lon -> X/Z (equiretangular). "
                "Nós sem geo são distribuídos em anéis por categoria.",
        "stats": stats, "nodes": core_nodes,
        "edges": [{"source": e["source"], "target": e["target"], "type": e["type"]}
                  for e in edges],
    }, open(os.path.join(DATA, "graph_core.json"), "w", encoding="utf-8"),
        ensure_ascii=False)

    print(json.dumps(stats, ensure_ascii=False, indent=1)[:2600])
    print(f"\nOK  nodes={len(nodes)} edges={len(edges)} -> data/")


if __name__ == "__main__":
    main()
