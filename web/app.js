/* ==========================================================================
   Onde a internet mora — grafo 3D de infraestrutura de internet
   Dados: data/graph_core.json (posições x/y/z pré-calculadas) + notes_map.json
   Eixo Y = hierarquia (camada 1..9) · X/Z = projeção equiretangular de lat/lon
   ========================================================================== */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

/* ── constantes de cena ────────────────────────────────────────────────── */
const MAP_Y = -8.9;                       // plano da Terra, abaixo de todas as camadas
const MAP_W = 32.68, MAP_D = 16.33;       // extensão da projeção equiretangular
const AC = 0x00b4d8, AC2 = 0x48cae4;

const KIND = {
  hub:           { label: 'hubs do grafo',       color: 0xffffff, r: 0.24 },
  root:          { label: 'servidor raiz',       color: 0xff4d6d, r: 0.30 },
  tld:           { label: 'zona de topo',        color: 0xff8c42, r: 0.18 },
  service:       { label: 'domínio / serviço',   color: 0xffd166, r: 0.16 },
  ns:            { label: 'nameserver',          color: 0x2ec4b6, r: 0.10 },
  ptr:           { label: 'nome reverso (PTR)',  color: 0x1d9e94, r: 0.072 },
  resolver_host: { label: 'host de resolvedor',  color: 0x2ec4b6, r: 0.11 },
  resolver_org:  { label: 'resolvedor público',  color: 0x06d6a0, r: 0.20 },
  ip:            { label: 'endereço IP',         color: 0x00b4d8, r: 0.10 },
  asn:           { label: 'rede (ASN)',          color: 0xb388ff, r: 0.18 },
  city:          { label: 'cidade / PoP',        color: 0xff69b4, r: 0.20 },
  country:       { label: 'país',                color: 0xe8a2ff, r: 0.26 },
  continent:     { label: 'continente',          color: 0xc9ada7, r: 0.32 },
};

const LAYERS = [
  { i: 0, y: -6.80, name: 'hubs do grafo',        kinds: ['hub'] },
  { i: 1, y: -5.10, name: 'servidores raiz',      kinds: ['root'] },
  { i: 2, y: -3.40, name: 'zonas de topo',        kinds: ['tld'] },
  { i: 3, y: -1.70, name: 'domínios e serviços',  kinds: ['service'] },
  { i: 4, y: 0.00, name: 'nameservers e PTR',    kinds: ['ns', 'ptr', 'resolver_host', 'resolver_org'] },
  { i: 5, y: 1.70, name: 'endereços IP',         kinds: ['ip'] },
  { i: 6, y: 3.40, name: 'ASN e PoPs',           kinds: ['asn', 'city'] },
  { i: 7, y: 5.10, name: 'países',               kinds: ['country'] },
  { i: 8, y: 6.80, name: 'continentes',          kinds: ['continent'] },
];

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmt = (n) => n.toLocaleString('pt-BR');

/* ── dados ─────────────────────────────────────────────────────────────── */
const [core, notes] = await Promise.all([
  fetch('./data/graph_core.json').then((r) => r.json()),
  fetch('./data/notes_map.json').then((r) => r.json()).catch(() => ({ notes: {} })),
]);
const N = core.nodes, E = core.edges;
const noteOf = notes.notes || {};
const PT = notes.countries_pt || {};
const deepLink = notes.note_deep_link || '';
const ptCountry = (cc, fallback) => (cc && PT[cc]) || fallback || '';

const byId = new Map();
for (const n of N) {
  n.pos = new THREE.Vector3(n.x, n.y, n.z);
  n.note = noteOf[n.id]?.note || null;
  n.grau = noteOf[n.id]?.grau || 0;
  byId.set(n.id, n);
}

/* adjacência (grafo não direcionado para navegação) */
const adj = new Map();
const deg = new Map();
for (const e of E) {
  if (!byId.has(e.source) || !byId.has(e.target)) continue;
  if (!adj.has(e.source)) adj.set(e.source, []);
  if (!adj.has(e.target)) adj.set(e.target, []);
  adj.get(e.source).push({ id: e.target, type: e.type });
  adj.get(e.target).push({ id: e.source, type: e.type });
  deg.set(e.source, (deg.get(e.source) || 0) + 1);
  deg.set(e.target, (deg.get(e.target) || 0) + 1);
}

