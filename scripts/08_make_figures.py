# -*- coding: utf-8 -*-
"""08 — Gera as figuras (SVG) do README a partir dos dados do grafo.

Sem dependências externas: os gráficos são escritos como SVG à mão (mesma paleta
do site), e o mapa-múndi é reconstruído do próprio mask de continentes que a
cena 3D usa (PNG 8-bit grayscale decodificado com zlib, redimensionado para uma
malha de ~2°).

Saída: docs/img/*.svg
"""
import json, math, os, re, zlib
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)

BG, INK, INK2, INK3 = "#111114", "#f2f3f5", "rgba(242,243,245,.62)", "rgba(242,243,245,.38)"
AC, AC2, WARN, HL = "#00b4d8", "#48cae4", "#ff4d6d", "#ffd166"
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Roboto,"
        "Helvetica,Arial,sans-serif")
MONO = "ui-monospace,SFMono-Regular,'JetBrains Mono',Consolas,monospace"

KIND_COLOR = {
    "hub": "#ffffff", "root": "#ff4d6d", "tld": "#ff8c42", "service": "#ffd166",
    "ns": "#2ec4b6", "ptr": "#1d9e94", "resolver_host": "#2ec4b6",
    "resolver_org": "#06d6a0", "ip": "#00b4d8", "asn": "#b388ff",
    "city": "#ff69b4", "country": "#e8a2ff", "continent": "#c9ada7",
}

core = json.load(open(os.path.join(DATA, "graph_core.json"), encoding="utf-8"))
stats = core["stats"]
gd = json.load(open(os.path.join(DATA, "nodes_edges_full.json"), encoding="utf-8"))
notes = json.load(open(os.path.join(DATA, "notes_map.json"), encoding="utf-8"))
PT = notes.get("countries_pt", {})


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" role="img" aria-label="{esc(title)}" '
            f'font-family="{FONT}">\n'
            f'<title>{esc(title)}</title>\n'
            f'<rect width="{w}" height="{h}" rx="12" fill="{BG}"/>\n'
            f'<rect x=".5" y=".5" width="{w-1}" height="{h-1}" rx="12" fill="none" '
            f'stroke="rgba(255,255,255,.10)"/>\n{body}\n</svg>\n')


def txt(x, y, s, size=12, fill=INK2, anchor="start", weight="400", mono=False,
        ls="0", opacity="1"):
    fam = f' font-family="{MONO}"' if mono else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}"{fam} '
            f'letter-spacing="{ls}" opacity="{opacity}">{esc(s)}</text>')


def save(name, content):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print(f"   {name:<26} {os.path.getsize(p)/1024:7.1f} KB")


