# -*- coding: utf-8 -*-
"""Baixa as fontes do Google Fonts e as converte em assets locais (woff2).

Motivo: a página declarava "sem CDN em runtime" mas carregava Inter Tight, Inter
e JetBrains Mono direto de fonts.googleapis.com — dependência de terceiros,
vazamento de IP do visitante e impossibilidade de usar CSP restritivo.

As famílias servidas pela API css2 são fontes variáveis: os arquivos de 400 e 500
têm bytes idênticos. O script deduplica por sha256 e declara faixa de peso
(`font-weight: 400 600`), servindo 3 arquivos em vez de 7.
"""
import hashlib, os, re, shutil, urllib.request

# caminho relativo ao próprio script: nada de caminho pessoal no repositório
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, "web")
OUT = os.path.join(WEB, "assets", "fonts")
if os.path.isdir(OUT):
    shutil.rmtree(OUT)
os.makedirs(OUT, exist_ok=True)

FAMS = [
    ("Inter+Tight", "inter-tight", ["400", "500", "600"]),
    ("Inter", "inter", ["400", "500"]),
    ("JetBrains+Mono", "jetbrains-mono", ["400", "500"]),
]
SUBSET = "latin"        # cobre acentuação pt-BR (U+0000-00FF) + pontuação usada
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

blocks, by_hash = [], {}
for api_name, slug, weights in FAMS:
    url = (f"https://fonts.googleapis.com/css2?family={api_name}:wght@"
           f"{';'.join(weights)}&display=swap")
    css = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read().decode()
    group = {}          # sha256 -> (arquivo, [pesos])
    for subset, block in re.findall(r"/\*\s*([\w-]+)\s*\*/\s*(@font-face\s*\{[^}]*\})", css):
        if subset != SUBSET:
            continue
        fam = re.search(r"font-family:\s*'([^']+)'", block).group(1)
        wt = re.search(r"font-weight:\s*(\d+)", block).group(1)
        src = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        ur = re.search(r"unicode-range:\s*([^;]+);", block).group(1).strip()
        data = urllib.request.urlopen(
            urllib.request.Request(src, headers={"User-Agent": UA}), timeout=60).read()
        h = hashlib.sha256(data).hexdigest()
        if h not in group:
            fname = f"{slug}-{SUBSET}.woff2"
            with open(os.path.join(OUT, fname), "wb") as f:
                f.write(data)
            group[h] = (fname, [], ur, fam)
            print(f"   {fname:<28} {len(data)/1024:7.1f} KB  (pesos {'+'.join(weights)})")
        group[h][1].append(wt)
    for h, (fname, wts, ur, fam) in group.items():
        lo, hi = min(wts), max(wts)
        spec = lo if lo == hi else f"{lo} {hi}"
        blocks.append(
            "@font-face {\n"
            f"  font-family: '{fam}';\n  font-style: normal;\n"
            f"  font-weight: {spec};\n  font-display: swap;\n"
            f"  src: url('fonts/{fname}') format('woff2');\n"
            f"  unicode-range: {ur};\n}}")
        by_hash[h] = fname

header = ("/* ==========================================================================\n"
          "   Fontes self-hosted — Inter Tight, Inter e JetBrains Mono\n"
          "   Licença: SIL Open Font License 1.1 (ver assets/fonts/LICENSE.txt).\n"
          "   Gerado por scripts/09_fetch_fonts.py (Google Fonts css2): nenhuma\n"
          "   requisição a terceiros em runtime.\n"
          "   ========================================================================== */\n\n")
with open(os.path.join(WEB, "assets", "fonts.css"), "w", encoding="utf-8", newline="\n") as f:
    f.write(header + "\n\n".join(blocks) + "\n")

total = sum(os.path.getsize(os.path.join(OUT, n)) for n in os.listdir(OUT))
print(f"OK  {len(os.listdir(OUT))} arquivos woff2 ({total/1024:.0f} KB) -> web/assets/fonts/")
print(f"OK  {len(blocks)} @font-face -> web/assets/fonts.css")