const stats = {
  nodes: N.length, edges: E.length,
  byKind: {}, byLayer: {},
  ips: N.filter((n) => n.kind === 'ip').length,
  countries: N.filter((n) => n.kind === 'country').length,
  cities: N.filter((n) => n.kind === 'city').length,
  asns: N.filter((n) => n.kind === 'asn').length,
  ptr: N.filter((n) => n.kind === 'ip' && n.ptr).length,
};
for (const n of N) {
  stats.byKind[n.kind] = (stats.byKind[n.kind] || 0) + 1;
  stats.byLayer[n.layer] = (stats.byLayer[n.layer] || 0) + 1;
}

/* ── cena ──────────────────────────────────────────────────────────────── */
const canvas = document.querySelector('#scene');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.setClearColor(0x111114, 1);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x111114, 0.0052);

const bbox = new THREE.Box3().setFromPoints(N.map((n) => n.pos));
const center = bbox.getCenter(new THREE.Vector3());
const size = bbox.getSize(new THREE.Vector3());
const R = Math.max(size.x, size.z) * 0.55;
const home = center.clone().add(new THREE.Vector3(0, -R * 0.30, 0));  // mira entre o grafo e a Terra

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.5, 600);
camera.position.copy(center).add(new THREE.Vector3(0, R * 0.80, R * 1.52));

const controls = new OrbitControls(camera, canvas);
controls.target.copy(center);
controls.enableDamping = true;
controls.dampingFactor = 0.055;
controls.rotateSpeed = 0.55;
controls.zoomSpeed = 0.75;
controls.panSpeed = 0.6;
controls.minDistance = 3;
controls.maxDistance = R * 6;
controls.autoRotateSpeed = 0.28;

scene.add(new THREE.AmbientLight(0xffffff, 1));

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.14, 0.30, 0.90);
composer.addPass(bloom);
composer.addPass(new OutputPass());
let useGlow = true;

/* ── Terra: continentes em ciano (relevo) + oceano escuro ──────────────── */
const texLoader = new THREE.TextureLoader();
const landMask = texLoader.load('./assets/earth-topology.png');
const waterMask = texLoader.load('./assets/earth-water.png');

const earth = new THREE.Group();
const ocean = new THREE.Mesh(
  new THREE.PlaneGeometry(MAP_W, MAP_D, 1, 1),
  new THREE.MeshBasicMaterial({
    color: 0x08303d,
    alphaMap: waterMask,
    transparent: true,
    opacity: 0.9,
    depthWrite: false,
  }),
);
const land = new THREE.Mesh(
  new THREE.PlaneGeometry(MAP_W, MAP_D, 1, 1),
  new THREE.MeshBasicMaterial({
    color: 0x37a3c0,
    alphaMap: landMask,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
  }),
);
for (const m of [ocean, land]) m.rotation.x = -Math.PI / 2;
land.position.y = 0.04;
earth.add(ocean, land);
earth.position.set(0, MAP_Y, 0);
scene.add(earth);

const mapFrame = new THREE.LineSegments(
  new THREE.EdgesGeometry(new THREE.PlaneGeometry(MAP_W + 0.4, MAP_D + 0.4)),
  new THREE.LineBasicMaterial({ color: AC, transparent: true, opacity: 0.22 }),
);
mapFrame.rotation.x = -Math.PI / 2;
mapFrame.position.set(0, MAP_Y + 0.01, 0);
scene.add(mapFrame);

/* grid de cada camada */
function grid(w, d, nx, nz, color, opacity) {
  const pts = [];
  for (let i = 0; i <= nx; i++) {
    const x = -w / 2 + (w * i) / nx;
    pts.push(x, 0, -d / 2, x, 0, d / 2);
  }
  for (let j = 0; j <= nz; j++) {
    const z = -d / 2 + (d * j) / nz;
    pts.push(-w / 2, 0, z, w / 2, 0, z);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  return new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    color, transparent: true, opacity, depthWrite: false,
  }));
}

const grids = [];
for (const L of LAYERS) {
  const g = grid(MAP_W + 3.6, MAP_D + 2.4, 8, 4, 0xffffff, L.i === 5 ? 0.075 : 0.042);
  g.position.y = L.y;
  g.userData.layer = L.i;
  scene.add(g);
  grids.push(g);
}