# ══════════════════════════════════════════════════════════════════════════
# 1) fluxo do pipeline
# ══════════════════════════════════════════════════════════════════════════
def fig_pipeline():
    W, H = 960, 400
    steps = [
        ("seeds.py", "13 raízes · ~70 TLDs\n~57 serviços · 30 resolvedores", AC),
        ("01–02 · coleta", "DNS-over-HTTPS (RFC 8484)\nip-api /batch · PTR reverso", AC2),
        ("03 · grafo", "V = 2.747 nós\nE = 7.639 arestas tipadas", HL),
        ("04 · vault", "2.765 notas Obsidian\n(frontmatter + wikilinks)", "#2ec4b6"),
        ("web/ · three.js", "posição pré-calculada\n(x, y=camada, z=geo)", "#b388ff"),
    ]
    b = []
    bw, gap, x0, y = 158, 30, 26, 150
    for i, (title, sub, col) in enumerate(steps):
        x = x0 + i * (bw + gap)
        b.append(f'<rect x="{x}" y="{y}" width="{bw}" height="112" rx="10" '
                 f'fill="rgba(255,255,255,.035)" stroke="rgba(255,255,255,.12)"/>')
        b.append(f'<rect x="{x}" y="{y}" width="3" height="112" rx="2" fill="{col}"/>')
        b.append(txt(x + 14, y + 28, title, 13.5, INK, weight="600"))
        for j, line in enumerate(sub.split("\n")):
            b.append(txt(x + 14, y + 52 + j * 16, line, 11, INK2, mono=True))
        if i < len(steps) - 1:
            xa = x + bw + 6
            b.append(f'<path d="M{xa} {y+56} h{gap-14} m-6 -5 l6 5 l-6 5" fill="none" '
                     f'stroke="{INK3}" stroke-width="1.4"/>')
    b.append(txt(26, 46, "pipeline determinístico — rode 01→10 e todo o grafo é regenerado",
                 15, INK, weight="600"))
    b.append(txt(26, 70, "a única entrada editorial é scripts/seeds.py; nada de dado sintético ou inventado",
                 11.5, INK3))
    b.append(txt(26, 300, "fontes de dado", 11, INK3, ls=".16em"))
    srcs = ["DNS-over-HTTPS — cloudflare-dns.com (RFC 8484)", "dns.google — fallback",
            "ip-api.com/batch — geo · ASN · hosting", "DNS reverso do SO — in-addr.arpa · ip6.arpa"]
    for i, s in enumerate(srcs):
        b.append(f'<circle cx="{32 + (i % 2) * 470}" cy="{322 + (i // 2) * 22}" r="3" fill="{AC}"/>')
        b.append(txt(44 + (i % 2) * 470, 326 + (i // 2) * 22, s, 11.5, INK2, mono=True))
    save("pipeline.svg", svg(W, H, "\n".join(b), "Pipeline de coleta e geração do grafo"))


# ══════════════════════════════════════════════════════════════════════════
# 2) distribuição de grau (log-log) + ajuste de lei de potência
# ══════════════════════════════════════════════════════════════════════════
def fig_degree():
    ids = {n["id"] for n in core["nodes"]}
    deg = Counter()
    for e in core["edges"]:
        if e["source"] in ids and e["target"] in ids:
            deg[e["source"]] += 1
            deg[e["target"]] += 1
    for i in ids:
        deg.setdefault(i, 0)
    n = len(ids)
    mean_d = sum(deg.values()) / n
    # cauda em escala livre: usamos a CCDF P(K >= k), que é a forma canônica de
    # checar lei de potência em amostra finita (Clauset–Shalizi–Newman, 2009).
    ks = sorted(k for k in set(deg.values()) if k >= 1)
    ccdf = {k: sum(1 for v in deg.values() if v >= k) / n for k in ks}
    pts = [(math.log10(k), math.log10(ccdf[k])) for k in ks if k >= 2 and ccdf[k] > 0]
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    slope = (sum((p[0] - mx) * (p[1] - my) for p in pts) /
             sum((p[0] - mx) ** 2 for p in pts))
    alpha = 1 - slope                   # CCDF ~ k^-(alpha-1)
    intercept = my - slope * mx
    ss_res = sum((p[1] - (slope * p[0] + intercept)) ** 2 for p in pts)
    r2 = 1 - ss_res / sum((p[1] - my) ** 2 for p in pts)
    kmin = 2
    pairs = sorted(zip(ks, [ccdf[k] for k in ks]))

    W, H = 900, 470
    L, R, T, B = 84, 40, 64, 78
    pw, ph = W - L - R, H - T - B
    lx0, lx1 = math.log10(1), math.log10(max(ks))
    ly0, ly1 = math.log10(0.5 / n), math.log10(1.2)
    px = lambda k: L + (math.log10(k) - lx0) / (lx1 - lx0) * pw
    py = lambda v: T + ph - (math.log10(v) - ly0) / (ly1 - ly0) * ph
    b = [txt(24, 38, "o grafo é livre de escala? — cauda da distribuição de grau", 15, INK, weight="600"),
         txt(24, 56, f"CCDF P(K ≥ k) ~ k^−{alpha-1:.2f} → expoente α = {alpha:.2f} "
                     f"(ajuste log-log, R² = {r2:.3f}) · ⟨k⟩ = {mean_d:.2f} · k máximo = {max(deg.values())}",
             11.5, INK3)]
    for e in range(-3, 2):
        v = 10 ** e
        if not (ly0 <= math.log10(v) <= ly1):
            continue
        y = py(v)
        b.append(f'<line x1="{L}" y1="{y:.1f}" x2="{W-R}" y2="{y:.1f}" stroke="rgba(255,255,255,.10)"/>')
        lab = f"{v:g}" if v >= 1 else f"1e{e}"
        b.append(txt(L - 10, y + 4, lab, 10.5, INK3, anchor="end", mono=True))
    for e in range(0, 4):
        k = 10 ** e
        if k > max(ks):
            break
        x = px(k)
        b.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{T+ph}" stroke="rgba(255,255,255,.10)"/>')
        b.append(txt(x, T + ph + 20, f"{k:g}", 10.5, INK3, anchor="middle", mono=True))
    b.append(f'<line x1="{L}" y1="{T+ph}" x2="{W-R}" y2="{T+ph}" stroke="rgba(255,255,255,.22)"/>')
    b.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+ph}" stroke="rgba(255,255,255,.22)"/>')
    k2 = max(ks)
    b.append(f'<line x1="{px(kmin):.1f}" y1="{py(10**(slope*math.log10(kmin)+intercept)):.1f}" '
             f'x2="{px(k2):.1f}" y2="{py(10**(slope*math.log10(k2)+intercept)):.1f}" '
             f'stroke="{HL}" stroke-width="1.4" stroke-dasharray="5 4" opacity=".9"/>')
    b.append(f'<path d="M{" L".join(f"{px(k):.1f} {py(v):.1f}" for k, v in pairs)}" '
             f'fill="none" stroke="{AC}" stroke-width="2"/>')
    b.append(f'<g fill="{AC}">')
    for k, v in pairs:
        b.append(f'<circle cx="{px(k):.1f}" cy="{py(v):.1f}" r="3.1"/>')
    b.append("</g>")
    b.append(txt(px(kmin) + 10, py(ccdf[kmin]) + 4,
                 f"k ≥ {kmin}: começo da reta (região de escala)", 10.5, INK2))
    yl_cx, yl_cy = 22, T + ph / 2
    b.append(f'<text x="0" y="0" font-size="12" fill="{INK2}" text-anchor="middle" '
             f'transform="translate({yl_cx} {yl_cy}) rotate(-90)">P(K ≥ k)</text>')
    b.append(txt(L + pw / 2, H - 26, "grau k (arestas por nó, escala log)", 12, INK2, anchor="middle"))
    b.append(f'<rect x="{W-262}" y="{T+14}" width="224" height="56" rx="8" '
             f'fill="rgba(255,255,255,.04)" stroke="rgba(255,255,255,.12)"/>')
    b.append(txt(W - 250, T + 34, f"nós {stats['nodes']} · arestas {stats['edges']}", 11, INK2, mono=True))
    b.append(txt(W - 250, T + 52, f"densidade {2*stats['edges']/(n*(n-1)):.2e}", 11, INK3, mono=True))
    save("distribuicao-grau.svg", svg(W, H, "\n".join(b),
                                      "Cauda da distribuição de grau do grafo DNS × geo"))


# ══════════════════════════════════════════════════════════════════════════
# 3) mapa equiretangular + PoPs
# ══════════════════════════════════════════════════════════════════════════
def decode_png_gray(path, step=4):
    """Decodifica PNG 8-bit grayscale (não entrelaçado) e devolve uma malha
    booleana de 'terra' amostrada a cada `step` pixels."""
    raw = open(path, "rb").read()
    pos, w, h, idat = 8, 0, 0, b""
    while pos < len(raw):
        ln = int.from_bytes(raw[pos:pos + 4], "big")
        typ = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h = int.from_bytes(data[0:4], "big"), int.from_bytes(data[4:8], "big")
            assert data[8] == 8 and data[9] == 0, "esperado PNG grayscale 8-bit"
        elif typ == b"IDAT":
            idat += data
        elif typ == b"IEND":
            break
        pos += 12 + ln
    buf = zlib.decompress(idat)
    stride = w + 1
    prev = bytearray(w)
    rows = []
    for y in range(h):
        ft = buf[y * stride]
        line = bytearray(buf[y * stride + 1:(y + 1) * stride])
        for i in range(w):                      # desfiltro (filtros 0–4)
            a = line[i - 1] if i else 0
            b_ = prev[i]
            c = prev[i - 1] if i else 0
            if ft == 1: line[i] = (line[i] + a) & 255
            elif ft == 2: line[i] = (line[i] + b_) & 255
            elif ft == 3: line[i] = (line[i] + ((a + b_) >> 1)) & 255
            elif ft == 4:
                p = a + b_ - c
                pa, pb, pc = abs(p - a), abs(p - b_), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b_ if pb <= pc else c)
                line[i] = (line[i] + pr) & 255
        rows.append(line)
        prev = line
    grid = [[rows[y][x] > 110 for x in range(0, w, step)] for y in range(0, h, step)]
    return grid


def fig_world():
    grid = decode_png_gray(os.path.join(ROOT, "web", "assets", "earth-topology.png"), step=5)
    gh, gw = len(grid), len(grid[0])
    W, H = 960, 560
    ML, MT, MW, MH = 30, 74, 900, 450
    def xy(lon, lat):
        return ML + (lon + 180) / 360 * MW, MT + (90 - lat) / 180 * MH
    b = []
    # malha de terra
    segs = []
    for gy, row in enumerate(grid):
        gx = 0
        while gx < gw:
            if row[gx]:
                x0 = gx
                while gx < gw and row[gx]:
                    gx += 1
                lon0 = -180 + x0 / gw * 360
                lon1 = -180 + gx / gw * 360
                lat = 90 - (gy + .5) / gh * 180
                xa, ya = xy(lon0, lat)
                xb, _ = xy(lon1, lat)
                xa, ya, xb, hh = round(xa, 1), round(ya, 1), round(xb, 1), MH / gh + 0.35
                segs.append(f"M{xa} {ya}h{max(0.6, round(xb-xa,1))}v{round(hh,2)}h-{max(0.6, round(xb-xa,1))}z")
            else:
                gx += 1
    b.append(f'<path d="{"".join(segs)}" fill="rgba(0,180,216,.22)" '
             f'shape-rendering="crispEdges"/>')
    # grade de paralelos/meridianos
    for lon in range(-150, 180, 30):
        x, _ = xy(lon, 0)
        b.append(f'<line x1="{x:.1f}" y1="{MT}" x2="{x:.1f}" y2="{MT+MH}" stroke="rgba(255,255,255,.06)"/>')
    for lat in range(-60, 90, 30):
        _, y = xy(0, lat)
        b.append(f'<line x1="{ML}" y1="{y:.1f}" x2="{ML+MW}" y2="{y:.1f}" stroke="rgba(255,255,255,.06)"/>')
        b.append(txt(ML - 8, y + 3.5, f"{lat}°", 9.5, INK3, anchor="end", mono=True))
    # PoPs (nós de cidade) e peso por nº de endereços observados no PoP
    ipcity = Counter()
    for n in gd["nodes"]:
        if n["kind"] == "ip" and isinstance(n.get("lat"), (int, float)):
            ipcity[(round(n["lat"], 3), round(n["lon"], 3))] += 1
    maxn = max(ipcity.values()) if ipcity else 1
    b.append(f'<g fill="{HL}" fill-opacity=".85" stroke="rgba(0,0,0,.5)" stroke-width=".5">')
    for (lat, lon), cnt in sorted(ipcity.items(), key=lambda kv: -kv[1]):
        x, y = xy(lon, lat)
        r = 1.7 + 5.4 * (cnt / maxn) ** .5
        b.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
    b.append("</g>")
    top = ipcity.most_common(5)
    used = []
    for i, ((lat, lon), cnt) in enumerate(top):
        x, y = xy(lon, lat)
        nm = next((f"{n.get('city')}, {n.get('country_cc')}" for n in gd["nodes"]
                   if n["kind"] == "city" and abs(n.get("lat", 99) - lat) < .002
                   and abs(n.get("lon", 99) - lon) < .002), "—")
        dx, dy = (10, -8) if i % 2 == 0 else (10, 16)
        while any(abs(x + dx - ux) < 150 and abs(y + dy - uy) < 13 for ux, uy in used):
            dy += 14 if i % 2 == 0 else 14
        used.append((x + dx, y + dy))
        b.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+dx-3:.1f}" y2="{y+dy-4:.1f}" '
                 f'stroke="{INK3}" stroke-width=".6"/>')
        b.append(txt(x + dx, y + dy, f"{nm} · {cnt}", 10, INK, mono=True))
    b.append(txt(30, 40, "pontos de presença observados — projeção equiretangular", 15, INK, weight="600"))
    b.append(txt(30, 58, f"{stats['cities']} cidades/PoPs · {stats['countries']} países · "
                         f"{stats['ips_geolocated']}/{stats['ips_total']} endereços geolocalizados "
                         f"({100*stats['ips_geolocated']/stats['ips_total']:.1f}%)", 11.5, INK3))
    b.append(txt(30, 542, "cada círculo é um PoP; o raio cresce com a raiz do número de endereços observados ali. "
                          "Posição = estimativa da API de geo (o PoP que respondeu), não a sede da organização.",
                 10, INK3))
    save("pops-mundo.svg", svg(W, H, "\n".join(b), "PoPs observados no mundo em projeção equiretangular"))


