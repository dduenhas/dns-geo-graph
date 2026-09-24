# -*- coding: utf-8 -*-
"""07 — Exporta para o site os dados que ele consome e ajusta os números do HTML.

O site é estático e servido a partir de web/ — os JSON precisam viver dentro dele.
Além da cópia, este passo reescreve as contagens que aparecem *em texto* no
index.html (meta description, Open Graph e tela de carregamento), que antes ficavam
desatualizadas a cada nova coleta.
"""
import json, os, re, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
WEB = os.path.join(ROOT, "web", "data")
INDEX = os.path.join(ROOT, "web", "index.html")

FILES = ["graph_core.json", "notes_map.json", "stats.json", "hosts.csv"]

fmtn = lambda n: f"{n:,}".replace(",", ".")


def sync_html_numbers(s):
    """Substitui as contagens em texto do index.html pelos números da coleta."""
    subs = [
        (r"Grafo de [\d.]+ nós", f"Grafo de {fmtn(s['nodes'])} nós"),
        (r"carregando [\d.]+ nós", f"carregando {fmtn(s['nodes'])} nós"),
        (r"[\d.]+ nós de infraestrutura real", f"{fmtn(s['nodes'])} nós de infraestrutura real"),
        (r"[\d.]+ nós de infraestrutura real de internet em 3D",
         f"{fmtn(s['nodes'])} nós de infraestrutura real de internet em 3D"),
    ]
    html = open(INDEX, encoding="utf-8").read()
    for pat, rep in subs:
        html, n = re.subn(pat, rep, html)
        if not n:
            print(f"   ! padrão não encontrado no index.html: {pat!r}")
    open(INDEX, "w", encoding="utf-8", newline="\n").write(html)


def main():
    os.makedirs(WEB, exist_ok=True)
    for f in FILES:
        src, dst = os.path.join(DATA, f), os.path.join(WEB, f)
        if not os.path.exists(src):
            print(f"   ! ausente: {f} (rode o pipeline 01→04 antes)")
            continue
        shutil.copy2(src, dst)
        print(f"   {f:<20} {os.path.getsize(dst)/1024:8.1f} KB")

    core = json.load(open(os.path.join(DATA, "graph_core.json"), encoding="utf-8"))
    sync_html_numbers(core["stats"])
    print(f"OK  web/data pronto — {len(core['nodes'])} nós, {len(core['edges'])} arestas")
    print("    index.html com as contagens sincronizadas")
    print("    rodar: python -m http.server 8765 --directory web")
    print("    depois: python scripts/10_write_deploy_config.py  (CSP/headers)")


if __name__ == "__main__":
    main()