/* ── nós (um InstancedMesh por tipo) ───────────────────────────────────── */
const geo = new THREE.SphereGeometry(1, 12, 9);
const groups = new Map();               // kind -> { ids, mesh, material }
for (const [k, meta] of Object.entries(KIND)) {
  const ids = N.filter((n) => n.kind === k).map((n) => n.id);
  if (!ids.length) continue;
  const material = new THREE.MeshBasicMaterial({
    color: meta.color, transparent: true, opacity: 1, depthWrite: false,
  });
  const mesh = new THREE.InstancedMesh(geo, material, ids.length);
  mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  mesh.userData.kind = k;
  mesh.userData.ids = ids;
  const m = new THREE.Matrix4();
  ids.forEach((id, i) => {
    const n = byId.get(id);
    const s = meta.r * (1 + 0.035 * Math.min(12, Math.sqrt(n.grau)));
    const p = n.pos;
    m.makeScale(s, s, s);
    m.setPosition(p.x, p.y, p.z);
    mesh.setMatrixAt(i, m);
  });
  mesh.instanceMatrix.needsUpdate = true;
  mesh.frustumCulled = false;
  mesh.userData.delay = LAYERS.find((L) => L.kinds.includes(k))?.i * 0.16 || 0;
  scene.add(mesh);
  groups.set(k, { ids, mesh, material, meta });
}
const meshes = [...groups.values()].map((g) => g.mesh);
const meshesAfterIntro = meshes.slice().sort((a, b) => a.userData.delay - b.userData.delay);

/* ── arestas em duas famílias: esqueleto (hierarquia) + malha densa ─────── */
const DENSE_TYPES = new Set(['geolocalizado em', 'ponto de presença em', 'anunciado por', 'PTR']);
var edgeSets = { estrutura: null, densa: null };
{
  const c = new THREE.Color();
  const build = (list, opacity) => {
    const pos = new Float32Array(list.length * 6);
    const col = new Float32Array(list.length * 6);
    list.forEach((e, i) => {
      const a = byId.get(e.source).pos, b = byId.get(e.target).pos;
      pos.set([a.x, a.y, a.z, b.x, b.y, b.z], i * 6);
      c.setHex(KIND[byId.get(e.source).kind].color);
      col.set([c.r, c.g, c.b], i * 6);
      c.setHex(KIND[byId.get(e.target).kind].color);
      col.set([c.r, c.g, c.b], i * 6 + 3);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const m = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
      vertexColors: true, transparent: true, opacity, depthWrite: false,
    }));
    m.frustumCulled = false;
    scene.add(m);
    return m;
  };
  edgeSets.estrutura = build(E.filter((e) => !DENSE_TYPES.has(e.type)), 0.16);
  edgeSets.densa = build(E.filter((e) => DENSE_TYPES.has(e.type)), 0.05);
}
var edgesMesh = edgeSets.estrutura;

