# -*- coding: utf-8 -*-
"""04 — Gera o vault Obsidian (markdown + .obsidian) a partir do grafo normalizado.

Entradas: data/nodes_edges_full.json, data/stats.json
Saída   : vault/   (abrir esta pasta como vault no Obsidian)
"""
import json, os, re, sys, time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
VAULT = os.path.join(ROOT, "grafo")
sys.path.insert(0, HERE)

BAD = r'[\\/:*?"<>|#^\[\]]'


def sanitize(name, ipv6=False):
    n = str(name).strip()
    if ipv6:
        n = n.replace(":", "-")
    n = re.sub(BAD, "-", n)
    n = re.sub(r"\s+", " ", n).strip(" .")
    return n[:120] or "sem-nome"


def slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s or "n"


FOLDER = {
    "hub": "000 HUB",
    "root": "200 Infraestrutura/210 Raiz",
    "tld": "200 Infraestrutura/220 TLDs",
    "service": "200 Infraestrutura/230 Serviços",
    "ns": "200 Infraestrutura/240 Nameservers",
    "ptr": "200 Infraestrutura/240 Nameservers",
    "resolver_host": "200 Infraestrutura/240 Nameservers",
    "resolver_org": "200 Infraestrutura/250 Resolvedores públicos",
    "ip": "300 Hosts",
    "asn": "400 Redes (ASN)",
    "city": "500 Geografia/510 Cidades",
    "country": "500 Geografia/520 Países",
    "continent": "500 Geografia/530 Continentes",
}

KIND_PT = {
    "hub": "HUB / índice", "root": "servidor raiz", "tld": "zona de topo (TLD)",
    "service": "serviço / domínio", "ns": "nameserver autoritativo",
    "ptr": "nome reverso (PTR)", "resolver_host": "hostname de resolvedor",
    "resolver_org": "operador de resolvedor público", "ip": "host (endereço IP)",
    "asn": "sistema autônomo (ASN)", "city": "cidade / PoP",
    "country": "país", "continent": "continente",
}
LAYER_PT = {
    0: "0 — raiz do espaço de nomes / hubs",
    1: "1 — servidores raiz (anycast global)",
    2: "2 — zonas de topo (TLD)",
    3: "3 — domínios e serviços",
    4: "4 — nameservers e nomes reversos",
    5: "5 — endereços IP (conectividade)",
    6: "6 — rede (ASN) e ponto de presença (cidade)",
    7: "7 — geografia (país)",
    8: "8 — continente",
}

warn = []

# Nomes em pt-BR para a camada geográfica (o dataset cru vem da ip-api em inglês;
# os continentes já são traduzidos no passo 03 — a camada fica consistente).
COUNTRY_PT = {
    "AE": "Emirados Árabes Unidos", "AR": "Argentina", "AT": "Áustria",
    "AU": "Austrália", "BE": "Bélgica", "BG": "Bulgária", "BO": "Bolívia",
    "BR": "Brasil", "CA": "Canadá", "CH": "Suíça", "CL": "Chile", "CN": "China",
    "CR": "Costa Rica", "CY": "Chipre", "CZ": "Tchéquia", "DE": "Alemanha",
    "DK": "Dinamarca", "EC": "Equador", "EG": "Egito", "ES": "Espanha",
    "FI": "Finlândia", "FR": "França", "GB": "Reino Unido", "GR": "Grécia",
    "HU": "Hungria", "ID": "Indonésia", "IE": "Irlanda", "IL": "Israel",
    "IN": "Índia", "IT": "Itália", "JP": "Japão", "KE": "Quênia",
    "KR": "Coreia do Sul", "MA": "Marrocos", "MX": "México", "NG": "Nigéria",
    "NL": "Países Baixos", "NO": "Noruega", "NZ": "Nova Zelândia", "PE": "Peru",
    "PK": "Paquistão", "PL": "Polônia", "PT": "Portugal", "RO": "Romênia",
    "RU": "Rússia", "SA": "Arábia Saudita", "SE": "Suécia", "SG": "Singapura",
    "TR": "Turquia", "UA": "Ucrânia", "US": "Estados Unidos", "UY": "Uruguai",
    "VE": "Venezuela", "ZA": "África do Sul",
}

# Notas de conteúdo (teoria, MOCs, guias): não são nós do grafo, mas precisam ser
# linkadas como wikilink para aparecerem no Graph View.
CONTENT_TITLES = {
    # 100 Teoria
    "Armazenamento de nós em grafos", "Modelo de nós e arestas",
    "Hierarquia DNS como grafo", "Anycast e geolocalização de IP",
    "Camadas do grafo", "Métricas do grafo", "Roadmap — visualização three.js",
    "Direção visual e tipografia", "Coleta, proveniência e reprodutibilidade",
    "Como abrir este vault no Obsidian", "Dicionário de tags",
    # 000 HUB / 600 Dados
    "Índice do grafo", "MOC Infraestrutura", "MOC Geografia", "MOC Redes (ASN)",
    "Estatísticas do dataset", "Ranking de nós por grau", "Datasets e arquivos",
}


def clean_vault():
    """Apaga o conteúdo gerado do vault antes de escrever.

    Sem isso, notas de nós que desapareceram entre duas coletas ficam para trás e
    viram órfãs (o validador 06 acusa justamente isso). `.obsidian/` é preservado
    porque guarda a configuração do Graph View do usuário; os diretórios de
    conteúdo são recriados abaixo.
    """
    import shutil
    for d in os.listdir(VAULT):
        p = os.path.join(VAULT, d)
        if os.path.isdir(p) and not d.startswith("."):
            shutil.rmtree(p, ignore_errors=True)
            print(f"   limpo: {d}/")


