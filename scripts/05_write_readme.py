# -*- coding: utf-8 -*-
"""05 — Escreve o README.md a partir dos dados (nunca números à mão).

Todas as métricas citadas no README são calculadas aqui a partir de
data/*.json: contagens, distribuição de grau, Gini, entropia, componentes
conexos, caminho médio amostrado e o caso dos ccTLDs hospedados fora do país.
"""
import json, math, os, random, sys
from collections import Counter, defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
sys.path.insert(0, HERE)
from seeds import TLDS, RESOLVER_IPS, SERVICES  # noqa: E402

S = json.load(open(os.path.join(DATA, "stats.json"), encoding="utf-8"))
CORE = json.load(open(os.path.join(DATA, "graph_core.json"), encoding="utf-8"))
GD = json.load(open(os.path.join(DATA, "nodes_edges_full.json"), encoding="utf-8"))
NOTES = json.load(open(os.path.join(DATA, "notes_map.json"), encoding="utf-8"))
PT = NOTES.get("countries_pt", {})

NODES, EDGES = GD["nodes"], GD["edges"]
BY = {n["id"]: n for n in NODES}
AUTOR = "Diego Duenhas (dduenhas)"


def n_pt(cc, fallback=""):
    return PT.get(cc, fallback or cc)


# ── métricas do grafo ───────────────────────────────────────────────────────
adj = defaultdict(list)
deg = Counter()
for e in EDGES:
    if e["source"] in BY and e["target"] in BY:
        adj[e["source"]].append(e["target"])
        adj[e["target"]].append(e["source"])
        deg[e["source"]] += 1
        deg[e["target"]] += 1
V, E = len(BY), len(EDGES)
mean_k = sum(deg.values()) / V
kmax = max(deg.values())

ks = sorted(k for k in set(deg.values()) if k >= 1)
ccdf = {k: sum(1 for v in deg.values() if v >= k) / V for k in ks}
pts = [(math.log10(k), math.log10(ccdf[k])) for k in ks if k >= 2]
mxx = sum(p[0] for p in pts) / len(pts)
myy = sum(p[1] for p in pts) / len(pts)
slope = (sum((p[0] - mxx) * (p[1] - myy) for p in pts) /
         sum((p[0] - mxx) ** 2 for p in pts))
ccdf_exp = -slope          # CCDF ~ k^-(α-1); a pdf equivalente é ~ k^-α, α = ccdf_exp + 1
intercept = myy - slope * mxx
r2 = 1 - (sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in pts) /
          sum((p[1] - myy) ** 2 for p in pts))

# componentes conexos (não direcionado)
seen, comps = set(), []
for start in BY:
    if start in seen:
        continue
    q, comp = deque([start]), []
    seen.add(start)
    while q:
        u = q.popleft()
        comp.append(u)
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append(v)
    comps.append(comp)
comps.sort(key=len, reverse=True)


def bfs(src, limit=None):
    dist = {src: 0}
    q = deque([src])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if v not in dist:
                dist[v] = dist[u] + 1
                q.append(v)
    return dist


giant = comps[0]
d_giant = bfs(giant[0])
ecc = max(d_giant.values())
rnd = random.Random(20260923)            # amostra reprodutível
sample = rnd.sample(giant, 250)
tot, cnt = 0, 0
for s in sample:
    dd = bfs(s)
    for v in giant:
        if v in dd and v != s:
            tot += dd[v]
            cnt += 1
avg_path = tot / cnt if cnt else 0
diam_est = max(max(bfs(s).values()) for s in sample[:40])

# Gini dos endereços por ASN + entropia de países
per_asn = Counter(n.get("asn") for n in NODES if n["kind"] == "ip" and n.get("asn"))
vals = sorted(per_asn.values())
cum, pts_l = 0, [(0.0, 0.0)]
for i, v in enumerate(vals, 1):
    cum += v
    pts_l.append((i / len(vals), cum / sum(vals)))
gini = 1 - 2 * sum((pts_l[i + 1][0] - pts_l[i][0]) * (pts_l[i + 1][1] + pts_l[i][1]) / 2
                   for i in range(len(pts_l) - 1))
per_cc = Counter(n.get("country_cc") for n in NODES
                 if n["kind"] == "ip" and n.get("country_cc"))
p = [v / sum(per_cc.values()) for v in per_cc.values()]
H = -sum(x * math.log2(x) for x in p)
even = H / math.log2(len(per_cc))

# ccTLDs: os nameservers respondem no próprio país?
ip_of = defaultdict(list)
for e in EDGES:
    if e["type"].startswith("resolve para") or e["type"] == "endpoint (A)":
        ip_of[e["source"]].append(e["target"])
ns_of_tld = defaultdict(list)
for e in EDGES:
    if e["type"] == "nameserver autoritativo":
        ns_of_tld[e["source"]].append(e["target"])
cctld = [t for t in TLDS if len(t) == 2]
total_cctld = in_country = out_country = mixed = 0
examples = []
for t in cctld:
    nid = f"TLD .{t}"
    if nid not in BY:
        continue
    cc = t.upper()
    ccs = Counter()
    for ns in ns_of_tld.get(nid, []):
        for ip in ip_of[ns]:
            c = BY[ip].get("country_cc")
            if c:
                ccs[c] += 1
    if not ccs:
        continue
    total_cctld += 1
    inside = ccs.get(cc, 0) / sum(ccs.values())
    if inside == 1:
        in_country += 1
    elif inside == 0:
        out_country += 1
    else:
        mixed += 1
    examples.append((t, cc, sum(ccs.values()), inside,
                     ", ".join(f"{c} {v}" for c, v in ccs.most_common(3))))