# ══════════════════════════════════════════════════════════════════════════
# 4) barras: países (com entropia de Shannon) e as camadas do grafo
# ══════════════════════════════════════════════════════════════════════════
def hbars(title, sub, rows, color_of, width=900, rowh=26, xlab="nós"):
    H = 96 + len(rows) * rowh + 34
    L, R = 250, 96
    pw = width - L - R
    mx = max(v for _, v, _ in rows) or 1
    b = [txt(24, 40, title, 15, INK, weight="600"), txt(24, 58, sub, 11.5, INK3)]
    y = 84
    for label, v, extra in rows:
        w = max(2, v / mx * pw)
        b.append(txt(L - 12, y + 13, label, 11.5, INK2, anchor="end", mono=True))
        b.append(f'<rect x="{L}" y="{y + 2}" width="{w:.1f}" height="{rowh - 10}" rx="3" '
                 f'fill="{color_of(label, v)}" fill-opacity=".85"/>')
        b.append(txt(L + w + 8, y + 13, extra or f"{v:,}".replace(",", "."), 11, INK3, mono=True))
        y += rowh
    b.append(txt(24, y + 22, xlab, 10.5, INK3, mono=True))
    return svg(width, H, "\n".join(b), title)


def fig_countries():
    c = Counter(n.get("country_cc") for n in gd["nodes"]
                if n["kind"] == "ip" and n.get("country_cc"))
    tot = sum(c.values())
    top = c.most_common(15)
    p = [v / tot for v in c.values()]
    H = -sum(x * math.log2(x) for x in p)
    even = H / math.log2(len(c))
    rows = [(f"{PT.get(cc, cc)} ({cc})", v, f"{v} · {100*v/tot:.1f}%") for cc, v in top]
    # cor por continente do cc? usa accent e destaca BR
    color = lambda label, v: (HL if label.endswith("(BR)") else
                              ("#ff69b4" if label.endswith("(CA)") else AC))
    sub = (f"entropia de Shannon H = {H:.2f} bits sobre {len(c)} países "
           f"(máx. {math.log2(len(c)):.2f}) · uniformidade {even:.2f} — "
           f"a internet concentra, mas não é um só lugar")
    save("top-paises.svg", hbars("de onde a internet responde — top 15 países",
                                 sub, rows, color, xlab="endereços IP"))


