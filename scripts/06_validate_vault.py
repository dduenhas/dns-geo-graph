# -*- coding: utf-8 -*-
"""06 — Valida o vault: links resolvidos, frontmatter, cobertura de nós."""
import json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
VAULT = os.path.join(ROOT, "grafo")

LINK = re.compile(r"\[\[([^\]\|#]+)(?:[#\|][^\]]*)?\]\]")
fm_re = re.compile(r"^---\n(.*?)\n---\n", re.S)

names = {}
dupes = defaultdict(list)
files = 0
for dirpath, _, fnames in os.walk(VAULT):
    if ".obsidian" in dirpath:
        continue
    for fn in fnames:
        if not fn.endswith(".md"):
            continue
        stem = fn[:-3]
        dupes[stem].append(os.path.relpath(os.path.join(dirpath, fn), VAULT))
        names[stem] = os.path.join(dirpath, fn)
        files += 1

all_links = Counter()
broken = Counter()
broken_src = defaultdict(list)
no_fm = []
tags = Counter()
total_link_uses = 0
for stem, path in names.items():
    t = open(path, encoding="utf-8").read()
    m = fm_re.match(t)
    if not m:
        no_fm.append(stem)
    else:
        for line in m.group(1).splitlines():
            if line.startswith("tags:"):
                for tag in re.findall(r"[\wçãéíóúâêôàÁÉÍÓÚ/\-]+", line.split(":", 1)[1]):
                    tags[tag] += 1
    for tgt in LINK.findall(t):
        tgt = tgt.strip()
        total_link_uses += 1
        all_links[tgt] += 1
        if tgt not in names and not tgt.endswith((".csv", ".json", ".graphml")):
            broken[tgt] += 1
            broken_src[tgt].append(stem)

gd = json.load(open(os.path.join(ROOT, "data", "nodes_edges_full.json"), encoding="utf-8"))
stats = gd["stats"]

print(f"notas .md: {files}")
print(f"nomes duplicados: {sum(1 for k, v in dupes.items() if len(v) > 1)}")
for k, v in list((k, v) for k, v in dupes.items() if len(v) > 1)[:5]:
    print("   ", k, "->", v)
print(f"usos de wikilink: {total_link_uses} | alvos distintos: {len(all_links)}")
print(f"links quebrados (alvo distinto): {len(broken)} | usos quebrados: {sum(broken.values())}")
for k, v in broken.most_common(12):
    print(f"   ! [[{k}]] x{v} <- {broken_src[k][:2]}")
print(f"notas sem frontmatter: {len(no_fm)} {no_fm[:8]}")
print(f"tags distintas: {len(tags)}")
print("   top tags:", tags.most_common(10))
print(f"\ngrafo: {stats['nodes']} nós / {stats['edges']} arestas")
referenced = set(all_links)
orphans = sorted(set(names) - referenced)
print(f"notas nunca referenciadas por outra nota: {len(orphans)} {orphans[:8]}")
print("arquivos de dados:", sorted(os.listdir(os.path.join(ROOT, "data"))))