/* ── linhas de pouso: nó geográfico -> Terra ───────────────────────────── */
{
  const geoNodes = N.filter((n) => n.lat !== null && n.lat !== undefined);
  const pos = new Float32Array(geoNodes.length * 6);
  geoNodes.forEach((n, i) => {
    pos.set([n.x, n.y, n.z, n.x, MAP_Y + 0.06, n.z], i * 6);
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  var dropMesh = new THREE.LineSegments(g, new THREE.LineBasicMaterial({
    color: AC, transparent: true, opacity: 0.1, depthWrite: false,
  }));
  dropMesh.frustumCulled = false;
  scene.add(dropMesh);
}

/* ── subgrafo destacado (hover / seleção) ──────────────────────────────── */
function makeHL(color, opacity, widthIgnored) {
  const g = new THREE.BufferGeometry();
  const m = new THREE.LineBasicMaterial({
    color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false,
  });
  const l = new THREE.LineSegments(g, m);
  l.frustumCulled = false;
  l.visible = false;
  scene.add(l);
  return l;
}
const hoverHL = makeHL(0xffffff, 0.5);
const selHL = makeHL(AC2, 0.95);
const marker = new THREE.Mesh(
  new THREE.SphereGeometry(1, 16, 12),
  new THREE.MeshBasicMaterial({ color: AC2, transparent: true, opacity: 0.9, depthWrite: false }),
);
marker.visible = false;
scene.add(marker);

function fillHL(line, id) {
  const nb = adj.get(id) || [];
  if (!nb.length) { line.visible = false; return; }
  const p = byId.get(id).pos;
  const arr = new Float32Array(nb.length * 6);
  nb.forEach((n, i) => {
    const q = byId.get(n.id).pos;
    arr.set([p.x, p.y, p.z, q.x, q.y, q.z], i * 6);
  });
  line.geometry.dispose();
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
  line.geometry = g;
  line.visible = true;
}

/* ── UI: números, trilho, legenda ──────────────────────────────────────── */
const LAYER_DESC = {
  0: 'índice e estrutura do grafo',
  1: 'os 13 servidores raiz anycast que sustentam o DNS',
  2: 'zonas de topo (.br, .com, .org…)',
  3: 'domínios e serviços observados',
  4: 'nameservers autoritativos, nomes reversos e resolvedores públicos',
  5: 'endereços IP vistos pela coleta (IPv4 + IPv6)',
  6: 'sistemas autônomos e pontos de presença',
  7: 'países onde esses endereços respondem',
  8: 'continentes',
};

document.querySelector('#eyebrow-counts').textContent =
  `${fmt(stats.ips)} endereços IP · ${fmt(stats.countries)} países · ${fmt(stats.asns)} redes · ${fmt(stats.ptr)} PTRs`;

const figures = [
  ['nós', fmt(stats.nodes)],
  ['arestas', fmt(stats.edges)],
  ['endereços IP', fmt(stats.ips)],
  ['PoPs', fmt(stats.cities)],
  ['países', fmt(stats.countries)],
  ['ASNs', fmt(stats.asns)],
];
document.querySelector('#figures').innerHTML = figures
  .map(([k, v]) => `<li><span class="v">${v}</span><span class="k">${k}</span></li>`).join('');

/* trilho */
const railList = document.querySelector('#rail-list');
railList.innerHTML = LAYERS.map((L) => {
  const n = L.kinds.reduce((a, k) => a + (stats.byKind[k] || 0), 0);
  return `<li><button type="button" data-layer="${L.i}" aria-pressed="false">
    <span class="idx">${String(L.i + 1).padStart(2, '0')}</span>
    <span class="name">${L.name}</span>
    <span class="n">${fmt(n)}</span>
    <span class="bar" style="width:${Math.max(3, (n / stats.nodes) * 100).toFixed(1)}%"></span>
  </button></li>`;
}).join('');

/* legenda */
const legendOrder = ['root', 'tld', 'service', 'ns', 'ip', 'asn', 'city', 'country', 'continent'];
document.querySelector('#legend').innerHTML = legendOrder
  .filter((k) => stats.byKind[k])
  .map((k) => `<li data-kind="${k}" aria-pressed="false" role="button" tabindex="0">
      <i style="background:#${KIND[k].color.toString(16).padStart(6, '0')}"></i>
      ${KIND[k].label} <span class="n">${fmt(stats.byKind[k])}</span></li>`).join('');

/* rótulos dos nós mais conectados (≤ 42, os hubs do grafo) */
const LABEL_MIN = 20;
const labelled = N.filter((n) => (n.grau || 0) >= LABEL_MIN)
  .sort((a, b) => b.grau - a.grau).slice(0, 42);
const nodeLabels = labelled.map((n) => {
  const d = document.createElement('div');
  d.className = 'node-label';
  d.setAttribute('aria-hidden', 'true');
  const nm = n.id.length > 26 ? n.id.slice(0, 25) + '…' : n.id;
  d.innerHTML = `<i style="background:#${KIND[n.kind].color.toString(16).padStart(6, '0')}"></i>${esc(nm)}`;
  document.body.appendChild(d);
  return { pos: n.pos, kind: n.kind, el: d };
});

/* ── estado de foco / seleção ──────────────────────────────────────────── */
let focusLayer = null;
let selected = null;
let hovered = null;

function applyFocus() {
  const kinds = focusLayer === null
    ? new Set(Object.keys(KIND))
    : new Set(LAYERS[focusLayer].kinds);
  const dim = selected ? 0.03 : (focusLayer !== null ? 0.05 : 0.10);
  for (const [k, g] of groups) {
    g.material.opacity = kinds.has(k) ? 1 : dim;
  }
  applyEdges();
  if (dropMesh) dropMesh.material.opacity = (focusLayer !== null || selected) ? 0.035 : 0.07;
  railList.querySelectorAll('button').forEach((b) => {
    b.setAttribute('aria-pressed', String(Number(b.dataset.layer) === focusLayer));
  });
}

function setStatus() {
  const s = document.querySelector('#status');
  if (selected) {
    s.textContent = `nó: ${selected} · ${KIND[byId.get(selected).kind].label}`;
  } else if (focusLayer !== null) {
    const L = LAYERS[focusLayer];
    const n = L.kinds.reduce((a, k) => a + (stats.byKind[k] || 0), 0);
    s.textContent = `camada ${String(L.i + 1).padStart(2, '0')} — ${LAYER_DESC[L.i]} · ${fmt(n)} nós`;
  } else {
    s.textContent = 'foco: grafo inteiro';
  }
}

/* ── painel do nó ──────────────────────────────────────────────────────── */
const panel = document.querySelector('#panel');

function pathToRoot(id) {
  const rootId = 'Zona Raiz (.)';
  if (!byId.has(rootId) || id === rootId) return [];
  const prev = new Map([[id, null]]);
  const q = [id];
  while (q.length) {
    const cur = q.shift();
    if (cur === rootId) {
      const out = [];
      let c = cur;
      while (c) { out.push(c); c = prev.get(c); }
      return out.reverse();
    }
    for (const nb of adj.get(cur) || []) {
      if (!prev.has(nb.id)) { prev.set(nb.id, cur); q.push(nb.id); }
    }
    if (prev.size > 4000) break;
  }
  return [];
}

function neighborsByType(id) {
  const m = new Map();
  for (const nb of adj.get(id) || []) {
    if (!m.has(nb.type)) m.set(nb.type, []);
    m.get(nb.type).push(nb.id);
  }
  return m;
}

function openPanel(id) {
  const n = byId.get(id);
  const meta = KIND[n.kind];
  const hex = `#${meta.color.toString(16).padStart(6, '0')}`;
  const nb = adj.get(id) || [];
  const nbt = neighborsByType(id);
  const path = pathToRoot(id);
  const geo = n.lat !== null && n.lat !== undefined
    ? `${n.lat.toFixed(3)}, ${n.lon.toFixed(3)}` : '—';

  const rows = [
    ['camada', `${String(n.layer + 1).padStart(2, '0')} — ${LAYERS[n.layer].name}`],
    ['tipo', meta.label],
    ['grau', fmt(n.grau)],
    n.ptr ? ['PTR', n.ptr] : null,
    n.asn ? ['ASN', n.asn] : null,
    n.resolver ? ['papel', 'resolvedor público'] : null,
    n.country ? ['país', ptCountry(n.cc, n.country)] : null,
    n.city ? ['cidade / PoP', n.city] : null,
    (n.lat !== null && n.lat !== undefined) ? ['coordenadas', geo] : null,
  ].filter(Boolean);

  const chips = [...nbt.entries()]
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, 6)
    .map(([type, ids]) => `<h4>${esc(type)} · ${fmt(ids.length)}</h4>
      <div class="chips">${ids.slice(0, 12).map((i) =>
        `<button class="chip" data-go="${esc(i)}" type="button">${esc(i)}</button>`).join('')}
        ${ids.length > 12 ? `<span class="chip"><span class="t">+${ids.length - 12}</span></span>` : ''}
      </div>`).join('');

  panel.innerHTML = `
    <span class="badge"><i style="background:${hex};color:${hex}"></i>${meta.label}</span>
    <h3>${esc(id)}</h3>
    <p class="sub">${n.note ? esc(n.note) + ' · ' : ''}${n.note ? esc(noteOf[id].folder) : 'sem nota'}</p>
    <dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>
    ${path.length > 2 ? `<h4>caminho até a zona raiz</h4>
      <div class="path">${path.map((p, i) =>
        `<button class="chip" data-go="${esc(p)}" type="button">${esc(p)}</button>` +
        (i < path.length - 1 ? '<span class="sep">→</span>' : '')).join('')}</div>` : ''}
    ${chips || '<h4>sem arestas</h4>'}
    <div class="actions">
      ${n.note ? `<a class="btn" href="${esc(deepLink + encodeURIComponent(n.note))}">Abrir no Obsidian</a>` : ''}
      <button class="btn ghost" type="button" id="copy-id">Copiar ID</button>
    </div>`;

  panel.hidden = false;
  panel.querySelector('#copy-id')?.addEventListener('click', async (ev) => {
    try { await navigator.clipboard.writeText(id); ev.target.textContent = 'copiado'; }
    catch { ev.target.textContent = 'copie manualmente'; }
  });
  panel.querySelectorAll('[data-go]').forEach((b) => {
    b.addEventListener('click', () => select(b.dataset.go, true));
  });
}

function closePanel() {
  panel.hidden = true;
  panel.innerHTML = '';
}

/* ── seleção / foco / voo de câmera ────────────────────────────────────── */
let camTween = null;

function flyTo(p, dist, dur = 950) {
  const dir = camera.position.clone().sub(controls.target);
  if (dir.lengthSq() < 1e-6) dir.set(0, 0.9, 1.4);
  dir.normalize().setY(Math.max(0.18, dir.y));
  camTween = {
    t: 0, dur,
    c0: camera.position.clone(), c1: p.clone().add(dir.normalize().multiplyScalar(dist)),
    t0: controls.target.clone(), t1: p.clone(),
  };
}

function select(id, fly = false) {
  if (!byId.has(id)) return;
  selected = id;
  const n = byId.get(id);
  openPanel(id);
  fillHL(selHL, id);
  marker.position.copy(n.pos);
  marker.scale.setScalar(Math.max(0.5, KIND[n.kind].r * 2.4));
  marker.visible = true;
  applyFocus();
  setStatus();
  if (fly) flyTo(n.pos, Math.max(6, R * 0.55), 900);
}

function clearSelection() {
  selected = null;
  selHL.visible = false;
  marker.visible = false;
  closePanel();
  applyFocus();
  setStatus();
}

function setFocusLayer(i) {
  focusLayer = (i === null || focusLayer === i) ? null : i;
  applyFocus();
  setStatus();
  if (focusLayer === null) {
    flyTo(home, R * 2.15, 900);
  } else {
    const pts = N.filter((n) => LAYERS[focusLayer].kinds.includes(n.kind)).map((n) => n.pos);
    const b = new THREE.Box3().setFromPoints(pts);
    const c = b.getCenter(new THREE.Vector3());
    const s = b.getSize(new THREE.Vector3());
    c.y += 0;
    flyTo(c, Math.max(9, Math.max(s.x, s.z) * 0.95), 950);
  }
}

railList.addEventListener('click', (e) => {
  const b = e.target.closest('button[data-layer]');
  if (b) setFocusLayer(Number(b.dataset.layer));
});
document.querySelector('#rail-reset').addEventListener('click', () => {
  focusLayer = null; clearSelection(); flyTo(home, R * 2.15, 900); applyFocus(); setStatus();
});
document.querySelector('#legend').addEventListener('click', (e) => {
  const li = e.target.closest('li[data-kind]');
  if (!li) return;
  const k = li.dataset.kind;
  const li2 = [...li.parentNode.children].find((x) => x.dataset.kind === k);
  const wasOn = li2.getAttribute('aria-pressed') === 'true';
  [...li.parentNode.children].forEach((x) => x.setAttribute('aria-pressed', 'false'));
  if (wasOn) { applyFocus(); return; }
  li2.setAttribute('aria-pressed', 'true');
  for (const [kk, g] of groups) g.material.opacity = kk === k ? 1 : 0.08;
  edgeSets.estrutura.material.opacity = 0.06;
  edgeSets.densa.material.opacity = 0.02;
  const L = LAYERS.find((l) => l.kinds.includes(k));
  flyTo(new THREE.Vector3(0, L.y, 0), R * 1.2, 850);
});

/* ── busca ─────────────────────────────────────────────────────────────── */
const indexList = N.map((n) => ({
  n,
  key: [n.id, n.note || '', n.asn, n.city, ptCountry(n.cc, n.country), n.ptr,
        KIND[n.kind].label].join(' ').toLowerCase(),
}));
const q = document.querySelector('#q');
const results = document.querySelector('#results');
let resultItems = [];
let activeResult = -1;

function renderResults(list) {
  resultItems = list.slice(0, 40);
  activeResult = resultItems.length ? 0 : -1;
  results.hidden = !resultItems.length;
  results.innerHTML = resultItems.map(({ n }, i) => `
    <li><button type="button" data-i="${i}" data-active="${i === activeResult}">
      <span class="k">${esc(KIND[n.kind].label)}</span>
      <span class="t">${esc(n.note || n.id)}</span>
    </button></li>`).join('');
  results.querySelectorAll('button').forEach((b) => {
    b.addEventListener('click', () => pick(Number(b.dataset.i)));
  });
}

function pick(i) {
  const item = resultItems[i];
  if (!item) return;
  results.hidden = true;
  q.value = item.n.note || item.n.id;
  select(item.n.id, true);
}

q.addEventListener('input', () => {
  const v = q.value.trim().toLowerCase();
  if (v.length < 2) { results.hidden = true; resultItems = []; return; }
  const terms = v.split(/\s+/);
  renderResults(indexList.filter((it) => terms.every((t) => it.key.includes(t))));
});
q.addEventListener('keydown', (e) => {
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    if (!resultItems.length) return;
    e.preventDefault();
    activeResult = (activeResult + (e.key === 'ArrowDown' ? 1 : -1) + resultItems.length) % resultItems.length;
    results.querySelectorAll('button').forEach((b, i) => b.dataset.active = String(i === activeResult));
  } else if (e.key === 'Enter') {
    e.preventDefault();
    pick(Math.max(0, activeResult));
  } else if (e.key === 'Escape') {
    results.hidden = true; q.blur();
  }
});

