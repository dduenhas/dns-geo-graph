# -*- coding: utf-8 -*-
"""01 — Coleta DNS real via DNS-over-HTTPS (Google + Cloudflare), sem chave de API.

Saída: data/raw/dns_records.json  (incremental, seguro contra interrupção)
"""
import json, os, sys, time, threading
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)
sys.path.insert(0, HERE)
from seeds import (ROOT_LETTERS, ROOT_OPERATORS, TLDS, SERVICES,
                   RESOLVER_IPS, RESOLVER_HOSTNAMES)

DOH = ["https://cloudflare-dns.com/dns-query", "https://dns.google/resolve"]
lock = threading.Lock()
cache = {}
records = {}          # fqdn -> {"A": [...], "AAAA": [...], "NS": [...], "PTR": [...]}
RAW_OUT = None


def doh(name, rtype, tries=3):
    key = (name.lower().rstrip("."), rtype)
    if key in cache:
        return cache[key]
    for t in range(tries):
        url = f"{DOH[t % 2]}?name={name}&type={rtype}"
        try:
            req = urllib.request.Request(url, headers={
                "accept": "application/dns-json",
                "User-Agent": "curl/8.4.0"})
            with urllib.request.urlopen(req, timeout=6) as r:
                data = json.loads(r.read().decode())
            ans = [a.get("data", "").rstrip(".") for a in data.get("Answer", [])
                   if a.get("type") == {"A": 1, "NS": 2, "PTR": 12, "AAAA": 28}[rtype]]
            ans = sorted(set(ans))
            cache[key] = ans
            return ans
        except Exception:
            time.sleep(0.3 * (t + 1))
    print(f"   ! falha: {name} {rtype}", flush=True)
    cache[key] = []
    return []


def rec(fqdn, rtype, values):
    with lock:
        e = records.setdefault(fqdn, {"A": [], "AAAA": [], "NS": [], "PTR": []})
        e[rtype] = sorted(set(e.get(rtype, [])) | set(values))


def resolve_host(host):
    a = doh(host, "A")
    aaaa = doh(host, "AAAA")
    rec(host, "A", a)
    rec(host, "AAAA", aaaa)
    return {"host": host, "A": a, "AAAA": aaaa}


def save(out, final=False):
    out["partial"] = not final
    # preserva chaves já acumuladas (ex.: "seconds" da coleta final)
    counts = dict(out.get("counts", {}))
    counts.update({"fqdn": len(records), "queries": len(cache),
                   "ips": len({ip for e in records.values()
                               for k in ("A", "AAAA") for ip in e.get(k, [])})})
    out["counts"] = counts
    tmp = os.path.join(RAW, "dns_records.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    os.replace(tmp, os.path.join(RAW, "dns_records.json"))


def main():
    t0 = time.time()

    # --- A) roots -----------------------------------------------------------
    root_hosts = [f"{l}.root-servers.net" for l in ROOT_LETTERS]
    print("== roots: A/AAAA", flush=True)
    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(resolve_host, root_hosts):
            print(f"   {r['host']:<24} v4={len(r['A'])} v6={len(r['AAAA'])}", flush=True)
    save(out := {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "DNS-over-HTTPS (cloudflare-dns.com primário, dns.google fallback)",
        "roots": {l: f"{l}.root-servers.net" for l in ROOT_LETTERS},
        "root_operators": ROOT_OPERATORS,
        "tld_ns": {}, "service_ns": {}, "resolver_ips": RESOLVER_IPS,
        "records": records,
    })

    # --- B) TLDs: NS -> hosts ----------------------------------------------
    print("== TLDs: NS", flush=True)
    tld_ns = {}
    with ThreadPoolExecutor(12) as ex:
        futs = {t: ex.submit(doh, t, "NS") for t in TLDS}
        for t, f in futs.items():
            ns = f.result()
            tld_ns[t] = ns
            rec(t, "NS", ns)
    out["tld_ns"] = tld_ns
    print(f"   {len(tld_ns)} TLDs, "
          f"{sum(len(v) for v in tld_ns.values())} nameservers", flush=True)
    save(out)
    ns_hosts = sorted({h for v in tld_ns.values() for h in v})

    # --- C) services: NS + apex A/AAAA -------------------------------------
    print("== services: NS + apex A/AAAA", flush=True)
    svc_ns = {}
    with ThreadPoolExecutor(12) as ex:
        futs = {d: ex.submit(doh, d, "NS") for d in SERVICES}
        for d, f in futs.items():
            svc_ns[d] = f.result()
            rec(d, "NS", svc_ns[d])
    out["service_ns"] = svc_ns
    print(f"   {len(svc_ns)} domínios, "
          f"{sum(len(v) for v in svc_ns.values())} nameservers", flush=True)
    ns_hosts += sorted({h for v in svc_ns.values() for h in v})
    save(out)

    apex = sorted(SERVICES) + RESOLVER_HOSTNAMES
    print(f"== apex A/AAAA ({len(apex)} hostnames)", flush=True)
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(resolve_host, apex))
    save(out)

    # --- resolve every nameserver host to IPs ------------------------------
    ns_hosts = sorted(set(ns_hosts))
    print(f"== resolvendo {len(ns_hosts)} hostnames de nameserver", flush=True)
    done = 0
    with ThreadPoolExecutor(16) as ex:
        for r in ex.map(resolve_host, ns_hosts):
            done += 1
            if done % 40 == 0:
                print(f"   ... {done}/{len(ns_hosts)} ({len(cache)} consultas, "
                      f"{round(time.time() - t0)}s)", flush=True)
    save(out)

    # --- PTR: já vem de ip-api (campo "reverse") no passo 02 ---------------
    ips = sorted({ip for e in records.values() for k in ("A", "AAAA") for ip in e[k]})
    print(f"== {len(ips)} IPs únicos (PTR será obtido via ip-api no passo 02)", flush=True)

    out["counts"]["seconds"] = round(time.time() - t0, 1)
    save(out, final=True)
    print(f"\nOK  {len(records)} FQDNs | {len(ips)} IPs únicos | {len(cache)} consultas "
          f"| {out['counts']['seconds']}s -> data/raw/dns_records.json", flush=True)


if __name__ == "__main__":
    main()