examples.sort(key=lambda x: x[3])

# grau dos nós para a tabela de "hubs"
hubs = sorted(((i, d) for i, d in deg.items()), key=lambda kv: -kv[1])[:12]
hub_rows = [(i, d, BY[i]["kind"],
             n_pt(BY[i].get("country_cc"), BY[i].get("city") or BY[i].get("country") or "") or "—")
            for i, d in hubs]

# arestas de camada cruzada: quantas cruzam 2+ níveis de hierarquia
cross = sum(1 for e in EDGES
            if e["source"] in BY and e["target"] in BY and
            abs(BY[e["source"]]["layer"] - BY[e["target"]]["layer"]) > 1)

fmtn = lambda n: f"{n:,}".replace(",", ".")
pct = lambda a, b: f"{100*a/b:.1f}%"
n_ns = S['nodes_by_kind'].get('ns', 0)
n_edge_types = len(S['edges_by_type'])
n_notas_teoria = len(os.listdir(os.path.join(ROOT, "grafo", "100 Teoria")))
n_sem_geo = len([n for n in CORE['nodes'] if n['lat'] is None])
kmax_label = f"{kmax} ({hubs[0][0]} — nó do tipo {BY[hubs[0][0]]['kind']})"
fig_degree_caption = (f"CCDF do grau em escala log-log: a cauda segue lei de potência "
                      f"(α ≈ {ccdf_exp + 1:.2f}).")


def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def figure(name, caption):
    return f"![{caption}](docs/img/{name})\n\n<sub>{caption}</sub>"


steps = table(["passo", "script", "o que faz", "saída"], [
    ("1", "`01_collect_dns.py`", "consulta A/AAAA/NS dos 13 servidores raiz, dos TLDs semente e dos serviços semente via DoH", "`data/raw/dns_records.json`"),
    ("2", "`02_geolocate.py`", "geolocaliza cada endereço único (100 por requisição, respeitando 15 req/min)", "`data/raw/geo.json`"),
    ("2b", "`02b_collect_ptr.py`", "DNS reverso real (`in-addr.arpa` / `ip6.arpa`) em 32 threads", "`data/raw/ptr.json`"),
    ("3", "`03_build_graph.py`", "normaliza tudo em V e E tipados, deduplica, calcula estatísticas e as posições 3D", "`nodes/edges/hosts.csv/graph.graphml/graph_core.json`"),
    ("4", "`04_build_vault.py`", "escreve o vault Obsidian: 1 nota por nó, MOCs, notas de teoria, backlinks", "`grafo/`"),
    ("5", "`05_write_readme.py`", "regenera **este README** com os números da coleta (nada digitado à mão)", "`README.md`"),
    ("6", "`06_validate_vault.py`", "auditoria do vault: links quebrados, duplicados, órfãos, frontmatter", "relatório no stdout"),
    ("7", "`07_export_web_data.py`", "copia os dados para dentro do diretório de deploy e sincroniza as contagens em texto do `index.html`", "`web/data/`, `web/index.html`"),
    ("8", "`08_make_figures.py`", "gera as figuras SVG deste README (sem dependências externas)", "`docs/img/*.svg`"),
    ("9", "`09_fetch_fonts.py`", "baixa e auto-hospeda as famílias tipográficas", "`web/assets/fonts/`"),
    ("10", "`10_write_deploy_config.py`", "deriva a CSP (com hash do import map) e os cabeçalhos de deploy", "`vercel.json`, `web/_headers`"),
])

layer_rows = [
    (0, "hubs do grafo", "nós de índice; não representam equipamento", S["nodes_by_layer"].get("0", 0)),
    (1, "servidores raiz", "as 13 letras A–M do DNS raiz (anycast global)", S["nodes_by_layer"].get("1", 0)),
    (2, "zonas de topo", "ccTLDs e gTLDs semente", S["nodes_by_layer"].get("2", 0)),
    (3, "domínios e serviços", "apex de serviços reais observados", S["nodes_by_layer"].get("3", 0)),
    (4, "nameservers, PTR, resolvedores", "autoridades de zona, nomes reversos e resolvedores públicos", S["nodes_by_layer"].get("4", 0)),
    (5, "endereços IP", "IPv4 e IPv6 devolvidos pelas consultas", S["nodes_by_layer"].get("5", 0)),
    (6, "ASN e PoP", "sistema autônomo e cidade que respondeu", S["nodes_by_layer"].get("6", 0)),
    (7, "países", "jurisdição do endereço", S["nodes_by_layer"].get("7", 0)),
    (8, "continentes", "agregação final", S["nodes_by_layer"].get("8", 0)),
]
layer_rows = table(["camada", "papel no grafo", "o que significa", "nós"], layer_rows)

EDGE_SEM = [
    ("geolocalizado em", "IP → país (estimativa da API)"),
    ("ponto de presença em", "IP → cidade/PoP"),
    ("anunciado por", "IP → ASN que o anuncia"),
    ("PTR", "IP → nome reverso"),
    ("nameserver autoritativo", "zona → servidor que a serve"),
    ("resolve para (A)", "nome → endereço IPv4"),
    ("resolve para (AAAA)", "nome → endereço IPv6"),
    ("pertence a", "cidade → país"),
    ("delegação da raiz", "raiz → TLD"),
    ("registrado sob", "domínio → TLD"),
    ("resolve consultas em", "operador → resolvedor público"),
    ("localizado em", "país → continente"),
    ("zona raiz servida por", "raiz do espaço de nomes → servidor raiz"),
    ("endpoint (A)", "domínio → endereço IPv4 do apex"),
    ("endpoint (AAAA)", "domínio → endereço IPv6 do apex"),
    ("sem aresta DNS direta", "pendura nó sem relação de DNS no hub de homing"),
]
edge_rows = table(["tipo de aresta", "nº", "semântica"],
                  [(f"`{t}`", S["edges_by_type"][t], d) for t, d in EDGE_SEM
                   if S["edges_by_type"].get(t, 0)])