def fig_layers():
    layers = [(0, "hubs do grafo", "hub"), (1, "servidores raiz (anycast)", "root"),
              (2, "zonas de topo (TLD)", "tld"), (3, "domínios e serviços", "service"),
              (4, "nameservers · PTR · resolvedores", "ns"),
              (5, "endereços IP", "ip"), (6, "ASN · cidade / PoP", "asn"),
              (7, "países", "country"), (8, "continentes", "continent")]
    nb = {int(k): v for k, v in stats["nodes_by_layer"].items()}
    rows = [(f"{i} · {name}", nb.get(i, 0), f"{nb.get(i,0)}") for i, name, _ in layers]
    color = lambda label, v: KIND_COLOR[dict((str(i), k) for i, _, k in layers)[label.split(" · ")[0]]]
    sub = (f"{stats['nodes']} nós em 9 níveis · eixo vertical da cena 3D é a hierarquia "
           f"(y = (camada − 4) × 1,70), não altitude")
    save("camadas.svg", hbars("as nove camadas do grafo", sub, rows, color, xlab="nós"))


# ══════════════════════════════════════════════════════════════════════════
# 5) concentração de ASN — curva de Lorenz + Gini
# ══════════════════════════════════════════════════════════════════════════
def fig_lorenz():
    per_asn = Counter(n.get("asn") for n in gd["nodes"]
                      if n["kind"] == "ip" and n.get("asn"))
    counts = sorted(per_asn.values())
    n = len(counts)
    tot = sum(counts)
    cum, pts = 0, [(0, 0)]
    for i, v in enumerate(counts, 1):
        cum += v
        pts.append((i / n, cum / tot))
    gini = 1 - 2 * sum((pts[i + 1][0] - pts[i][0]) * (pts[i + 1][1] + pts[i][1]) / 2
                       for i in range(len(pts) - 1))
    top10 = per_asn.most_common(10)
    share10 = 100 * sum(v for _, v in top10) / tot
    W, H = 900, 460
    L, T, S = 96, 74, 320
    px = lambda x: L + x * S
    py = lambda y: T + S - y * S
    b = [txt(24, 40, "concentração por rede (ASN)", 15, INK, weight="600"),
         txt(24, 58, f"{n} sistemas autônomos anunciam os {stats['ips_total']} endereços do grafo · "
                     f"Gini = {gini:.2f} · top 10 concentram {share10:.0f}% dos endereços",
             11.5, INK3)]
    for i in range(6):
        g = i / 5
        b.append(f'<line x1="{px(g):.1f}" y1="{T}" x2="{px(g):.1f}" y2="{T+S}" stroke="rgba(255,255,255,.07)"/>')
        b.append(f'<line x1="{L}" y1="{py(g):.1f}" x2="{L+S}" y2="{py(g):.1f}" stroke="rgba(255,255,255,.07)"/>')
        b.append(txt(L - 10, py(g) + 4, f"{int(g*100)}%", 10, INK3, anchor="end", mono=True))
        b.append(txt(px(g), T + S + 20, f"{int(g*100)}%", 10, INK3, anchor="middle", mono=True))
    b.append(f'<line x1="{L}" y1="{T}" x2="{L}" y2="{T+S}" stroke="rgba(255,255,255,.22)"/>')
    b.append(f'<line x1="{L}" y1="{T+S}" x2="{L+S}" y2="{T+S}" stroke="rgba(255,255,255,.22)"/>')
    b.append(f'<line x1="{px(0)}" y1="{py(0)}" x2="{px(1)}" y2="{py(1)}" '
             f'stroke="{INK3}" stroke-dasharray="5 4"/>')
    b.append(txt(px(.62), py(.72), "igualdade perfeita", 10, INK3))
    path = "M" + " L".join(f"{px(x):.1f} {py(y):.1f}" for x, y in pts)
    b.append(f'<path d="{path}" fill="none" stroke="{AC}" stroke-width="2"/>')
    b.append(f'<path d="{path} L{px(1):.1f} {py(1):.1f} L{px(0):.1f} {py(1):.1f} Z" '
             f'fill="{AC}" fill-opacity=".12"/>')
    top10 = per_asn.most_common(10)
    b.append(txt(L + S + 46, T + 10, "top redes por endereços", 11, INK3, ls=".14em"))
    y = T + 34
    for asn, v in top10:
        b.append(f'<circle cx="{L+S+52}" cy="{y-4}" r="3" fill="{AC}"/>')
        b.append(txt(L + S + 64, y, f"{asn}  {v}", 10.5, INK2, mono=True))
        y += 21
    b.append(txt(L, H - 22, "fração acumulada de ASNs (do menor para o maior)", 10.5, INK3))
    save("concentracao-asn.svg", svg(W, H, "\n".join(b), "Curva de Lorenz da concentração de endereços por ASN"))


