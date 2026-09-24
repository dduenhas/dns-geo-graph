---
tipo: teoria
tags: [teoria/anycast, moc]
---
# Anycast e geolocalização de IP

> [!warning] O dado geográfico deste projeto é *visto da coleta*, não do cadastro
> A coleta partiu de um único ponto (notebook do usuário, Brasil). Para endereços
> **anycast** (raiz, resolvedores públicos, CDNs), o PoP que responde é o mais próximo
> **daquele ponto**. O campo `lat/lon` do ip-api descreve o PoP que atendeu, não todos
> os PoPs do endereço.

Consequências práticas:

- `1.1.1.1` aparece aqui com uma cidade (a que atendeu) — na prática são ~300 PoPs.
- Endereços marcados `hosting: sim` (893 de 1388 neste
  dataset) revelam infraestrutura de datacenter/cloud, não residencial.
- PTR (`reverse`) é a melhor pista de função: `dns.google`, `ns1.uol.com.br`,
  `a.root-servers.net` dizem o que o endereço *faz*.

## Como o grafos lida com isso

O nó do IP guarda **um** ponto de presença, e o frontmatter traz `lat`/`lon` para o
filtro do Graph View; a aresta `ponto de presença em` liga o endereço à cidade. Na fase
three.js (ver [[Roadmap — visualização three.js]]) a mesma escolha aparece como uma
esfera com os nós geo-posicionados e os nós anycast em anéis concêntricos.
