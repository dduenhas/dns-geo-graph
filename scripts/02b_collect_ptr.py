# -*- coding: utf-8 -*-
"""02b — DNS reverso (PTR) real dos IPs coletados.

O endpoint /batch da ip-api não devolve o campo `reverse` (só consulta individual).
PTR é informação de DNS: usamos o resolvedor do próprio sistema (getnameinfo /
in-addr.arpa / ip6.arpa) — rápido e autoritativo.

Saída: data/raw/ptr.json  (gravação incremental)
"""
import json, os, socket, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")


def ptr(ip):
    try:
        return ip, socket.gethostbyaddr(ip)[0]
    except Exception:
        return ip, None


def save(out, queried, t0, partial):
    tmp = os.path.join(RAW, "ptr.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                   "source": "DNS reverse (in-addr.arpa / ip6.arpa) via resolvedor do sistema",
                   "partial": partial, "ptr": out,
                   "counts": {"queried_total": queried, "with_ptr": len(out),
                              "seconds": round(time.time() - t0, 1)}},
                  f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(RAW, "ptr.json"))


def main():
    t0 = time.time()
    dns = json.load(open(os.path.join(RAW, "dns_records.json"), encoding="utf-8"))
    ips = sorted({ip for e in dns["records"].values()
                  for k in ("A", "AAAA") for ip in e.get(k, [])}
                 | set(dns.get("resolver_ips", {})))
    print(f"{len(ips)} IPs para consulta reversa", flush=True)

    out, done = {}, 0
    with ThreadPoolExecutor(32) as ex:
        for ip, name in ex.map(ptr, ips):
            if name:
                out[ip] = name
            done += 1
            if done % 200 == 0:
                print(f"   ... {done}/{len(ips)} ({len(out)} com PTR, "
                      f"{round(time.time() - t0)}s)", flush=True)
                save(out, len(ips), t0, partial=True)

    save(out, len(ips), t0, partial=False)
    print(f"OK  {len(out)}/{len(ips)} IPs com PTR ({round(time.time() - t0)}s)")


if __name__ == "__main__":
    main()