# ══════════════════════════════════════════════════════════════════════════
# 6) subgrafo da zona .br — leitura da hierarquia camada por camada
# ══════════════════════════════════════════════════════════════════════════
def fig_subgraph_br():
    """Recorte da zona .br desenhado como DAG em camadas (Sugiyama simplificado):
    cada camada é uma linha horizontal e cada nameserver ganha uma coluna própria,
    para que a relação 'quem serve quem' seja lida de cima para baixo."""
    by = {n["id"]: n for n in gd["nodes"]}
    root = "TLD .br"
    nss = sorted({e["target"] for e in gd["edges"]
                  if e["source"] == root and e["type"] == "nameserver autoritativo"
                  and e["target"] in by})
    ips_of = {ns: sorted({e["target"] for e in gd["edges"]
                          if e["source"] == ns and e["type"].startswith("resolve para")
                          and e["target"] in by}) for ns in nss}
    l6 = defaultdict(set)
    for ns, ips in ips_of.items():
        for ip in ips:
            for e in gd["edges"]:
                if e["source"] == ip and e["type"] in ("anunciado por", "ponto de presença em",
                                                       "geolocalizado em", "PTR") and e["target"] in by:
                    l6[ns].add(e["target"])
    W, H = 980, 660
    y_l2, y_l4, y_l5, y_l6 = 120, 236, 372, 520
    b = []
    for i, (y, lab) in enumerate([(y_l2, "camada 2 — zona de topo"),
                                  (y_l4, "camada 4 — nameservers autoritativos"),
                                  (y_l5, "camada 5 — endereços IP"),
                                  (y_l6, "camadas 6–7 — rede, PoP e país")]):
        b.append(f'<line x1="30" y1="{y}" x2="{W-30}" y2="{y}" stroke="rgba(255,255,255,.07)"/>')
        b.append(txt(34, y - 10, lab, 9.5, INK3, mono=True))
    colw = (W - 80) / len(nss)
    b.append(f'<circle cx="{W/2:.0f}" cy="{y_l2}" r="6" fill="{KIND_COLOR["tld"]}"/>')
    b.append(txt(W / 2, y_l2 - 14, root, 11.5, INK, anchor="middle", mono=True))
    # 1ª passada: posições (preserva ordem de descoberta para o eixo de baixo)
    seen6, ns_x, ip_pos = {}, {}, []
    for i, ns in enumerate(nss):
        xs = 40 + colw * (i + .5)
        ns_x[ns] = xs
        for j, ip in enumerate(ips_of[ns][:4]):
            xi = min(max(xs + (j - (len(ips_of[ns][:4]) - 1) / 2) * 21, 34), W - 34)
            ip_pos.append((ns, ip, xi))
            for nid in sorted(l6[ns]):
                seen6.setdefault(nid, len(seen6))
    # 2ª passada: arestas e nós
    b.append(f'<g stroke="{AC}">')
    for ns in nss:
        b.append(f'<line x1="{W/2:.0f}" y1="{y_l2+6}" x2="{ns_x[ns]:.1f}" y2="{y_l4-6}" '
                 f'stroke-opacity=".45"/>')
    for ns, ip, xi in ip_pos:
        b.append(f'<line x1="{ns_x[ns]:.1f}" y1="{y_l4+5}" x2="{xi:.1f}" y2="{y_l5-5}" '
                 f'stroke-opacity=".35"/>')
    for ns, ip, xi in ip_pos:
        for nid in sorted(l6[ns]):
            kx = 60 + (W - 120) * (seen6[nid] / max(1, len(seen6) - 1))
            b.append(f'<line x1="{xi:.1f}" y1="{y_l5+4}" x2="{kx:.1f}" y2="{y_l6-6}" '
                     f'stroke-opacity=".16"/>')
    b.append("</g>")
    for i, ns in enumerate(nss):
        xs = ns_x[ns]
        b.append(f'<circle cx="{xs:.1f}" cy="{y_l4}" r="4" fill="{KIND_COLOR["ns"]}"/>')
        b.append(txt(xs, y_l4 - 12, ns, 10, INK2, anchor="middle", mono=True))
    for ns, ip, xi in ip_pos:
        b.append(f'<circle cx="{xi:.1f}" cy="{y_l5}" r="3.1" fill="{KIND_COLOR["ip"]}"/>')
    for nid, idx in sorted(seen6.items(), key=lambda kv: kv[1]):
        n = by[nid]
        kx = 60 + (W - 120) * (idx / max(1, len(seen6) - 1))
        col = KIND_COLOR.get(n["kind"], AC)
        r = 3.4 if n["kind"] in ("asn", "city") else 3
        b.append(f'<circle cx="{kx:.1f}" cy="{y_l6}" r="{r}" fill="{col}"/>')
        if n["kind"] in ("city", "asn"):
            b.append(txt(kx, y_l6 + 16, nid[:22], 9, INK3, anchor="middle", mono=True))
    b.append(txt(24, 40, "um recorte real: a zona .br e o que pende dela", 15, INK, weight="600"))
    nrec = 1 + len(nss) + sum(len(v) for v in ips_of.values()) + len(seen6)
    b.append(txt(24, 58, f"{len(nss)} nameservers autoritativos (.dns.br) · "
                         f"{sum(len(v) for v in ips_of.values())} endereços · "
                         f"{len(seen6)} nós de rede/PoP/país — {nrec} nós, "
                         f"delegação da raiz até o continente", 11.5, INK3))
    b.append(txt(24, H - 18, "cores = tipos de nó da legenda do site; topo→base = mesma ordem de camadas "
                             "da cena 3D (o eixo vertical é hierarquia, não altitude)", 10, INK3))
    save("subgrafo-br.svg", svg(W, H, "\n".join(b), "Subgrafo da zona .br"))


if __name__ == "__main__":
    print("figuras -> docs/img/")
    fig_pipeline()
    fig_layers()
    fig_degree()
    fig_world()
    fig_countries()
    fig_lorenz()
    fig_subgraph_br()
    print(f"OK  {len(os.listdir(OUT))} figuras em docs/img/")
