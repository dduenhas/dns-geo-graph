# -*- coding: utf-8 -*-
"""02 — Geolocalização + ASN + PTR dos IPs coletados (ip-api.com, sem chave).

Limite do serviço: 100 IPs por requisição no endpoint /batch, 15 req/min.
Saída: data/raw/geo.json
"""
import json, os, time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")

FIELDS = ("status,message,continent,continentCode,country,countryCode,region,regionName,"
          "city,district,zip,lat,lon,timezone,isp,org,as,asname,reverse,mobile,proxy,hosting,query")
CHUNK = 100

# ip-api free tier só atende em HTTP (sem TLS): os dados de geo/ASN podem ser
# adulterados por um intermediário na rede. Para exigir TLS (plano pago da
# ip-api ou outro provedor compatível com o mesmo formato /batch), defina:
#   IPAPI_BATCH_URL=https://pro.ip-api.com/batch?key=<sua-chave>
IPAPI_BATCH_URL = os.environ.get("IPAPI_BATCH_URL", "http://ip-api.com/batch")


def batch(ips):
    body = json.dumps([{"query": ip, "fields": FIELDS} for ip in ips]).encode()
    req = urllib.request.Request(
        IPAPI_BATCH_URL, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "curl/8.4.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def main():
    with open(os.path.join(RAW, "dns_records.json"), encoding="utf-8") as f:
        dns = json.load(f)
    ips = sorted({ip for e in dns["records"].values()
                  for k in ("A", "AAAA") for ip in e.get(k, [])})
    ips += sorted(dns.get("resolver_ips", {}).keys())
    ips = sorted(set(ips))
    print(f"{len(ips)} IPs para geolocalizar ({len(ips)//CHUNK + 1} lotes)")

    geo, failed = {}, []
    for i in range(0, len(ips), CHUNK):
        chunk = ips[i:i + CHUNK]
        for attempt in range(4):
            try:
                res = batch(chunk)
                for r in res:
                    if r.get("status") == "success":
                        geo[r["query"]] = r
                    else:
                        failed.append((r.get("query"), r.get("message")))
                break
            except Exception as e:
                print(f"   lote {i//CHUNK}: erro {e} — retry {attempt+1}")
                time.sleep(8)
        print(f"   lote {i//CHUNK + 1}: {len(geo)} ok / {len(failed)} falhas")
        time.sleep(4.5)  # respeita 15 req/min

    out = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "ip-api.com /batch (fields completos)",
        "geo": geo,
        "failed": failed,
        "counts": {"queried": len(ips), "ok": len(geo), "failed": len(failed)},
    }
    with open(os.path.join(RAW, "geo.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    countries = {v["countryCode"] for v in geo.values()}
    cities = {(v["countryCode"], v["city"]) for v in geo.values() if v.get("city")}
    asns = {v["as"].split()[0] for v in geo.values() if v.get("as")}
    print(f"OK  {len(geo)} IPs | {len(countries)} países | {len(cities)} cidades | {len(asns)} ASNs")


if __name__ == "__main__":
    main()