/* ── toggles ───────────────────────────────────────────────────────────── */
let labelsOn = true;
let edgeMode = 0;                     // 0 = todas · 1 = só esqueleto · 2 = nenhuma
function applyEdges() {
  if (!edgeSets.estrutura) return;
  edgeSets.estrutura.visible = edgeMode < 2;
  edgeSets.densa.visible = edgeMode === 0;
  const dim = (focusLayer !== null || selected) ? 0.2 : 1;   // isolar camada/nó apaga o resto
  edgeSets.estrutura.material.opacity = 0.16 * dim;
  edgeSets.densa.material.opacity = 0.05 * dim;
}
const toggles = {
  earth: (on) => { earth.visible = on; mapFrame.visible = on; if (dropMesh) dropMesh.visible = on; },
  edges: () => {},                                        // tratado em applyEdges()
  labels: (on) => { labelsOn = on; },
  spin: (on) => { controls.autoRotate = on; },
  glow: (on) => { useGlow = on; },
};
document.querySelectorAll('.toggles button').forEach((b) => {
  if (b.dataset.toggle === 'edges') {
    b.addEventListener('click', () => {
      edgeMode = (edgeMode + 1) % 3;
      b.classList.toggle('on', edgeMode < 2);
      b.textContent = ['Arestas', 'Esqueleto', 'Sem arestas'][edgeMode];
      b.setAttribute('aria-pressed', String(edgeMode < 2));
      applyEdges();
    });
    return;
  }
  b.addEventListener('click', () => {
    const on = !b.classList.contains('on');
    b.classList.toggle('on', on);
    b.setAttribute('aria-pressed', String(on));
    toggles[b.dataset.toggle]?.(on);
  });
});
if (reduceMotion) {
  document.querySelector('[data-toggle="spin"]').classList.remove('on');
  controls.autoRotate = false;
}

