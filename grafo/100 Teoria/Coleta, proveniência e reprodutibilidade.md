---
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
