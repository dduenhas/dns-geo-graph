# -*- coding: utf-8 -*-
"""
Sementes (seeds) do grafo DNS -> GEO.

Três camadas de entrada:
  A) ROOTS      : os 13 servidores raiz (a-m.root-servers.net) + operadores
  B) TLDS       : nameservers autoritativos de ccTLDs e gTLDs (descobertos via DoH/NS)
  C) SERVICES   : nameservers + endpoints de serviços reais (globais e brasileiros)
  D) RESOLVERS  : IPs reais de resolvedores públicos (anycast) + seus hostnames

Nada aqui é inventado: todo dado final vem de consulta DNS ao vivo (DNS-over-HTTPS)
e de geolocalização/ASN via ip-api.com.
"""

ROOT_LETTERS = list("abcdefghijklm")

ROOT_OPERATORS = {
    "a": ("Verisign, Inc.", "US", "VeriSign Naming and Directory Services"),
    "b": ("Information Sciences Institute (USC-ISI)", "US", "USC/ISI"),
    "c": ("Cogent Communications", "US", "PSINet/Cogent"),
    "d": ("University of Maryland (UMD)", "US", "UMD"),
    "e": ("NASA Ames Research Center", "US", "NASA"),
    "f": ("Internet Systems Consortium (ISC)", "US", "ISC"),
    "g": ("U.S. Department of Defense (Network Information Center)", "US", "DoD NIC"),
    "h": ("U.S. Army Research Lab", "US", "US Army"),
    "i": ("Netnod", "SE", "Netnod (ex-Autonomica)"),
    "j": ("Verisign, Inc.", "US", "Verisign"),
    "k": ("RIPE NCC", "NL", "RIPE NCC"),
    "l": ("ICANN", "US", "ICANN"),
    "m": ("WIDE Project", "JP", "WIDE Project"),
}

# ---- B) TLDs: pedimos NS de cada um -----------------------------------------
TLDS = [
    # ccTLDs
    "br", "uk", "de", "fr", "nl", "jp", "cn", "ru", "in", "au", "ca", "mx", "ar",
    "pt", "es", "it", "se", "ch", "pl", "za", "ng", "sg", "kr", "id", "tr", "be",
    "at", "dk", "no", "fi", "ie", "nz", "il", "ae", "sa", "co", "cl", "pe", "uy",
    "ec", "py", "bo", "ve", "cz", "ro", "gr", "hu", "ua", "ke", "eg", "ma",
    # gTLDs
    "com", "org", "net", "edu", "gov", "info", "biz", "io", "dev", "app", "xyz",
    "ai", "cloud", "tech", "online", "site", "store", "blog", "shop", "tv", "cc",
]

# ---- C) Serviços reais: pedimos NS + A/AAAA do apex --------------------------
SERVICES = {
    # globais
    "google.com": ("Google", "US"),
    "cloudflare.com": ("Cloudflare", "US"),
    "amazon.com": ("Amazon", "US"),
    "aws.amazon.com": ("Amazon Web Services", "US"),
    "microsoft.com": ("Microsoft", "US"),
    "apple.com": ("Apple", "US"),
    "meta.com": ("Meta", "US"),
    "x.com": ("X Corp.", "US"),
    "github.com": ("GitHub", "US"),
    "gitlab.com": ("GitLab", "NL"),
    "wikipedia.org": ("Wikimedia Foundation", "US"),
    "wikimedia.org": ("Wikimedia Foundation", "US"),
    "mozilla.org": ("Mozilla", "US"),
    "netflix.com": ("Netflix", "US"),
    "spotify.com": ("Spotify", "SE"),
    "telegram.org": ("Telegram", "AE"),
    "tiktok.com": ("ByteDance", "SG"),
    "zoom.us": ("Zoom", "US"),
    "openai.com": ("OpenAI", "US"),
    "anthropic.com": ("Anthropic", "US"),
    "huggingface.co": ("Hugging Face", "US"),
    "nvidia.com": ("NVIDIA", "US"),
    "oracle.com": ("Oracle", "US"),
    "redhat.com": ("Red Hat", "US"),
    "debian.org": ("Debian Project", "US"),
    "ubuntu.com": ("Canonical", "GB"),
    "python.org": ("Python Software Foundation", "US"),
    "nodejs.org": ("OpenJS Foundation", "US"),
    "npmjs.com": ("npm / GitHub", "US"),
    "docker.com": ("Docker", "US"),
    "kubernetes.io": ("CNCF", "US"),
    "vercel.com": ("Vercel", "US"),
    "netlify.com": ("Netlify", "US"),
    "fastly.com": ("Fastly", "US"),
    "akamai.com": ("Akamai", "US"),
    "bing.com": ("Microsoft", "US"),
    "duckduckgo.com": ("DuckDuckGo", "US"),
    "proton.me": ("Proton AG", "CH"),
    "signal.org": ("Signal Foundation", "US"),
    # brasil
    "gov.br": ("Governo Federal do Brasil", "BR"),
    "uol.com.br": ("UOL", "BR"),
    "globo.com": ("Grupo Globo", "BR"),
    "mercadolivre.com.br": ("Mercado Livre", "BR"),
    "bradesco.com.br": ("Bradesco", "BR"),
    "itau.com.br": ("Itaú Unibanco", "BR"),
    "nubank.com.br": ("Nubank", "BR"),
    "petrobras.com.br": ("Petrobras", "BR"),
    "usp.br": ("Universidade de São Paulo", "BR"),
    "unicamp.br": ("Unicamp", "BR"),
    "ufrn.br": ("Universidade Federal do RN", "BR"),
    "ifrn.edu.br": ("IFRN", "BR"),
    "serpro.gov.br": ("SERPRO", "BR"),
    "dns.br": ("Registro.br / NIC.br (autoritativo .br)", "BR"),
    "registro.br": ("Registro.br / NIC.br", "BR"),
    "nic.br": ("NIC.br", "BR"),
    "cgi.br": ("CGI.br", "BR"),
    "rnp.br": ("RNP — Rede Nacional de Pesquisa", "BR"),
}