/* ── teclado ───────────────────────────────────────────────────────────── */
addEventListener('keydown', (e) => {
  if (e.target === q) return;
  if (e.key >= '1' && e.key <= '9') setFocusLayer(Number(e.key) - 1);
  else if (e.key === '0' || e.key === 'Escape') { focusLayer = null; clearSelection(); flyTo(home, R * 2.15, 800); applyFocus(); setStatus(); }
  else if (e.key === '/') { e.preventDefault(); q.focus(); }
});

/* ── ponteiro: hover + clique ──────────────────────────────────────────── */
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const tip = document.querySelector('#tip');
let pointerMoved = true, px = 0, py = 0;

canvas.addEventListener('pointermove', (e) => {
  px = e.clientX; py = e.clientY;
  pointer.x = (e.clientX / innerWidth) * 2 - 1;
  pointer.y = -(e.clientY / innerHeight) * 2 + 1;
  pointerMoved = true;
  if (!tip.hidden) {
    tip.style.left = Math.min(px + 16, innerWidth - tip.offsetWidth - 12) + 'px';
    tip.style.top = Math.min(py + 16, innerHeight - tip.offsetHeight - 12) + 'px';
  }
});
canvas.addEventListener('pointerleave', () => { pointerMoved = false; hover(null); });

canvas.addEventListener('click', () => {
  if (dragged) return;
  if (hovered) select(hovered.id); else clearSelection();
});
let dragged = false, downXY = null;
canvas.addEventListener('pointerdown', (e) => { dragged = false; downXY = [e.clientX, e.clientY]; });
canvas.addEventListener('pointerup', (e) => {
  if (downXY && Math.hypot(e.clientX - downXY[0], e.clientY - downXY[1]) > 5) dragged = true;
});