def main():
    gd = json.load(open(os.path.join(DATA, "nodes_edges_full.json"), encoding="utf-8"))
    stats = gd["stats"]
    nodes = {n["id"]: n for n in gd["nodes"]}
    edges = gd["edges"]

    if "--no-clean" not in sys.argv:
        clean_vault()

    # ---- nome da nota por nó -------------------------------------------
    name = {}
    used = {}
    for nid, n in nodes.items():
        if n["kind"] == "ip":
            nm = ("IP6 " if n.get("ipv6") else "IP ") + sanitize(nid, ipv6=True)
        elif n["kind"] == "country" and n.get("cc") in COUNTRY_PT:
            nm = COUNTRY_PT[n["cc"]]
        else:
            nm = sanitize(nid)
        if nm in used and used[nm] != nid:
            old = used[nm]
            nm = nm + " (" + slug(n.get("kind", "?")) + ")"
            while nm in used:
                nm += "·"
            warn.append(f"colisão de nome: {nid!r} vs {old!r} -> {nm!r}")
        used[nm] = nid
        name[nid] = nm

    out_edges = defaultdict(list)
    in_edges = defaultdict(list)
    degree = Counter()
    for e in edges:
        s, t = e["source"], e["target"]
        if s not in name or t not in name:
            continue
        out_edges[s].append(e)
        in_edges[t].append(e)
        degree[s] += 1
        degree[t] += 1

    def L(nid, label=None):
        if nid in CONTENT_TITLES:            # nota de conteúdo, não nó do grafo
            return f"[[{nid}{'|' + label if label else ''}]]"
        return f"[[{name[nid]}{'|' + label if label else ''}]]" if nid in name else f"`{nid}`"

    written = 0
    paths = {}

    def write(nid, text):
        nonlocal written
        n = nodes[nid]
        folder = FOLDER.get(n["kind"], "600 Dados")
        path = os.path.join(VAULT, folder, name[nid] + ".md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        paths[nid] = path
        written += 1

    def fm(n, extra_tags=(), extra=None):
        d = {
            "tipo": n["kind"], "camada": n.get("layer", 0),
            "grau": degree.get(n["id"], 0),
        }
        tags = [f"no/{n['kind']}", f"camada/{n.get('layer', 0)}"]
        if n.get("country_cc"):
            d["pais_cc"] = n["country_cc"]
            d["pais"] = COUNTRY_PT.get(n["country_cc"], n.get("country"))
            tags.append("geo/" + slug(n["country_cc"]))
        if n.get("city"):
            d["cidade"] = n["city"]
        if n.get("asn"):
            d["asn"] = n["asn"]
        if n.get("ptr"):
            d["ptr"] = n["ptr"]
        if n.get("lat") is not None:
            d["lat"] = n["lat"]
            d["lon"] = n["lon"]
        if n.get("ipv6"):
            d["familia"] = "IPv6"
        elif n["kind"] == "ip":
            d["familia"] = "IPv4"
        if extra:
            d.update(extra)
        tags += list(extra_tags)
        lines = ["---"]
        for k, v in d.items():
            if isinstance(v, str) and re.search(r'[:#\[\]{},"\']', v):
                v = '"' + v.replace('"', "'") + '"'
            lines.append(f"{k}: {v}")
        lines.append("tags: [" + ", ".join(tags) + "]")
        lines.append("---")
        return "\n".join(lines)

    def edges_block(nid, limit=400):
        out = [f"- **{e['type']}** → {L(e['target'])}" for e in out_edges[nid]]
        inn = [f"- {L(e['source'])} → **{e['type']}**" for e in in_edges[nid]]
        txt = ""
        if out:
            txt += "### Arestas de saída\n\n" + "\n".join(out[:limit]) + "\n\n"
        if inn:
            txt += "### Arestas de entrada\n\n" + "\n".join(inn[:limit]) + "\n\n"
        return txt

    # ============================ 1. HUBs ================================
    write("Zona Raiz (.)", f"""{fm(nodes['Zona Raiz (.)'])}
# Zona Raiz (.)

Nó agregador: representa a **raiz do espaço de nomes DNS**. Não é um host físico —
é a função que os 13 servidores raiz executam em qualquercast global.

- Servidores raiz homing: {', '.join(L(f'{l}.root-servers.net') for l in 'abcdefghijklm')}
- Zonas de topo delegadas neste dataset: **{sum(1 for n in nodes.values() if n['kind'] == 'tld')}**

## Ligações

{edges_block('Zona Raiz (.)')}
""")
    write("Zona raiz — servidores homing", f"""{fm(nodes['Zona raiz — servidores homing'])}
# Zona raiz — servidores homing

Nó de conveniência que pendura os elementos sem aresta DNS direta (nomes reversos
isolados, ASNs sem IP associado, etc.), para que o grafo não tenha ilhas soltas.

{edges_block('Zona raiz — servidores homing')}
""")

    # ============================ 2. infra ===============================
    for nid, n in nodes.items():
        k = n["kind"]
        if k == "root":
            ips = [(e["target"], nodes[e["target"]]) for e in out_edges[nid]]
            v4 = [i for i, m in ips if not m.get("ipv6")]
            v6 = [i for i, m in ips if m.get("ipv6")]
            rows = "\n".join(
                f"| {L(i)} | {'IPv6' if m.get('ipv6') else 'IPv4'} | {m.get('city') or '—'} "
                f"| {m.get('country') or '—'} | {m.get('asn') or '—'} |"
                for i, m in ips)
            write(nid, f"""{fm(n, extra_tags=[])}
# {name[nid]}

| campo | valor |
|---|---|
| Letra | `{n.get('letter')}` |
| Operador | {n.get('operator_kind')} |
| Operador (formal) | {n.get('operator')} |
| País do operador | {n.get('operator_cc')} |
| Endereços IPv4 | {n.get('ipv4', 0)} |
| Endereços IPv6 | {n.get('ipv6', 0)} |

## Endereços e PoPs observados

| Endereço | Família | Cidade | País | ASN |
|---|---|---|---|---|
{rows}

> [!info] Anycast
> Um servidor raiz é anunciado de **dezenas a centenas de PoPs**. O endereço é o mesmo
> no mundo inteiro; a geolocalização acima aponta o PoP que **respondeu** à coleta.

{edges_block(nid)}
""")
        elif k == "tld":
            ns = [e["target"] for e in out_edges[nid] if e["type"] == "nameserver autoritativo"]
            doms = [e["source"] for e in in_edges[nid] if e["type"] == "registrado sob"]
            rows = "\n".join(f"| {L(x)} | {nodes.get(x, {}).get('org') or '—'} |" for x in doms)
            write(nid, f"""{fm(n)}
# {name[nid]}

Zona de topo `.{n.get('tld')}` · **{len(ns)}** nameservers autoritativos observados.

## Nameservers

{chr(10).join('- ' + L(x) for x in ns) or '_nenhum_'}

## Domínios deste dataset registrados sob esta zona

| Domínio | Organização |
|---|---|
{rows or '| — | — |'}

{edges_block(nid)}
""")
        elif k == "service":
            ns = [e["target"] for e in out_edges[nid] if e["type"] == "nameserver autoritativo"]
            eps = [e["target"] for e in out_edges[nid] if e["type"].startswith("endpoint")]
            ns_ips = [x for x in ns for e2 in out_edges.get(x, []) for x in [e2["target"]]]
            allip = sorted(set(eps) | set(ns_ips))
            cc = Counter(nodes[i].get("country") for i in allip if nodes[i].get("country"))
            cty = Counter(f"{nodes[i].get('city')} ({nodes[i].get('country_cc')})"
                          for i in allip if nodes[i].get("city"))
            asn = Counter(nodes[i].get("asn_full") for i in allip if nodes[i].get("asn_name"))
            geo_rows = "\n".join(f"| {c} | {v} |" for c, v in cty.most_common(12))
            write(nid, f"""{fm(n)}
# {name[nid]}

Serviço/domínio · organização **{n.get('org') or '—'}** ({n.get('org_cc') or '—'}).
Zona de topo: {L('TLD .' + nid.rsplit('.', 1)[-1]) if ('TLD .' + nid.rsplit('.', 1)[-1]) in name else '—'}

## Nameservers autoritativos

{chr(10).join('- ' + L(x) for x in ns) or '_nenhum_'}

## Endpoints e IPs associados ({len(allip)})

| Endereço | Cidade | País | ASN | PTR |
|---|---|---|---|---|
{chr(10).join(f"| {L(i)} | {nodes[i].get('city') or '—'} | {nodes[i].get('country') or '—'} | {nodes[i].get('asn') or '—'} | {nodes[i].get('ptr') or '—'} |" for i in eps[:40])}

## Onde este serviço está localizado

| Cidade (PoP observado) | IPs |
|---|---|
{geo_rows or '| — | — |'}

## Países

{chr(10).join(f'- {c}: {v}' for c, v in cc.most_common()) or '_sem geolocalização_'}

## Redes (ASN) anunciantes

{chr(10).join(f'- {L(a)} ({v})' for a, v in asn.most_common()) or '_—_'}

{edges_block(nid)}
""")
        elif k in ("ns", "ptr", "resolver_host"):
            ips = [e["target"] for e in out_edges[nid]
                   if e["type"].startswith("resolve para")]
            zones = [e["source"] for e in in_edges[nid]
                     if e["type"] == "nameserver autoritativo"]
            rows = "\n".join(
                f"| {L(i)} | {'IPv6' if nodes[i].get('ipv6') else 'IPv4'} | "
                f"{nodes[i].get('city') or '—'} | {nodes[i].get('country') or '—'} | "
                f"{nodes[i].get('asn') or '—'} | {nodes[i].get('ptr') or '—'} |" for i in ips)
            write(nid, f"""{fm(n)}
# {name[nid]}

Função: **{KIND_PT[k]}**

| campo | valor |
|---|---|
| Arestas | {degree.get(nid, 0)} |
| Zonas servidas | {len(zones)} |
| Endereços | {len(ips)} |

## Zonas para as quais este nome responde

{chr(10).join('- ' + L(z) for z in zones) or '_nenhuma (aparece apenas como nome reverso)_'}

## Endereços resolvidos

| Endereço | Família | Cidade | País | ASN | PTR |
|---|---|---|---|---|---|
{rows or '| — | — | — | — | — | — |'}

{edges_block(nid)}
""")
        elif k == "resolver_org":
            ips = [e["target"] for e in out_edges[nid]]
            rows = "\n".join(
                f"| {L(i)} | {nodes[i].get('ip') or i} | {nodes[i].get('resolver_desc') or '—'} | "
                f"{nodes[i].get('city') or '—'} | {nodes[i].get('country') or '—'} | "
                f"{nodes[i].get('asn') or '—'} |" for i in ips)
            write(nid, f"""{fm(n)}
# {name[nid]}

Resolvedor público (anycast). Endereços conhecidos usados na coleta:

| Nó | Endereço | Papel | Cidade | País | ASN |
|---|---|---|---|---|---|
{rows or '| — | — | — | — | — | — |'}

{edges_block(nid)}
""")

    # ============================ 3. hosts IP ============================
    for nid, n in nodes.items():
        if n["kind"] != "ip":
            continue
        hosts = [e["source"] for e in in_edges[nid]
                 if e["type"].startswith(("resolve para", "endpoint"))]
        zones = []
        for h in hosts:
            for e2 in in_edges.get(h, []):
                if e2["type"] == "nameserver autoritativo":
                    zones.append(e2["source"])
        cid = f"{n.get('city')}, {n.get('country_cc')}"
        geo_line = " → ".join(filter(None, [
            L(cid) if cid in name else None,
            L(n.get("country")) if n.get("country") in name else None,
            L(n.get("continent")) if n.get("continent") in name else None,
        ]))
        write(nid, f"""{fm(n)}
# {name[nid]}

`{nid}` — **{'IPv6' if n.get('ipv6') else 'IPv4'}** · {KIND_PT['ip']}
{('> [!warning] Nome do arquivo' + chr(10) + '> Windows proíbe `:` em nomes de arquivo — por isso os `:` do endereço viram `-` no nome da nota. O endereço real é o código acima.' + chr(10)) if n.get('ipv6') else ''}
> [!info] Localização
> {n.get('city') or 'cidade não informada'}, {n.get('country') or '—'}
> ({n.get('lat')}, {n.get('lon')}) · fuso `{n.get('timezone') or '—'}`
> {'· **resolvedor público**' if n.get('resolver') else ''}

## Identidade de rede

| campo | valor |
|---|---|
| PTR (nome reverso) | {L(n['ptr']) if n.get('ptr') in name else '`' + (n.get('ptr') or '—') + '`'} |
| ASN | {L(n['asn_full']) if n.get('asn_full') in name else '—'} |
| ISP | {n.get('isp') or '—'} |
| Organização | {n.get('org') or '—'} |
| Região | {n.get('region') or '—'} |
| Datacenter/hosting | {'sim' if n.get('hosting') else 'não'} |
| Móvel | {'sim' if n.get('mobile') else 'não'} |
| Proxy/VPN | {'sim' if n.get('proxy') else 'não'} |
| Grau no grafo | {degree.get(nid, 0)} |

## Hierarquia geográfica

{geo_line or '_sem geolocalização_'}

## Alcançado por

{chr(10).join('- ' + L(h) for h in hosts) or '_só apareceu como endereço de nomes reversos ou resolvedores_'}

## Zonas atendidas por estes nomes

{chr(10).join('- ' + L(z) for z in sorted(set(zones))) or '_—_'}

{edges_block(nid)}
""")

    # ============================ 4. ASN / geo ===========================
    for nid, n in nodes.items():
        k = n["kind"]
        if k == "asn":
            ips = [e["source"] for e in in_edges[nid]]
            cty = Counter(f"{nodes[i].get('city')}, {nodes[i].get('country_cc')}"
                          for i in ips if nodes[i].get("city"))
            cc = Counter(nodes[i].get("country") for i in ips if nodes[i].get("country"))
            rows = "\n".join(
                f"| {L(i)} | {nodes[i].get('ptr') or '—'} | {nodes[i].get('city') or '—'} | "
                f"{nodes[i].get('country') or '—'} | {'sim' if nodes[i].get('hosting') else 'não'} |"
                for i in sorted(ips, key=lambda x: (nodes[x].get("country_cc") or "",
                                                    nodes[x].get("city") or ""))[:60])
            write(nid, f"""{fm(n, extra_tags=['rede/asn'])}
# {name[nid]}

Sistema autônomo · **{len(ips)}** endereços neste dataset.

| campo | valor |
|---|---|
| ASN | `{n.get('asn')}` |
| Nome | {n.get('asn_name')} |
| ISP declarado | {n.get('isp') or '—'} |
| Org declarada | {n.get('org') or '—'} |
| Grau no grafo | {degree.get(nid, 0)} |

## Países de presença

{chr(10).join(f'- {L(c) if c in name else c}: {v}' for c, v in cc.most_common()) or '_—_'}

## Cidades / PoPs

{chr(10).join(f'- {L(c) if c in name else c}: {v}' for c, v in cty.most_common(20)) or '_—_'}

## Endereços anunciados

| Endereço | PTR | Cidade | País | Hosting |
|---|---|---|---|---|
{rows or '| — | — | — | — | — |'}

{edges_block(nid)}
""")
        elif k == "city":
            ips = [e["source"] for e in in_edges[nid]]
            asn = Counter(nodes[i].get("asn_full") for i in ips if nodes[i].get("asn_name"))
            write(nid, f"""{fm(n, extra_tags=['geo/cidade'])}
# {name[nid]}

PoP / cidade: **{len(ips)}** endereços observados.
Coordenadas de referência: `{n.get('lat')}, {n.get('lon')}` — {L(n.get('country')) if n.get('country') in name else ''} {L(n.get('continent')) if n.get('continent') in name else ''}

## Redes presentes

{chr(10).join(f'- {L(a)} ({v})' for a, v in asn.most_common(15)) or '_—_'}

## Endereços

| Endereço | PTR | ASN | País |
|---|---|---|---|
{chr(10).join(f"| {L(i)} | {nodes[i].get('ptr') or '—'} | {nodes[i].get('asn') or '—'} | {nodes[i].get('country') or '—'} |" for i in sorted(set(ips)))}

{edges_block(nid)}
""")
        elif k == "country":
            ips = [e["source"] for e in in_edges[nid]
                   if nodes[e["source"]]["kind"] == "ip"]
            cities_in = [e["source"] for e in in_edges[nid]
                         if nodes[e["source"]]["kind"] == "city"]
            asn = Counter(nodes[i].get("asn_full") for i in ips if nodes[i].get("asn_name"))
            alias = [] if any(ch in nid for ch in "'\"") else [nid]
            write(nid, f"""{fm(n, extra_tags=['geo/pais'], extra={'aliases': alias} if alias else None)}
# {name[nid]}

`{n.get('cc')}` · {L(n.get('continent')) if n.get('continent') in name else ''}
> [!note] Nome no dataset
> A ip-api devolve `{nid}`; a nota é titulada em português e mantém o nome original
> como alias (linkável).

**{len(ips)}** endereços · **{len(cities_in)}** cidades · **{len(asn)}** redes.

## Cidades / PoPs

| Cidade | Endereços |
|---|---|
{chr(10).join(f"| {L(c)} | {len([e for e in in_edges.get(c, []) if nodes[e['source']]['kind'] == 'ip'])} |" for c in sorted(cities_in)) or '| — | — |'}

## Redes

{chr(10).join(f'- {L(a)} ({v})' for a, v in asn.most_common(20)) or '_—_'}

{edges_block(nid)}
""")
        elif k == "continent":
            kids = [e["source"] for e in in_edges[nid]]
            ips = [e["source"] for c in kids for e in in_edges.get(c, [])
                   if nodes[e["source"]]["kind"] == "ip"]
            cty = {nodes[i].get("city") for i in ips if nodes[i].get("city")}
            asn = Counter(nodes[i].get("asn_full") for i in ips if nodes[i].get("asn_name"))
            write(nid, f"""{fm(n, extra_tags=['geo/continente'])}
# {name[nid]}

**{len(ips)}** endereços · **{len(kids)}** países · **{len(cty)}** cidades.

## Países

| País | Endereços |
|---|---|
{chr(10).join(f"| {L(c)} | {len([e for e in in_edges.get(c, []) if nodes[e['source']]['kind'] == 'ip'])} |" for c in sorted(kids)) or '| — | — |'}

## Redes mais presentes

{chr(10).join(f'- {L(a)} ({v})' for a, v in asn.most_common(20)) or '_—_'}

{edges_block(nid)}
""")

    # ============================ 5. notas de conteúdo ===================
    os.makedirs(os.path.join(VAULT, "100 Teoria"), exist_ok=True)

    def theory(filename, text):
        nonlocal written
        p = os.path.join(VAULT, "100 Teoria", filename + ".md")
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
        written += 1

    theory("Armazenamento de nós em grafos", f"""---
tipo: teoria
tags: [teoria/grafos, moc]
---
# Armazenamento de nós em grafos

Um **grafo** é G = (V, E): um conjunto de nós (V) e arestas (E) que os relacionam.
Guardar informação *como grafo* significa aceitar três consequências:

1. **A identidade do dado é o nó, não a linha.** Um servidor SSH não "pertence" a uma
   tabela; ele existe como entidade e ganha significado pelas relações que acumula.
2. **A hierarquia é uma aresta tipada, não uma pasta.** `TLD .br → a.dns.br` e
   `a.dns.br → 200.160.0.x` são hierarquias *diferentes* (delegação e resolução) que
   convivem no mesmo nó.
3. **A consulta é navegação.** Não há JOIN: caminha-se de nó em nó.

## Por que isso descreve bem a internet

O DNS já **é** um grafo direcionado acíclico de delegação — a árvore de zonas. Sobreposto
a ele existe um segundo grafo, **físico**: nomes → endereços → ASNs → cidades. Este
projeto armazena exatamente esses dois grafos e as arestas que os costuram.

| Camada | Nó | Aresta | Semântica |
|---|---|---|---|
| {LAYER_PT[1]} | {L('a.root-servers.net')} | `zona raiz servida por` | função, não máquina |
| {LAYER_PT[2]} | TLD | `delegação da raiz` | autoridade de zona |
| {LAYER_PT[4]} | nameserver | `nameserver autoritativo` | quem responde por quem |
| {LAYER_PT[5]} | IP | `resolve para (A/AAAA)` | nomes → endereços |
| {LAYER_PT[6]} | cidade | `ponto de presença em` | onde a fibra chega |
| {LAYER_PT[7]} | país | `geolocalizado em` | jurisdição |

Ver também: {L('Camadas do grafo')} · {L('Modelo de nós e arestas')} ·
{L('Hierarquia DNS como grafo')} · {L('Métricas do grafo')}
""")
    theory("Modelo de nós e arestas", f"""---
tipo: teoria
tags: [teoria/modelo, moc]
---
# Modelo de nós e arestas

## Nós ({stats['nodes']} no total)

| tipo | quantidade | pasta |
|---|---|---|
""" + "\n".join(
        f"| {KIND_PT.get(k, k)} (`{k}`) | {v} | {FOLDER.get(k, '-')} |"
        for k, v in stats["nodes_by_kind"].items()) + f"""

## Arestas ({stats['edges']} no total)

| tipo de aresta | quantidade |
|---|---|
""" + "\n".join(f"| `{k}` | {v} |" for k, v in stats["edges_by_type"].items()) + """

## Arestas de conteúdo (curadas à mão)

| aresta | significado |
|---|---|
| `é exemplo de` | instância que ilustra um conceito |
| `contradiz` | dado que refuta uma hipótese (ex.: anycast vs. geo) |
| `inspira` | relação teórica (grafos de conhecimento, redes) |
| `das sementes` | entrada em `scripts/seeds.py` que originou o nó |

Ver [[Dicionário de tags]].
""")
    theory("Hierarquia DNS como grafo", f"""---
tipo: teoria
tags: [teoria/dns, moc]
---
# Hierarquia DNS como grafo

```
. (zona raiz)                     ← {sum(1 for n in nodes.values() if n['kind']=='root')} servidores anycast
├── .br            → a.dns.br …   ← {sum(1 for n in nodes.values() if n['kind']=='tld')} TLDs neste dataset
│   ├── globo.com  → ns1.globo.com …
│   │   └── 200.147.x.x → São Paulo, BR → ASN das operadoras
└── .com           → a.gtld-servers.net …
    └── google.com → ns1.google.com → 216.239.x.x → Ashburn, US
```

Dois grafos sobrepostos:

| | grafo de nomes | grafo físico |
|---|---|---|
| nós | zonas, domínios, nomes | IPs, ASNs, cidades, países |
| arestas | delegação, NS, CNAME | anúncio BGP, geolocalização |
| escala | milhões de nomes | ~76 mil ASNs, ~4 bilhões de IPs (IPv4) |
| falha típica | NXDOMAIN, SERVFAIL | rota, filtro, censura |

A ponte entre os dois é a aresta `resolve para (A/AAAA)` — é o único lugar em que o
mundo dos nomes toca o mundo dos cabos. **Todo gargalo de análise de infraestrutura vive
nessa ponte.**
""")
    theory("Anycast e geolocalização de IP", f"""---
tipo: teoria
tags: [teoria/anycast, moc]
---
# Anycast e geolocalização de IP

> [!warning] O dado geográfico deste projeto é *visto da coleta*, não do cadastro
> A coleta partiu de um único ponto (notebook do usuário, Brasil). Para endereços
> **anycast** (raiz, resolvedores públicos, CDNs), o PoP que responde é o mais próximo
> **daquele ponto**. O campo `lat/lon` do ip-api descreve o PoP que atendeu, não todos
> os PoPs do endereço.

Consequências práticas:

- `1.1.1.1` aparece aqui com uma cidade (a que atendeu) — na prática são ~300 PoPs.
- Endereços marcados `hosting: sim` ({stats['ips_hosting']} de {stats['ips_total']} neste
  dataset) revelam infraestrutura de datacenter/cloud, não residencial.
- PTR (`reverse`) é a melhor pista de função: `dns.google`, `ns1.uol.com.br`,
  `a.root-servers.net` dizem o que o endereço *faz*.

## Como o grafos lida com isso

O nó do IP guarda **um** ponto de presença, e o frontmatter traz `lat`/`lon` para o
filtro do Graph View; a aresta `ponto de presença em` liga o endereço à cidade. Na fase
three.js (ver {L('Roadmap — visualização three.js')}) a mesma escolha aparece como uma
esfera com os nós geo-posicionados e os nós anycast em anéis concêntricos.
""")
    theory("Camadas do grafo", f"""---
tipo: teoria
tags: [teoria/camadas, moc]
---
# Camadas do grafo

Cada nó tem `camada` (0–8) no frontmatter e a tag `#camada/N`. Serve para filtrar o
Graph View (`tag:#camada/5`) e para posicionar em Y no three.js.

| camada | papel | nós |
|---|---|---|
""" + "\n".join(
        f"| {LAYER_PT.get(int(k), k)} | {v} |" for k, v in stats["nodes_by_layer"].items())
      + f"""

No três componentes:

1. **camadas 0–4** — espaço de nomes (o DNS puro).
2. **camada 5** — endereçamento (`{stats['ips_total']}` IPs, `{stats['ips_v4']}` IPv4 /
   `{stats['ips_v6']}` IPv6).
3. **camadas 6–8** — geografia e rede (`{stats['asns']}` ASNs, `{stats['cities']}` cidades,
   `{stats['countries']}` países).
""")
    theory("Métricas do grafo", f"""---
tipo: teoria
tags: [teoria/metricas, moc]
---
# Métricas do grafo

| métrica | valor |
|---|---|
| Nós | {stats['nodes']} |
| Arestas | {stats['edges']} |
| Densidade | {round(2 * stats['edges'] / (stats['nodes'] * (stats['nodes'] - 1)), 6)} |
| Grau médio | {round(2 * stats['edges'] / stats['nodes'], 2)} |
| Componentes esperados | 1 (hub garante conectividade) |

O Graph View do Obsidian mostra mais links aparentes do que arestas existem, porque
wikilinks em tabelas contam duas vezes. Use `data/stats.json` como fonte de verdade.

## Nós com maior grau (hubs do grafo)

| nó | tipo | grau |
|---|---|---|
""" + "\n".join(
        f"| {L(i)} | {KIND_PT.get(nodes[i]['kind'], '')} | {d} |"
        for i, d in degree.most_common(30)) + f"""

Ver também {L('Ranking de nós por grau')} (lista completa) e {L('Estatísticas do dataset')}.
""")
    theory("Roadmap — visualização three.js", f"""---
tipo: roadmap
tags: [roadmap, threejs]
---
# Roadmap — visualização three.js

O payload já está pronto: **`data/graph_core.json`**
(`{stats['nodes']}` nós, `{stats['edges']}` arestas, cada nó com `x/y/z` pré-calculados).

## Contrato do payload

| campo | significado |
|---|---|
| `x` | `lon` em radianos × 5.2 (equiretangular) |
| `y` | `(camada − 4) × 1.15` — o eixo **hierárquico** |
| `z` | `−lat` em radianos × 5.2 |
| nós sem geo | distribuídos em anéis por categoria (infra sem endereço) |
| `kind`, `layer`, `country`, `city`, `asn`, `ptr`, `resolver` | atributos para cor/tooltip/filtro |

## Etapas

1. **Cena** — `three` + `OrbitControls`, fundo `#1a1a1f`, bloom leve nos nós `resolver`.
2. **Nós** — `Points`/`InstancedMesh` por categoria (7 cores, ver .obsidian/graph.json),
   escala por grau, halo para hubs.
3. **Arestas** — `LineSegments` único com cor por tipo; opacidade baixa, destaque no hover.
4. **Camadas** — planos/grades translúcidos com rótulo (`camada 5 — endereços`).
5. **Terra** — geografia real: mapa equiretangular como textura em plano em `y = 0`,
   os nós geo (camadas 5–8) ancorando nele.
6. **Interação** — raycast → painel lateral com o mesmo conteúdo da nota Obsidian;
   clique → deep link `obsidian://open?vault=grafo&file=<nota>`.
7. **Tipografia e diagramação** — ver {L('Direção visual e tipografia')}.

## Mesma fonte, duas saídas

```
scripts/01_collect_dns.py ─► data/raw/dns_records.json ─┐
scripts/02_geolocate.py   ─► data/raw/geo.json ─────────┼─► 03_build_graph.py ─► data/*.json|csv|graphml
                                                        └─► 04_build_vault.py ─► grafo/  (Obsidian)
                                                                                  └─► web/ (three.js, fase 2)
```
""")
    theory("Direção visual e tipografia", """---
tipo: design
tags: [design, roadmap]
---
# Direção visual e tipografia

Direção (fase 2, `web/`): *dark technical*, herdando a linguagem que o usuário já usa —
fundo `#1a1a1f`, acento ciano `#00b4d8`, painéis discretos, tipografia mono para dados e
uma grotesca de alto impacto para títulos. **Nada de estética "AI design"/ShadCN.**

| elemento | escolha |
|---|---|
| fundo | `#1a1a1f` / `#111114` |
| acento | `#00b4d8` (ciano), `#ff4d6d` (alerta), `#ffd166` (destaque) |
| display | Inter Tight / Space Grotesk, tracking negativo, 96–160 px |
| dados | JetBrains Mono / IBM Plex Mono, 12–14 px, tabular |
| grade | 12 colunas, gutter 24 px, margem 8 vw |
| movimento | entrada em camadas (camada 1 → 8), 600–900 ms, ease-out cúbico |

Regra de ouro: **a tipografia carrega a hierarquia, o grafo carrega a informação.**
Nenhum elemento decorativo compete com os nós.
""")
    theory("Coleta, proveniência e reprodutibilidade", """---
tipo: metodologia
tags: [metodologia, dados]
---
# Coleta, proveniência e reprodutibilidade

## Fontes (todas públicas, sem chave de API)

| fonte | uso | endpoint |
|---|---|---|
| DNS-over-HTTPS Cloudflare | NS / A / AAAA (primário) | `https://cloudflare-dns.com/dns-query` |
| DNS-over-HTTPS Google | mesma consulta (fallback) | `https://dns.google/resolve` |
| DNS reverso via resolvedor do sistema | PTR (`in-addr.arpa` / `ip6.arpa`) | `socket.gethostbyaddr` |
| ip-api.com `/batch` | geo, ASN, ISP, flags | `http://ip-api.com/batch` (100 IPs/req, 15 req/min) |

> [!note] Por que o PTR não vem da ip-api
> O endpoint `/batch` da ip-api devolve vazio no campo `reverse` (só a consulta
> individual, em plano gratuito limitado). PTR é dado de DNS: perguntamos direto a
> `in-addr.arpa` / `ip6.arpa`, o que é mais autoritativo de qualquer forma.

## Pipeline

```bash
cd Projetos/obsidian
python scripts/01_collect_dns.py     # consultas DNS reais  -> data/raw/dns_records.json
python scripts/02_geolocate.py       # geo/ASN via ip-api   -> data/raw/geo.json
python scripts/02b_collect_ptr.py    # DNS reverso (PTR)    -> data/raw/ptr.json
python scripts/03_build_graph.py     # normaliza            -> data/nodes.json, edges.json,
                                     #                        hosts.csv, graph.graphml, graph_core.json
python scripts/04_build_vault.py     # escreve o vault      -> vault/
python scripts/05_write_readme.py    # README com os números
python scripts/06_validate_vault.py  # auditoria de links e frontmatter
```

`scripts/seeds.py` é a **única** entrada editorial: 13 raízes, ~70 TLDs, ~60 serviços,
~30 resolvedores públicos. Mudar as sementes e rodar de novo regenera tudo — nada é
escrito à mão dentro do vault.

## Limites declarados

- Geolocalização de IP é estimativa comercial, não cartório. Precisão típica: cidade/região.
- Anycast: ver [[Anycast e geolocalização de IP]].
- IPv6 é geo-localizado com menos precisão.
- Uma coleta por IP: o PoP pode mudar com a rota.
""")
    theory("Como abrir este vault no Obsidian", """---
tipo: guia
tags: [guia, obsidian]
---
# Como abrir este vault no Obsidian

1. Obsidian → **Open folder as vault** → a pasta `grafo/` deste projeto
   (ex.: `<pasta-do-clone>/grafo`; no Windows, `…\\onde-a-internet-mora\\grafo`)
2. Abra a nota [[Índice do grafo]] (pasta `000 HUB`).
3. Graph View (`Ctrl+G`): as cores já vêm configuradas em `.obsidian/graph.json`.

## Filtros prontos (cole na busca do Graph View)

| filtro | efeito |
|---|---|
| `tag:#camada/5` | só endereços IP |
| `tag:#camada/6` | rede (ASN, PoPs) |
| `tag:#geo/pais` | países |
| `-tag:#no/ip -tag:#geo/cidade` | só infraestrutura de nomes |
| `path:"400 Redes"` | apenas ASNs |
| `tag:#geo/br` | tudo geolocalizado no Brasil |

## Ajustes úteis

- Graph View → *Forces*: **Link distance 180**, **Repel 12** — separa os clusters de
  cidade dos nameservers.
- *Filters* → desmarque `Attachments` e `Existing files only` se quiser ver o grafo puro.
- Arquivos muito conectados (`data`, `README`) ficam de fora do vault de propósito.
""")
    theory("Dicionário de tags", f"""---
tipo: guia
tags: [guia, tags]
---
# Dicionário de tags

| tag | aplicada a |
|---|---|
| `#no/root` `#no/tld` `#no/service` `#no/ns` `#no/ip` `#no/asn` `#no/city` `#no/country` `#no/continent` | tipo do nó |
| `#camada/0` … `#camada/8` | camada hierárquica |
| `#geo/<cc>` | país do dado geográfico (ex.: `#geo/br`, `#geo/us`) |
| `#geo/pais` `#geo/cidade` `#geo/continente` | nível geográfico |
| `#rede/asn` | sistemas autônomos |
| `#teoria/*` `#metodologia` `#roadmap` `#design` `#guia` | notas de conteúdo |

Ativos agora: `{stats['countries']}` tags `#geo/*` de país, `{stats['cities']}` cidades,
`{stats['asns']}` ASNs.
""")

    # ---- MOCs ----------------------------------------------------------
    def hub(filename, title, body, tags="[moc]"):
        nonlocal written
        p = os.path.join(VAULT, "000 HUB", filename + ".md")
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(f"---\ntipo: hub\ntags: {tags}\n---\n# {title}\n\n{body}\n")
        written += 1

    hubs = [nid for nid, n in nodes.items() if n["kind"] == "root"]
    tlds = sorted([nid for nid, n in nodes.items() if n["kind"] == "tld"],
                  key=lambda x: -degree.get(x, 0))
    svcs = sorted([nid for nid, n in nodes.items() if n["kind"] == "service"],
                  key=lambda x: -degree.get(x, 0))
    asns = sorted([nid for nid, n in nodes.items() if n["kind"] == "asn"],
                  key=lambda x: -degree.get(x, 0))
    cties = sorted([nid for nid, n in nodes.items() if n["kind"] == "city"],
                   key=lambda x: -degree.get(x, 0))
    ctrys = sorted([nid for nid, n in nodes.items() if n["kind"] == "country"],
                   key=lambda x: -degree.get(x, 0))
    conts = sorted([nid for nid, n in nodes.items() if n["kind"] == "continent"])
    resolvers = sorted([nid for nid, n in nodes.items() if n["kind"] == "resolver_org"])

    hub("Índice do grafo", "Índice do grafo — DNS × Geografia", f"""
> [!abstract] O que é este vault
> Armazenamento experimental de nós em grafo, aplicado a infraestrutura real de internet:
> **{stats['ips_total']} endereços IP**, **{stats['nodes']} nós**, **{stats['edges']} arestas**,
> coletados ao vivo por DNS-over-HTTPS e geolocalizados por ASN/PoP.

| porta de entrada | conteúdo |
|---|---|
| {L('MOC Infraestrutura')} | raízes, TLDs, serviços, nameservers, resolvedores |
| {L('MOC Geografia')} | continentes → países → cidades → endereços |
| {L('MOC Redes (ASN)')} | sistemas autônomos e onde operam |
| {L('Estatísticas do dataset')} | números, rankings, distribuições |
| {L('Ranking de nós por grau')} | hubs do grafo |
| {L('Armazenamento de nós em grafos')} | a teoria por trás do armazenamento |
| {L('Como abrir este vault no Obsidian')} | instalação, filtros, cores |
| {L('Roadmap — visualização three.js')} | próxima fase (web, awwwards-grade) |
| {L('Coleta, proveniência e reprodutibilidade')} | como tudo foi gerado |
| {L('Datasets e arquivos')} | arquivos canônicos (csv, graphml, json) |

Nós sem nenhuma aresta DNS direta (nomes reversos isolados, redes sem IP associado)
ficam pendurados em {L('Zona raiz — servidores homing')} — é o que impede ilhas soltas
no Graph View.
""")

    hub("MOC Infraestrutura", "MOC — Infraestrutura de nomes", f"""
## Servidores raiz ({len(hubs)})

{chr(10).join('- ' + L(h) for h in hubs)}

## Zonas de topo ({len(tlds)})

{chr(10).join('- ' + L(t) for t in tlds)}

## Serviços ({len(svcs)})

{chr(10).join('- ' + L(s) for s in svcs)}

## Resolvedores públicos ({len(resolvers)})

{chr(10).join('- ' + L(r) for r in resolvers)}

## Nameservers

{sum(1 for n in nodes.values() if n['kind'] in ('ns', 'ptr', 'resolver_host'))} notas na pasta
`200 Infraestrutura/240 Nameservers` — acesse pelo Graph View com `path:"240 Nameservers"`.
""")

    hub("MOC Geografia", "MOC — Geografia", f"""
## Continentes

{chr(10).join('- ' + L(c) for c in conts)}

## Países com mais endereços ({len(ctrys)} no total)

| país | grau |
|---|---|
{chr(10).join(f"| {L(c)} | {degree.get(c, 0)} |" for c in ctrys[:25])}

## Cidades / PoPs ({len(cties)} no total)

| cidade | endereços |
|---|---|
{chr(10).join(f"| {L(c)} | {degree.get(c, 0)} |" for c in cties[:40])}
""")

    hub("MOC Redes (ASN)", "MOC — Redes autônomas", f"""
{len(asns)} sistemas autônomos presentes no dataset ({stats['asns']} únicos).

| ASN | endereços |
|---|---|
{chr(10).join(f"| {L(a)} | {degree.get(a, 0)} |" for a in asns[:60])}
""")

    def keystat_rows(key, top=20):
        return "\n".join(f"| {k} | {v} |" for k, v in stats[key][:top])

    hub("Estatísticas do dataset", "Estatísticas do dataset", f"""
> Gerado em {stats['generated_at']} — fonte de verdade: `data/stats.json`

| métrica | valor |
|---|---|
| Nós | {stats['nodes']} |
| Arestas | {stats['edges']} |
| Endereços IP | {stats['ips_total']} (IPv4 {stats['ips_v4']} / IPv6 {stats['ips_v6']}) |
| Geolocalizados | {stats['ips_geolocated']} |
| Em datacenter/hosting | {stats['ips_hosting']} |
| Países | {stats['countries']} |
| Cidades / PoPs | {stats['cities']} |
| ASNs | {stats['asns']} |
| Consultas DNS | {stats['dns_queries'].get('queries', '—')} |
| Tempo de coleta DNS | {stats['dns_queries'].get('seconds', '—')} s |

## Top países

| país | endereços |
|---|---|
{keystat_rows('top_countries')}

## Top cidades / PoPs

| cidade | endereços |
|---|---|
{keystat_rows('top_cities')}

## Top redes (ASN)

| ASN | endereços |
|---|---|
{keystat_rows('top_asns')}

## Nós por tipo

| tipo | nós |
|---|---|
{chr(10).join(f"| `{k}` | {v} |" for k, v in stats['nodes_by_kind'].items())}

## Nós por camada

| camada | nós |
|---|---|
{chr(10).join(f"| {k} | {v} |" for k, v in stats['nodes_by_layer'].items())}
""")

    hub("Ranking de nós por grau", "Ranking de nós por grau", f"""
Grau = número de arestas incidentes (entrada + saída) no grafo normalizado.

| # | nó | tipo | camada | grau |
|---|---|---|---|---|
""" + "\n".join(
        f"| {i+1} | {L(nid)} | {nodes[nid]['kind']} | {nodes[nid].get('layer')} | {d} |"
        for i, (nid, d) in enumerate(degree.most_common(120))) + "\n")

    # ============================ 6. datasets ============================
    import shutil
    ddir = os.path.join(VAULT, "600 Dados")
    os.makedirs(ddir, exist_ok=True)
    src_csv = os.path.join(DATA, "hosts.csv")
    if os.path.exists(src_csv):
        shutil.copy2(src_csv, os.path.join(ddir, "hosts.csv"))
    top = "\n".join(
        f"| {L(r['ip'], r['ip'])} | {r['ptr'] or '—'} | {r['asn_name'] or '—'} | "
        f"{r['cidade'] or '—'} | {r['pais'] or '—'} | {r['lat']},{r['lon']} |"
        for r in [dict(zip(["ip", "familia", "ptr", "asn", "asn_name", "isp", "org",
                            "cidade", "regiao", "pais", "pais_cc", "continente", "lat",
                            "lon", "timezone", "datacenter", "resolvedor_publico"], line))
                  for line in (open(src_csv, encoding="utf-8").read().splitlines()[1:])][:60]
        if r["ip"] in name)
    with open(os.path.join(ddir, "Datasets e arquivos.md"), "w", encoding="utf-8") as f:
        f.write(f"""---
tipo: dado
tags: [dados, dataset]
---
# Datasets e arquivos

Cópia de leitura dentro do vault: [[hosts.csv]] ({stats['ips_total']} linhas, separador `,`).

Os arquivos canônicos ficam **fora** do vault, em `Projetos/obsidian/data/`:

| arquivo | conteúdo |
|---|---|
| `data/raw/dns_records.json` | respostas DNS brutas (NS/A/AAAA) por nome |
| `data/raw/geo.json` | resposta crua do ip-api por endereço |
| `data/nodes.json` | {stats['nodes']} nós tipados |
| `data/edges.json` | {stats['edges']} arestas tipadas |
| `data/stats.json` | todas as métricas |
| `data/hosts.csv` | tabela plana de endereços + geo + ASN |
| `data/graph.graphml` | formato aberto para Gephi / yEd / Cytoscape |
| `data/graph_core.json` | payload com `x/y/z` para o three.js |

## Amostra (60 primeiros endereços)

| endereço | PTR | ASN | cidade | país | lat,lon |
|---|---|---|---|---|---|
{top}

Regenerar: ver [[Coleta, proveniência e reprodutibilidade]].
""")
    written += 1

    # ============================ 7. mapa de notas (para o web/three.js) ==
    json.dump({
        "generated_at": stats["generated_at"],
        "vault_name": os.path.basename(VAULT),
        "note_deep_link": "obsidian://open?vault=" + os.path.basename(VAULT) + "&file=",
        "countries_pt": COUNTRY_PT,
        "notes": {nid: {"note": name[nid], "kind": nodes[nid]["kind"],
                        "folder": FOLDER.get(nodes[nid]["kind"], "600 Dados"),
                        "grau": degree.get(nid, 0)}
                  for nid in nodes},
    }, open(os.path.join(DATA, "notes_map.json"), "w", encoding="utf-8"),
        ensure_ascii=False, separators=(",", ":"))

    # ============================ 8. .obsidian ===========================
    obs = os.path.join(VAULT, ".obsidian")
    os.makedirs(obs, exist_ok=True)
    colors = {
        "000 HUB": "FFFFFF", "200 Infraestrutura/210": "FF4D6D",
        "200 Infraestrutura/220": "FF8C42", "200 Infraestrutura/230": "FFD166",
        "200 Infraestrutura/240": "2EC4B6", "200 Infraestrutura/250": "06D6A0",
        "300 Hosts": "00B4D8", "400 Redes": "B388FF",
        "500 Geografia/510": "FF69B4", "500 Geografia/520": "E8A2FF",
        "500 Geografia/530": "C9ADA7",
    }
    json.dump({
        "collapse-filter": False, "search": "", "showTags": False,
        "showAttachments": False, "hideUnresolved": False, "showOrphans": True,
        "collapse-color-groups": False,
        "colorGroups": [{"query": f'path:"{p}"',
                         "color": {"a": 1, "rgb": int(c, 16)}} for p, c in colors.items()],
        "collapse-display": False, "showArrow": False, "textFadeMultiplier": -1.2,
        "nodeSizeMultiplier": 1.4, "lineSizeMultiplier": 0.6,
        "collapse-forces": False, "centerStrength": 0.35, "repelStrength": 12,
        "linkStrength": 0.9, "linkDistance": 180, "scale": 0.35, "close": False,
    }, open(os.path.join(obs, "graph.json"), "w", encoding="utf-8"), indent=2)
    json.dump({"attachmentFolderPath": "600 Dados/anexos", "alwaysUpdateLinks": True,
               "newFileLocation": "folder", "newFileFolderPath": "600 Dados",
               "showLineNumber": True, "readableLineLength": False},
              open(os.path.join(obs, "app.json"), "w", encoding="utf-8"), indent=2)
    json.dump({"accentColor": "#00b4d8", "theme": "obsidian", "baseFontSize": 16,
               "cssTheme": ""},
              open(os.path.join(obs, "appearance.json"), "w", encoding="utf-8"), indent=2)
    os.makedirs(os.path.join(VAULT, "600 Dados", "anexos"), exist_ok=True)

    print(f"OK  {written} notas escritas em grafo/")
    print("    notas por pasta:")
    cnt = Counter(os.path.dirname(p).replace(VAULT + os.sep, "")
                  for p in paths.values())
    for k, v in sorted(cnt.items()):
        print(f"      {k:<45} {v}")
    if warn:
        print(f"    avisos ({len(warn)}):")
        for w in warn[:10]:
            print("      " + w)


if __name__ == "__main__":
    main()