# ---- D) Resolvedores públicos: IPs anycast reais ----------------------------
RESOLVER_IPS = {
    "1.1.1.1": ("Cloudflare Public DNS (primário)", "Cloudflare"),
    "1.0.0.1": ("Cloudflare Public DNS (secundário)", "Cloudflare"),
    "2606:4700:4700::1111": ("Cloudflare Public DNS v6", "Cloudflare"),
    "8.8.8.8": ("Google Public DNS (primário)", "Google"),
    "8.8.4.4": ("Google Public DNS (secundário)", "Google"),
    "2001:4860:4860::8888": ("Google Public DNS v6", "Google"),
    "9.9.9.9": ("Quad9 (primário, filtro de ameaças)", "Quad9 / IBM / PCH"),
    "149.112.112.112": ("Quad9 (secundário)", "Quad9 / IBM / PCH"),
    "2620:fe::fe": ("Quad9 v6", "Quad9 / IBM / PCH"),
    "208.67.222.222": ("Cisco OpenDNS (primário)", "Cisco"),
    "208.67.220.220": ("Cisco OpenDNS (secundário)", "Cisco"),
    "2620:119:35::35": ("Cisco OpenDNS v6", "Cisco"),
    "94.140.14.14": ("AdGuard DNS (primário)", "AdGuard"),
    "94.140.15.15": ("AdGuard DNS (secundário)", "AdGuard"),
    "2a00:5a60::ad1:0ff": ("AdGuard DNS v6", "AdGuard"),
    "185.228.168.9": ("CleanBrowsing (família)", "CleanBrowsing"),
    "76.76.2.0": ("Control D (primário)", "Control D"),
    "76.76.10.0": ("Control D (secundário)", "Control D"),
    "77.88.8.8": ("Yandex DNS (básico)", "Yandex"),
    "64.6.64.6": ("Verisign Public DNS (primário)", "Verisign"),
    "64.6.65.6": ("Verisign Public DNS (secundário)", "Verisign"),
    "156.154.70.1": ("Neustar/UltraDNS (primário)", "Neustar"),
    "84.200.69.80": ("DNS.WATCH (primário)", "DNS.WATCH"),
    "216.146.35.35": ("Oracle Dyn (primário)", "Oracle"),
    "8.26.56.26": ("Comodo Secure DNS (primário)", "Comodo"),
    "4.2.2.1": ("Level3 / Lumen (primário)", "Lumen"),
    "205.171.3.65": ("CenturyLink/Qwest (primário)", "Lumen"),
    "193.110.81.0": ("dns0.eu (primário)", "dns0.eu"),
    "37.235.1.174": ("FreeDNS / afraid.org", "FreeDNS"),
    "199.85.126.10": ("Norton ConnectSafe", "Gen Digital"),
    "198.101.242.72": ("OpenNIC / resolvedor comunitário", "OpenNIC"),
}

RESOLVER_HOSTNAMES = [
    "one.one.one.one", "dns.google", "dns.quad9.net", "opendns.com",
    "dns.adguard-dns.com", "dns0.eu", "cleanbrowsing.org", "controld.com",
]