function pickAt() {
  raycaster.setFromCamera(pointer, camera);
  const list = focusLayer === null
    ? meshes
    : meshes.filter((m) => LAYERS[focusLayer].kinds.includes(m.userData.kind));
  const hits = raycaster.intersectObjects(list, false);
  if (!hits.length) return null;
  const hit = hits[0];
  const kind = hit.object.userData.kind;
  const id = hit.object.userData.ids[hit.instanceId];
  return { id, kind, n: byId.get(id) };
}

function hover(hit) {
  if (hit?.id === hovered?.id) return;
  hovered = hit;
  if (!hit) {
    hoverHL.visible = false;
    tip.hidden = true;
    canvas.style.cursor = '';
    return;
  }
  const n = hit.n;
  fillHL(hoverHL, hit.id);
  tip.hidden = false;
  tip.innerHTML = `<b>${esc(n.note || n.id)}</b><br>
    <span class="k">${esc(KIND[n.kind].label)} · camada ${String(n.layer + 1).padStart(2, '0')}</span>
    ${n.city || n.country ? `<br><span class="k">${esc([n.city, ptCountry(n.cc, n.country)].filter(Boolean).join(', '))}</span>` : ''}
    ${n.asn ? `<br><span class="k">${esc(n.asn)}</span>` : ''}`;
  tip.style.left = Math.min(px + 16, innerWidth - tip.offsetWidth - 12) + 'px';
  tip.style.top = Math.min(py + 16, innerHeight - tip.offsetHeight - 12) + 'px';
  canvas.style.cursor = 'pointer';
}

