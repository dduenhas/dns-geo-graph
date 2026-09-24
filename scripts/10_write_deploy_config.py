# -*- coding: utf-8 -*-
"""10 — Gera a configuração de deploy (Vercel + Cloudflare Pages) a partir do
index.html.

Por que existe: a CSP restritiva precisa autorizar o `<script type="importmap">`
inline por hash sha256. Três arquivos de configuração com o mesmo hash copiado à
mão desincronizam no primeiro edit; aqui a CSP é definida uma vez e os arquivos
são derivados (dry-run com `--check` para CI).

Saídas: vercel.json (raiz), web/vercel.json (quando o Root Directory = web),
        web/_headers (Cloudflare Pages), web/robots.txt
"""
import base64, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")
INDEX = os.path.join(WEB, "index.html")

CACHE_IMMUTABLE = "public, max-age=31536000, immutable"
CACHE_DATA = "public, max-age=3600"


def csp_for(html):
    """CSP sem origem externa alguma: fontes, libs e dados são servidos do
    próprio domínio. O único inline é o import map, autorizado por hash."""
    m = re.search(r'<script type="importmap">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("! importmap inline não encontrado em web/index.html")
    digest = base64.b64encode(
        hashlib.sha256(m.group(1).encode("utf-8")).digest()).decode()
    return (
        "default-src 'none'; "
        f"script-src 'self' 'sha256-{digest}'; "
        "style-src 'self' 'unsafe-inline'; "      # atributos style="" gerados no DOM
        "img-src 'self' data:; "                  # textura do grão é SVG data:
        "font-src 'self'; "
        "connect-src 'self'; "                    # fetch de ./data/*.json
        "manifest-src 'self'; "
        "base-uri 'none'; "
        "form-action 'none'; "
        "frame-ancestors 'none'; "
        "object-src 'none'; "
        "upgrade-insecure-requests"
    ), digest


def security_headers(csp):
    return [
        {"key": "Content-Security-Policy", "value": csp},
        {"key": "Strict-Transport-Security", "value": "max-age=63072000; includeSubDomains; preload"},
        {"key": "X-Content-Type-Options", "value": "nosniff"},
        {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"},
        {"key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=(), payment=(), usb=()"},
        {"key": "Cross-Origin-Opener-Policy", "value": "same-origin"},
        {"key": "Cross-Origin-Resource-Policy", "value": "same-origin"},
        {"key": "X-Frame-Options", "value": "DENY"},
    ]


def vercel_config(csp, with_output_dir):
    cfg = {
        "$schema": "https://openapi.vercel.sh/vercel.json",
        "cleanUrls": True,
        "headers": [
            {"source": "/(.*)", "headers": security_headers(csp)},
            {"source": "/assets/(.*)", "headers": [
                {"key": "Cache-Control", "value": CACHE_IMMUTABLE}]},
            {"source": "/vendor/(.*)", "headers": [
                {"key": "Cache-Control", "value": CACHE_IMMUTABLE}]},
            {"source": "/data/(.*)", "headers": [
                {"key": "Cache-Control", "value": CACHE_DATA}]},
        ],
    }
    if with_output_dir:
        # deploy direto do repositório: o site é o diretório web/, sem build
        cfg = {"framework": None, "buildCommand": None, "installCommand": None,
               **cfg, "outputDirectory": "web"}
    return cfg


def pages_headers(csp):
    out = ["/*"]
    out += [f"  {h['key']}: {h['value']}" for h in security_headers(csp)]
    out += ["", "/assets/*", f"  Cache-Control: {CACHE_IMMUTABLE}",
            "", "/vendor/*", f"  Cache-Control: {CACHE_IMMUTABLE}",
            "", "/data/*", f"  Cache-Control: {CACHE_DATA}", ""]
    return "\n".join(out)


ROBOTS = """User-agent: *
Allow: /
"""


def main():
    check = "--check" in sys.argv
    html = open(INDEX, encoding="utf-8").read()
    csp, digest = csp_for(html)

    targets = {
        os.path.join(ROOT, "vercel.json"): json.dumps(
            vercel_config(csp, True), indent=2, ensure_ascii=False) + "\n",
        os.path.join(WEB, "vercel.json"): json.dumps(
            vercel_config(csp, False), indent=2, ensure_ascii=False) + "\n",
        os.path.join(WEB, "_headers"): pages_headers(csp),
        os.path.join(WEB, "robots.txt"): ROBOTS,
    }

    drift = []
    for path, content in targets.items():
        old = open(path, encoding="utf-8").read() if os.path.exists(path) else None
        if old == content:
            print(f"   ok        {os.path.relpath(path, ROOT)}")
        elif check and old is not None:
            drift.append(os.path.relpath(path, ROOT))
            print(f"   DESATUALIZADO {os.path.relpath(path, ROOT)}")
        else:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            print(f"   escrito   {os.path.relpath(path, ROOT)}")

    print(f"\nimport map sha256-{digest}")
    if drift:
        raise SystemExit(f"! {len(drift)} arquivo(s) fora de sincronia com index.html: {drift}")
    print("OK  CSP e cabeçalhos de segurança derivados de web/index.html")


if __name__ == "__main__":
    main()