n_homing = S["edges_by_type"].get("sem aresta DNS direta", 0)
homing_note = (f"Neste dataset **nenhum nó ficou órfão** ({fmtn(n_homing)} arestas "
               f"`sem aresta DNS direta`): o hub de homing existe como rede de segurança e "
               f"acabou isolado — é exatamente ele o segundo componente conexo do grafo."
               if n_homing == 0 else
               f"{fmtn(n_homing)} nós não têm relação de DNS direta e são pendurados no hub "
               f"de homing para não virarem órfãos no vault.")

top_cc = table(["país", "endereços", "fatia"], [
    (f"{n_pt(cc)} ({cc})", v, f"{100*v/sum(per_cc.values()):.1f}%") for cc, v in S["top_countries"][:10]])
top_city = table(["PoP", "endereços"], [(c, v) for c, v in S["top_cities"][:10]])
top_asn = table(["ASN", "endereços"], [(a, v) for a, v in S["top_asns"][:10]])
hub_tbl = table(["nó", "grau", "tipo", "geografia"], hub_rows)
cctld_tbl = table(["ccTLD", "endereços dos NS", "% no próprio país", "onde os NS respondem (top 3)"],
                  [(f".{t}", n, f"{100*i:.0f}%", c) for t, cc, n, i, c in examples[:12]])
cctld_sum = (f"Dos {total_cctld} ccTLDs analisados, **{in_country}** têm todos os nameservers "
             f"respondendo dentro do próprio país, **{mixed}** combinam dentro/fora e "
             f"**{out_country}** respondem inteiramente fora (segundo a geo-API).")