/* ── resize ────────────────────────────────────────────────────────────── */
addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
  composer.setSize(innerWidth, innerHeight);
  bloom.setSize(innerWidth, innerHeight);
});

/* ── intro ─────────────────────────────────────────────────────────────── */
const INTRO = reduceMotion ? 0.35 : 2.5;
let introT = 0;
camera.position.copy(center).add(new THREE.Vector3(0, R * 0.5, R * 0.75));
flyTo(home, R * 2.15, INTRO * 1000);

/* ── loop ──────────────────────────────────────────────────────────────── */
const clock = new THREE.Clock();
const tmp = new THREE.Vector3();

function tick() {
  const dt = Math.min(0.05, clock.getDelta());

  if (introT < INTRO) {
    introT += dt;
    for (const m of meshesAfterIntro) {
      const k = Math.min(1, Math.max(0, (introT - m.userData.delay) / 0.85));
      m.scale.setScalar(0.001 + 0.999 * (1 - Math.pow(1 - k, 3)));
    }
  } else if (meshes[0] && meshes[0].scale.x !== 1) {
    meshes.forEach((m) => m.scale.setScalar(1));
  }

  if (camTween) {
    camTween.t += dt * 1000;
    const k = Math.min(1, camTween.t / camTween.dur);
    const e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
    camera.position.lerpVectors(camTween.c0, camTween.c1, e);
    controls.target.lerpVectors(camTween.t0, camTween.t1, e);
    if (k >= 1) camTween = null;
  }

  controls.update();

  if (pointerMoved) {
    hover(pickAt());
    pointerMoved = false;
  }

  for (const L of nodeLabels) {
    tmp.copy(L.pos).project(camera);
    const vis = labelsOn && tmp.z < 1;
    L.el.style.display = vis ? '' : 'none';
    if (!vis) continue;
    L.el.style.left = ((tmp.x * 0.5 + 0.5) * innerWidth) + 'px';
    L.el.style.top = ((-tmp.y * 0.5 + 0.5) * innerHeight) + 'px';
    const inFocus = focusLayer === null || LAYERS[focusLayer].kinds.includes(L.kind);
    L.el.style.opacity = inFocus ? '1' : '0.18';
  }

  if (marker.visible && selected) {
    marker.scale.setScalar(Math.max(0.45, KIND[byId.get(selected).kind].r * (2.0 + 0.5 * Math.sin(performance.now() / 320))));
  }

  if (useGlow) composer.render(); else renderer.render(scene, camera);
  requestAnimationFrame(tick);
}

/* ── pronto ────────────────────────────────────────────────────────────── */
applyFocus();
setStatus();
requestAnimationFrame(tick);
setTimeout(() => document.querySelector('#boot').classList.add('gone'), 260);

/* exposto para verificação automatizada */
window.__viz = {
  stats, focusLayer: () => focusLayer, selected: () => selected,
  meshes: meshes.length, groups: groups.size, edgesMesh: !!edgesMesh,
  setFocus: setFocusLayer, select, center, R,
  camera, controls, scene, layers: LAYERS, byId, noteOf,
  toggle: (k) => { const b = document.querySelector(`[data-toggle="${k}"]`); if (b) b.click(); return k; },
  look: (px, py, pz, tx, ty, tz) => {
    camera.position.set(px, py, pz);
    controls.target.set(tx, ty, tz);
    controls.update();
  },
};