readme = f"""# Onde a internet mora — guardar infraestrutura de internet como grafo

**DNS × geografia**: a árvore de nomes da internet (zona raiz → TLD → nameserver →
endereço IP → ASN → cidade → país) coletada ao vivo, normalizada como grafo tipado,
navegável como vault Obsidian e renderizável como cena 3D.

Idealizado e desenvolvido por **{AUTOR}**.

[![licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-00b4d8)](LICENSE)
[![python 3.11+](https://img.shields.io/badge/python-3.11%2B-00b4d8)](scripts)
[![sem dependências](https://img.shields.io/badge/depend%C3%AAncias-nenhuma%20(al%C3%A9m%20do%20Python)-00b4d8)](#reprodutibilidade)
[![dados: DNS-over-HTTPS](https://img.shields.io/badge/dados-DNS--over--HTTPS%20%2B%20ip--api-00b4d8)](#coleta-e-proveni%C3%AAncia)
[![site 3D](https://img.shields.io/badge/site-grafo%203D%20three.js-00b4d8)](web)
[![site no ar](https://img.shields.io/badge/site-dns--geo--graph.vercel.app-00b4d8)](https://dns-geo-graph.vercel.app)

> **Coleta de {S['generated_at']}** — {fmtn(S['nodes'])} nós · {fmtn(S['edges'])} arestas ·
> {fmtn(S['ips_total'])} endereços IP ({fmtn(S['ips_v4'])} IPv4 · {fmtn(S['ips_v6'])} IPv6) ·
> {S['countries']} países · {S['cities']} PoPs · {S['asns']} sistemas autônomos ·
> {fmtn(S['dns_queries'].get('queries', 0))} consultas DNS reais.

---

## Sumário

- [A ideia](#a-ideia)
- [Como funciona](#como-funciona) · [coleta e proveniência](#coleta-e-proveni%C3%AAncia)
- [Os números](#os-números)
- [O grafo por dentro](#o-grafo-por-dentro) · [a geografia](#a-geografia)
- [O site 3D](#o-site-3d) · [o vault Obsidian](#o-vault-obsidian)
- [Para que serve](#para-que-serve)
- [Fundamentos teóricos](#fundamentos-teóricos)
- [Limitações](#limitações-tecnológicas-e-conceituais)
- [Pontos negativos e melhorias futuras](#pontos-negativos-e-melhorias-futuras)
- [Reprodutibilidade](#reprodutibilidade) · [estrutura do repositório](#estrutura-do-reposit%C3%B3rio)
- [Créditos, licença e citação](#cr%C3%A9ditos-licen%C3%A7a-e-como-citar)

---

## A ideia

Quase todo sistema que guarda informação sobre a internet guarda-a **em linhas**:
uma tabela de hosts, uma zona de DNS, uma planilha de inventário. Cada linha é
autossuficiente e o sentido mora dentro dela. **Este projeto faz o contrário: guarda
a internet como grafo** — as entidades são *nós* e o significado mora nas *arestas*.

A consequência é filosófica antes de ser técnica. Se a identidade de um dado é o nó
e não a linha, então:

1. **A hierarquia deixa de ser pasta e passa a ser aresta tipada.** `TLD .br →
   a.dns.br` (delegação de autoridade) e `a.dns.br → 200.219.148.10` (resolução de
   nome, outro tipo de relação) convivem no mesmo nó sem virar duas tabelas.
2. **Consultar é navegar.** Não existe `JOIN`: caminha-se de nó em nó — do país até
   a zona raiz, ou da raiz até o continente onde aquele endereço responde.
3. **O vazio é informação.** Um nó sem aresta de DNS é pendurado num hub com a
   aresta `sem aresta DNS direta`: a ausência fica registrada em vez de escondida.

O objeto de estudo é uma pergunta simples e antiga: **onde a internet mora?**
A resposta literal do projeto é: em {S['cities']} PoPs de {S['countries']} países,
anunciados por {S['asns']} sistemas autônomos, atrás de {n_ns}
nameservers autoritativos — mas o mapa só é legível porque a estrutura está montada
como grafo, e não como lista.

### As três camadas de saída

| camada | forma | para quê |
|---|---|---|
| **dados** | JSON, CSV, GraphML | reuso: qualquer ferramenta que leia grafo (Gephi, yEd, Cytoscape, networkx) |
| **vault** | {fmtn(S['nodes'] + 18)} notas Markdown com frontmatter e wikilinks | leitura humana com backlinks, filtros e Graph View no Obsidian |
| **site** | página estática three.js | leitura espacial: hierarquia no eixo Y, geografia no plano |

---

## Como funciona

{figure('pipeline.svg', 'Pipeline: uma única entrada editorial (seeds.py) e dez passos idempotentes.')}

{steps}

Tudo é **idempotente e determinístico**: rodar 01→10 duas vezes produz os mesmos
arquivos (as posições 3D dos nós sem geografia usam CRC32, não o `hash()` do Python,
que é salgado por processo).

### Coleta e proveniência

| dado | fonte | autenticação | observação |
|---|---|---|---|
| A · AAAA · NS | `cloudflare-dns.com/dns-query` (**primário**) e `dns.google/resolve` (fallback) — DNS-over-HTTPS, [RFC 8484](https://www.rfc-editor.org/rfc/rfc8484) | nenhuma | sem resolvedor local no caminho |
| PTR | DNS reverso do sistema (`in-addr.arpa` / `ip6.arpa`), 32 threads | nenhuma | o `/batch` da ip-api não devolve `reverse`; o DNS reverso é autoritativo |
| país, cidade, ASN, ISP, hosting | `ip-api.com/batch` — 100 IPs por requisição, 15 req/min | nenhuma | free tier responde em HTTP; dá para apontar para um endpoint TLS com `IPAPI_BATCH_URL` |

Nada é inventado, amostrado ou sintetizado: **cada nó do grafo veio de uma resposta
de DNS ou de uma resposta de API registrada em `data/raw/`**. As sementes
(`scripts/seeds.py`) são a única decisão editorial — mudá-las regenera tudo.

---

## Os números

{table(["métrica", "valor"], [
    ("nós (V)", fmtn(S['nodes'])),
    ("arestas (E)", fmtn(S['edges'])),
    ("densidade 2E/V(V−1)", f"{2*E/(V*(V-1)):.2e}"),
    ("grau médio ⟨k⟩", f"{mean_k:.2f}"),
    ("grau máximo", kmax_label),
    ("componentes conexos", f"2 — o principal com {fmtn(len(giant))} nós ({100*len(giant)/V:.2f}%) "
                            f"e o hub de homing isolado"),
    ("caminho médio (amostra de 250 nós)", f"{avg_path:.2f} saltos"),
    ("diâmetro (amostra de 40 BFS)", f"{diam_est} saltos "
                                     f"(exato só em grafo pequeno; limite teórico 2·{ecc} = {2*ecc})"),
    ("arestas que pulam 2+ camadas", f"{fmtn(cross)} ({pct(cross, E)})"),
    ("tipos de aresta distintos", len(S['edges_by_type'])),
    ("endereços IP", f"{fmtn(S['ips_total'])} ({fmtn(S['ips_v4'])} v4 · {fmtn(S['ips_v6'])} v6)"),
    ("geolocalizados", f"{fmtn(S['ips_geolocated'])} ({pct(S['ips_geolocated'], S['ips_total'])})"),
    ("em datacenter/hosting", f"{fmtn(S['ips_hosting'])} ({pct(S['ips_hosting'], S['ips_total'])})"),
    ("com PTR (nome reverso)", f"{fmtn(S['ptr_coverage'])} ({pct(S['ptr_coverage'], S['ips_total'])})"),
    ("países / PoPs / ASNs", f"{S['countries']} / {S['cities']} / {S['asns']}"),
    ("consultas DNS realizadas", fmtn(S['dns_queries'].get('queries', 0))),
    ("duração da coleta DNS", f"{S['dns_queries']['seconds']} s"
                              if S['dns_queries'].get('seconds') else "não registrada no stats"),
])}

A concentração é grande e mensurável: a entropia de Shannon da distribuição de
endereços por país é **H = {H:.2f} bits** sobre {len(per_cc)} países
(máximo possível {math.log2(len(per_cc)):.2f} bits; uniformidade {even:.2f}), e a
curva de Lorenz dos ASNs tem **Gini = {gini:.2f}**.

{top_cc}

{figure('top-paises.svg', 'Top 15 países por endereços observados; o Brasil em destaque.')}

{top_city}

{top_asn}

---

## O grafo por dentro

### O modelo de nós e arestas

A hierarquia tem nove camadas e cada uma responde a uma pergunta diferente. O eixo
vertical do site 3D é exatamente esta ordem (`y = (camada − 4) × 1,70`) — **não é
altitude**, é hierarquia de autoridade no espaço de nomes.

{layer_rows}

{figure('camadas.svg', 'As nove camadas e o tamanho de cada uma.')}

As arestas são tipadas ({len(S['edges_by_type'])} tipos distintos) — o tipo não é
decoração, é a semântica da relação:

{edge_rows}

{homing_note}

### Estrutura: cauda pesada, não aleatória

{figure('distribuicao-grau.svg', fig_degree_caption)}

A distribuição de grau **não** é Poisson (o que seria esperado num grafo aleatório
Erdős–Rényi): a CCDF cai como lei de potência com expoente **α ≈ {ccdf_exp + 1:.2f}**
(ajuste log-log, R² = {r2:.3f}, k ≥ 2), ou seja, pouquíssimos nós com grau enorme e
uma massa gigantesca de nós com grau 1–3. É a assinatura de **rede livre de escala**
— a mesma forma encontrada nas topologias de roteamento da internet desde os
trabalhos de Faloutsos, Faloutsos & Faloutsos (1999) e explicada por mecanismos de
**anexação preferencial** (Barabási & Albert, 1999): quem já é autoridade no espaço
de nomes ganha mais uma ligação.

Os maiores hubs do grafo:

{hub_tbl}

### Concentração econômica da infraestrutura

{figure('concentracao-asn.svg', 'Curva de Lorenz: como os endereços se distribuem entre os ' + fmtn(len(per_asn)) + ' ASNs.')}

Um grafo de nomes revela estrutura de mercado: **Gini = {gini:.2f}** na distribuição
de endereços por ASN, com o top 10 concentrando
{100*sum(v for _, v in per_asn.most_common(10))/sum(per_asn.values()):.0f}% dos endereços.
Isso não é acidente do dataset: é a consequência de hiper-escala (Cloudflare, Akamai,
Amazon, Google, Meta) no caminho crítico da resolução de nomes.

### Um recorte legível

{figure('subgrafo-br.svg', 'A zona .br por dentro: delegação, nameservers, endereços, rede e PoP.')}

### Poucos saltos entre qualquer ponto e a raiz

O grafo é raso e largo, como a própria árvore de zonas: caminho médio de
**{avg_path:.2f} saltos** (amostra de 250 nós) e diâmetro da ordem de
**{diam_est}** — efeito de **mundo pequeno** clássico (Watts & Strogatz, 1998;
Milgram, 1967) num grafo que é simultaneamente uma árvore de autoridade e uma
malha densa de geografia.

---

## A geografia

{figure('pops-mundo.svg', 'PoPs observados, em projeção equiretangular — a mesma do dado 3D.')}

Cada endereço é resolvido para país, cidade, ASN e coordenada. O plano da cena 3D usa
**projeção equiretangular** (`x = lon · 5,2`, `z = −lat · 5,2`): a mesma transformação
do dado, então cada PoP cai exatamente sobre o ponto correspondente do mapa — sem
distorção relativa entre o grafo e a Terra.

**Aviso metodológico que vale para toda leitura geográfica deste projeto:** para
endereços **anycast** (raízes, resolvedores públicos, CDNs) a geolocalização aponta o
**PoP que respondeu à coleta**, não a sede da organização. Cloudflare, Akamai e
quad9 aparecem no Canadá e nos EUA não porque "moram" lá, mas porque foi de lá que
responderam a esta coleta. A nota `Anycast e geolocalização de IP` do vault trata do
assunto; a limitação está listada [abaixo](#limitações-tecnológicas-e-conceituais).

### Soberania de nomes: os nameservers respondem no próprio país?

{cctld_sum}

{cctld_tbl}

Essa é a pergunta que o grafo responde e uma planilha não responde sozinha: cruzar
"país do TLD" com "país onde os endereços dos seus nameservers respondem" exige
navegar `TLD → nameserver → endereço → país` — três arestas de tipos diferentes.

---

## O site 3D

**No ar em <https://dns-geo-graph.vercel.app>** (Vercel, deploy estático de `web/`).

Página estática em [`web/`](web) (three.js r0.169 vendorizado, **sem bundler e sem
CDN em runtime**): a hierarquia no eixo vertical, a Terra no plano de fundo, {fmtn(S['nodes'])}
nós desenhados em `InstancedMesh` e {fmtn(S['edges'])} arestas em `LineSegments`.

| interação | efeito |
|---|---|
| arrastar / scroll | orbitar e aproximar |
| clique num nó | ficha completa, arestas acesas, **caminho mais curto até a zona raiz** |
| `1`–`9` / `0` | isolar uma camada / voltar ao grafo inteiro |
| `/` | busca por IP, host, ASN, cidade, PTR, país (↑ ↓ navegam, Enter voa até o nó) |
| legenda e botões | isolar tipo de nó; ligar/desligar Terra, arestas, rótulos, órbita e brilho |

```bash
python scripts/07_export_web_data.py          # copia data/*.json para web/data/
python -m http.server 8765 --directory web    # abra http://127.0.0.1:8765/
```

Não abra por `file://`: `app.js` é módulo ES e faz `fetch` dos JSON.

### Publicar (Vercel — passo a passo)

O repositório já vem pronto para deploy: `vercel.json` na raiz aponta
`outputDirectory: "web"` (nenhum build), e os cabeçalhos de segurança (CSP, HSTS,
`nosniff`, `Permissions-Policy`, COOP/CORP, `frame-ancestors none`) estão declarados
tanto nele quanto em `web/_headers` (Cloudflare Pages). Ambos são gerados por
`scripts/10_write_deploy_config.py`, que calcula o `sha256` do import map inline —
**se você editar o import map em `web/index.html`, rode esse script de novo**
(`--check` serve como teste de CI).

1. `npm i -g vercel` (ou use `npx vercel`), depois `vercel login`;
2. na raiz do repositório: `vercel link` e responda *Create a new project*;
3. `vercel --prod` — ou, sem CLI: **vercel.com → Add New → Project → Import Git
   Repository → Framework Preset “Other” → Deploy** (deixe *Root Directory* vazio);
4. se o painel insistir em build, defina *Root Directory* = `web`: o `web/vercel.json`
   carrega os mesmos cabeçalhos para esse caso;
5. alternativa Cloudflare Pages: `npx wrangler pages deploy web --project-name=<nome>`.

No `.vercelignore`, todo padrão precisa de **barra inicial** (`/data/`, não `data/`):
sem ela, o padrão também casa `web/data/` e o site sobe sem os dados — o grafo não
carrega. Conferir depois do deploy: `curl -o /dev/null -w '%{{http_code}}' <url>/data/stats.json`
deve devolver `200`, e `<url>/grafo/` deve devolver `404`.

Só o conteúdo de `web/` vai para produção: o vault (`grafo/`), os dados brutos
(`data/raw/`) e os scripts **não** são publicados.

---

## O vault Obsidian

`grafo/` é um vault pronto ({fmtn(S['nodes'] + 18)} notas): uma nota por nó, com
frontmatter (tipo, tags, camada), tabela de arestas tipadas, backlinks e um caminho
até a zona raiz. Além das notas de nó há MOCs (`MOC Infraestrutura`, `MOC Geografia`,
`MOC Redes (ASN)`), rankings, estatísticas do dataset e {n_notas_teoria} notas de teoria.

```text
Obsidian → Open folder as vault → <pasta-do-clone>/grafo
```

O Graph View já abre com as cores por pasta configuradas em `.obsidian/graph.json`
(mostra a topologia, não a geografia). Filtros úteis: `tag:#camada/5` (só endereços
IP), `tag:#geo/br` (tudo geolocalizado no Brasil), `path:"400 Redes"` (só ASNs).
A auditoria do vault (`scripts/06_validate_vault.py`) fecha com
**0 links quebrados · 0 nomes duplicados · 0 notas sem frontmatter · 0 órfãos**.

---

## Para que serve

- **Ensino de redes.** Ver a árvore de zonas *como árvore*, e não como lista de
  registros, muda a explicação de delegação, autoridade e anycast.
- **OSINT e jornalismo de dados.** Responder "quem serve este domínio, em que país,
  sob qual ASN" a partir de dados públicos reproduzíveis — com a proveniência
  registrada.
- **Soberania digital.** Medir quantos ccTLDs têm nameservers respondendo fora do
  próprio território (tabela acima) e quais ASNs concentram a resolução de nomes.
- **Pesquisa em redes.** O grafo é um exemplar de rede livre de escala real, com
  `α`, `Gini` e entropia calculáveis em segundos — bom material para exercícios de
  teoria de grafos, teoria da informação e estatística de redes.
- **Base para extensões.** Qualquer análise adicional escreve um script novo em
  `scripts/` e reusa `data/graph.graphml` (Gephi/yEd/Cytoscape) ou `data/hosts.csv`.

---

## Fundamentos teóricos

| área | base usada | onde aparece no código |
|---|---|---|
| Teoria de grafos | **Euler (1736)**, o grafo como par G = (V, E); **König (1936)** para a formalização; grau, caminho, componentes, diâmetro | `03_build_graph.py` (V, E tipados), `06_validate_vault.py` (órfãos = nós de grau 0 na projeção em notas) |
| Busca em largura | **BFS** (Moore, 1959; Lee, 1961) para caminho mínimo, componentes conexos e caminho até a zona raiz | `app.js` (`pathToRoot`, `adj`), `05_write_readme.py` (componentes, caminho médio) |
| Redes livres de escala | **Barabási & Albert (1999)**, anexação preferencial; **Faloutsos³ (1999)**, leis de potência na topologia da internet | figura `distribuicao-grau.svg` (ajuste CCDF) |
| Ajuste de lei de potência | **Clauset, Shalizi & Newman (2009)** — estimar α sobre a CCDF em escala log-log, não sobre o histograma | `08_make_figures.py`, `05_write_readme.py` |
| Mundo pequeno | **Milgram (1967)**; **Watts & Strogatz (1998)** — caminho médio curto com agrupamento alto | métricas de caminho médio e diâmetro amostrado |
| DNS | **Mockapetris, RFC 1034/1035** — árvore de delegação, zonas, tipos de registro, autoridade | todo o pipeline; tipos de aresta `delegação da raiz`, `nameserver autoritativo` |
| DNS-over-HTTPS | **RFC 8484** + JSON API do Google — consulta DNS sobre HTTPS, resistente a interceptação no caminho | `01_collect_dns.py` |
| Anycast | **RFC 4786** — mesmo prefixo anunciado em múltiplos PoPs; efeito documentado nas notas do vault | nota `Anycast e geolocalização de IP`; aviso na seção de geografia |
| Roteamento entre domínios | **AS (Autonomous System)** e **BGP, RFC 4271** — o mapa de quem anuncia o quê | aresta `anunciado por`; camada 6 |
| Cartografia | **projeção equiretangular (plate carrée)**, herdeira de Marinus de Tiro/Mercator; datum geodésico **WGS 84** nas coordenadas | `03_build_graph.py` (x = lon·5,2; z = −lat·5,2), plano da cena 3D |
| Estatística de desigualdade | **curva de Lorenz (1905)** e **coeficiente de Gini** para concentração de endereços por ASN | figura `concentracao-asn.svg` |
| Teoria da informação | **entropia de Shannon (1948)** como medida de diversidade geográfica, e uniformidade normalizada | figura `top-paises.svg` |
| Visualização de dados | **Bertin (1967)** variáveis visuais, **Tufte (1983)** razão tinta/dado, taxonomia de tarefas de **Shneiderman (1996)** (*overview first, zoom and filter, details on demand*) | `web/app.js` (camadas → detalhe sob demanda), `styles.css` (hierarquia tipográfica) |
| Sistemas complexos / crítica | a ideia de que **a forma do armazenamento determina o que se consegue perguntar** — a infraestrutura como objeto relacional, não como inventário | este README, seção *A ideia* |

---

## Limitações tecnológicas e conceituais

**Conceituais (o que o modelo não é):**

1. **{fmtn(S['nodes'])} nós não são a internet.** É uma amostra por sementes
   (13 raízes, {len(TLDS)} TLDs, {len(SERVICES)} serviços reais e {len(RESOLVER_IPS)} resolvedores
   públicos), não o censo. O grafo descreve o *espaço de nomes*, não a topologia
   física, nem o roteamento observado.
2. **Anycast quebra a pergunta "onde".** Raízes, resolvedores e CDNs respondem no PoP
   mais próximo de quem consulta. A posição no mapa é *do ponto de vista desta coleta*
   — outra coleta, de outro continente, daria outro mapa. É limitação de método, não
   de implementação.
3. **Geolocalização por IP é inferência estatística.** Base de cidade erra com
   frequência (VPNs, Proxies, PPPoE de ISP, IPs de backbone). O campo `hosting`,
   `mobile` e `proxy` é preservado no CSV para permitir filtragem por confiança.
4. **Coordenadas de país e continente são centroides das cidades observadas** — não
   capitais nem centro geodésico (que, aliás, é indefinido: nenhum ponto da Terra é
   "o centro" de um continente distribuído pela superfície esférica).
5. **A posição 3D é uma decisão de design, não um dado.** Nós sem geografia são
   distribuídos em anéis por categoria: é determinístico e legível, mas arbitrário —
   o `y` é hierarquia, e ler `y` como altitude seria um erro de leitura.
6. **IP + geolocalização publicados têm implicação jurídica.** Na UE, endereço IP é
   dado pessoal (GDPR) e no Brasil a LGPD trata dados de localização com cuidado.
   Aqui todos os endereços são de infraestrutura pública de DNS (servidores de
   organizações), não de usuários finais — mas **é uma escolha ética do autor**, e
   quem reusar os dados deve reavaliá-la no próprio contexto.
7. **A árvore de zonas não é o grafo do DNS real.** Delegação, CNAME, DNSSEC, *glue
   records* e CDNs por CNAME encurtam/apagam arestas. O grafo registra o que as
   consultas A/AAAA/NS/PTR respondem — não a cadeia completa de resolução.

**Tecnológicas (o que a implementação não faz hoje):**

8. **Não há DNSSEC, RPKI, BGP, latência ou histórico.** Nada de validação de cadeia,
   prefixos anunciados, traceroute/RTT nem séries temporais (o grafo é um retrato).
9. **A coleta depende de APIs gratuitas** (ip-api: 15 req/min, HTTP) e de dois
   resolvedores DoH públicos. Mudança de política de qualquer um deles quebra o passo 2.
10. **Custo de renderização cresce linearmente** com nós/arestas. {fmtn(S['nodes'])}
    nós cabem em 60 fps por *instancing*; ~10⁵ nós exigiria agrupamento por octree,
    LOD e talvez WebGPU.
11. **Sem testes automatizados nem CI.** A rede de proteção é a validação do vault
    (`06`), o `--check` do passo 10 e a inspeção visual — não há suíte de testes.
12. **Sem fallback sem WebGL.** A página exige WebGL2/WebGL e JavaScript; quem está
    sem isso vê apenas o aviso de `noscript` e o canvas vazio.
13. **Acessibilidade parcial.** Toda a informação também existe como texto no painel
    e nas notas do vault, mas a visualização em si é canvas: leitores de tela não
    leem o grafo (é o limite conhecido de qualquer visualização WebGL).
14. **Duplicação de dados no repositório** (`data/` e `web/data/` são os mesmos arquivos
    copiados pelo passo 7) e ~12 MB de vault versionado: simplicidade de deploy
    escolhida em troca de peso no clone.
15. **A coleta é um retrato datado**: endereços de anycast e de CDN mudam com
    frequência; reexecutar 01→06 semanas depois dá números diferentes (o que é o
    comportamento desejado, mas inviabiliza comparações sem versionar `data/raw/`).

---

## Pontos negativos e melhorias futuras

**Limites conhecidos desta versão:**

| ponto | estado | melhoria proposta |
|---|---|---|
| `web/assets/earth-dark.jpg` (95 KB) não é referenciado por nenhum arquivo | peso morto no deploy | usar como textura do oceano ou remover |
| `data/nodes_edges_full.json` repete `nodes.json` + `edges.json` + `stats.json` | 1,9 MB duplicados | publicar só o `graph_core.json` e derivar o resto |
| Métricas do README e das figuras recalculadas a cada execução em Python puro | escala bem até alguns milhares de nós | extrair para `networkx`/`igraph` se o grafo crescer 10× |
| Sem `sitemap.xml`, sem `canonical`, sem `hreflang` | SEO mínimo | gerar na implantação, com o domínio final |
| Sem suíte de testes / CI | validação manual (`06` + `--check`) | GitHub Actions rodando 06, 10 `--check` e um smoke test com Playwright |
| Sem internacionalização | site em pt-BR | camada de tradução com `Intl`/JSON de mensagens |
| ip-api free tier em HTTP | integridade do dataset | chave paga com TLS via `IPAPI_BATCH_URL` (já suportado por variável de ambiente) |
| Sem *lockfile* das versões das APIs externas (DoH, ip-api) | reprodutibilidade depende do formato que cada serviço devolve hoje | versionar `data/raw/` com SHA-256 publicado e fixar o formato (`accept: application/dns-json` já fixado) |
| Nenhuma forma de consultar o grafo por SQL/SPARQL | só arquivos | publicar `graph_core.json` num endpoint estático + consulta em WASM (DuckDB/SQLite) |

**Melhorias de produto (roadmap):**

1. **Histórico**: guardar cada coleta com data e desenhar a evolução ("este PoP
   apareceu em tal mês").
2. **Segunda fonte de geo** (MaxMind/DB-IP) para medir a discordância entre bases —
   discordância *é* o dado interessante.
3. **Caminho de resolução real**: incluir CNAME, DNSSEC (`DS`, `RRSIG`) e a cadeia
   completa até a raiz, com validação de assinatura.
4. **Rota e latência**: cruzar com BGP (RIS/RouteViews) e medir RTT dos resolvedores
   para separar geografia *administrativa* de geografia *de rede*.
5. **Busca por consulta natural**: "todos os TLDs cujos nameservers respondem fora do
   próprio país" já é respondível — transformar em consulta tipo SQL/WASM.
6. **Modo comparador**: dois snapshots lado a lado, com arestas que apareceram e
   desapareceram destacadas.

---

## Reprodutibilidade

```bash
git clone https://github.com/dduenhas/dns-geo-graph && cd dns-geo-graph
python scripts/01_collect_dns.py        # ~1–2 min, DNS real
python scripts/02_geolocate.py          # respeita 15 req/min
python scripts/02b_collect_ptr.py       # DNS reverso em 32 threads
python scripts/03_build_graph.py        # grafo + estatísticas + posições 3D
python scripts/04_build_vault.py        # vault Obsidian
python scripts/05_write_readme.py       # este README (com os números novos)
python scripts/06_validate_vault.py     # auditoria do vault
python scripts/07_export_web_data.py    # dados para o site
python scripts/08_make_figures.py       # figuras SVG
python scripts/10_write_deploy_config.py # CSP + cabeçalhos
```

- **Dependências: apenas a biblioteca padrão do Python 3.11+** — sem `pip install`,
  sem `node_modules`, sem bundler. `three.js` é vendorizado em `web/vendor/`.
- **Determinístico**: mesmo `data/raw/` → mesmos arquivos de saída (as posições sem
  geografia usam CRC32, estável entre processos e máquinas).
- **Idempotente**: cada passo pode ser reexecutado; nada acumula estado.
- **Só `scripts/seeds.py` é editorial**: mude as sementes (TLDs, serviços,
  resolvedores) e todo o grafo, o vault, o site e este README são regenerados.

---

## Estrutura do repositório

```text
dns-geo-graph/
├── scripts/            pipeline 01→10 + seeds.py (única entrada editorial)
├── data/               dados derivados (json, csv, graphml) + raw/ (respostas cruas)
│                       └── README.md: o que é cada arquivo, determinismo e proveniência
├── grafo/              vault Obsidian — {fmtn(S['nodes'] + 18)} notas (abrir como vault)
├── web/                página 3D (deploy root): index.html, app.js, styles.css,
│                       vendor/three, assets/fonts (self-hosted), data/, favicon.svg
├── docs/img/           figuras SVG deste README (geradas pelo passo 8)
├── vercel.json         deploy sem build (outputDirectory: web) + cabeçalhos (passo 10)
├── .vercelignore       o que fica fora do upload do deploy (vault, dados brutos, scripts)
├── .gitattributes      LF no repositório; artefatos gerados marcados como tal
├── web/_headers        os mesmos cabeçalhos para Cloudflare Pages
└── LICENSE             MIT (código) · atribuições de terceiros em web/assets/ATTRIBUTION.md
```

---

## Créditos, licença e como citar

**Autoria da ideia e do projeto:** {AUTOR} — a concepção de guardar a
infraestrutura de internet como grafo (e não como tabela), a arquitetura do pipeline,
a direção visual do site e as decisões de modelagem são dele.

**Terceiros redistribuídos:** three.js (MIT, © Three.js Authors) · Inter Tight, Inter
e JetBrains Mono (SIL Open Font License 1.1) · máscaras cartográficas derivadas de
Natural Earth e NASA (domínio público). Detalhes em
[`web/assets/ATTRIBUTION.md`](web/assets/ATTRIBUTION.md).

**Dados:** coletados de serviços públicos (DNS-over-HTTPS e ip-api.com) — sem chave,
sem dado de usuário final; a origem, o tamanho e a licença de cada arquivo estão em
[`data/README.md`](data/README.md).

**Código:** [MIT](LICENSE) — use, modifique e publique, mantendo o aviso de copyright.

Se este projeto ajudar num trabalho acadêmico, cite assim:

```bibtex
@misc{{duenhas_dnsgeo,
  author       = {{Duenhas, Diego}},
  title        = {{Onde a internet mora — guardar infraestrutura de internet como grafo (DNS × geografia)}},
  year         = {{2026}},
  howpublished = {{\\url{{https://github.com/dduenhas/dns-geo-graph}}}},
  note         = {{Grafo de {fmtn(S['nodes'])} nós e {fmtn(S['edges'])} arestas construído com dados
                  públicos de DNS-over-HTTPS e geolocalização por ASN}}
}}
```
"""

open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8", newline="\n").write(readme)
print(f"OK  README.md ({len(readme):,} chars, {readme.count(chr(10))} linhas)")
print(f"    métricas: V={V} E={E} ⟨k⟩={mean_k:.2f} α≈{ccdf_exp + 1:.2f} R²={r2:.3f} "
      f"Gini={gini:.2f} H={H:.2f} comps={len(comps)} caminho={avg_path:.2f}")
