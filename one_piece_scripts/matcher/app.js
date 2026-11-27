/* Manual matcher UI - vanilla JS, no build step. */

let data = { queue: [], auto: {} };
let state = { links: {}, resolved: [] };
let resolvedSet = new Set();
let filter = 'pending';
let search = '';
let curIdx = -1;
let selOfficial = null;
let saveTimer = null;

const $ = (id) => document.getElementById(id);

function jget(url) { return fetch(url).then(r => r.json()); }

function toast(msg) {
  const t = $('toast');
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._h);
  t._h = setTimeout(() => { t.hidden = true; }, 1600);
}

function save() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    fetch('/api/state', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ links: state.links, resolved: [...resolvedSet] })
    }).then(r => {
      if (!r.ok) return r.text().then(m => toast('save failed: ' + m));
      toast('saved');
      renderSidebar();
      renderProgress();
    });
  }, 250);
}

function crImg(url) {
  return '/img/c/?u=' + encodeURIComponent(url);
}
function offImg(code) {
  return '/img/o/' + encodeURIComponent(code) + '.png';
}

function finalAssignment(item, code) {
  if (Object.prototype.hasOwnProperty.call(state.links, code)) {
    return state.links[code].length ? 'manual' : 'cleared';
  }
  if (item.assigned && item.assigned[code]) return 'auto';
  return null;
}

function unresolvedCount(item) {
  if (item.type !== 'variant') return 1;
  return item.official.filter(o => finalAssignment(item, o.image_code) === null).length;
}

function statusOf(item) {
  if (item.type !== 'variant') {
    if (resolvedSet.has(item.base_code)) return 'resolved';
    const linked = state.links[item.base_code] || (data.auto[item.base_code] || []);
    return linked.includes(item.entry.name) ? 'resolved' : 'pending';
  }
  if (resolvedSet.has(item.base_code)) return 'resolved';
  return unresolvedCount(item) === 0 ? 'resolved' : 'pending';
}

function filteredItems() {
  return data.queue.filter(item => {
    const st = statusOf(item);
    if (filter === 'pending' && st === 'resolved') return false;
    if (filter === 'resolved' && st !== 'resolved') return false;
    if (search) {
      const hay = (item.base_code + ' ' + (item.official_name || '') + ' ' +
        (item.type === 'name_mismatch' ? item.entry.name : '')).toLowerCase();
      if (!hay.includes(search)) return false;
    }
    return true;
  });
}

function renderProgress() {
  const total = data.queue.length;
  const done = data.queue.filter(i => statusOf(i) === 'resolved').length;
  const links = Object.keys(state.links).length;
  $('progress').innerHTML = `<b>${done}</b> / ${total} reviewed · ${links} manual links`;
}

function renderSidebar() {
  const items = filteredItems();
  const ul = $('itemList');
  ul.innerHTML = '';
  items.forEach(item => {
    const li = document.createElement('li');
    const idx = data.queue.indexOf(item);
    if (idx === curIdx) li.className = 'active';
    const st = statusOf(item);
    const dot = document.createElement('span');
    dot.className = 'dot ' + (item.type === 'name_mismatch' && st !== 'resolved' ? 'nm' : st);
    const code = document.createElement('span');
    code.className = 'item-code';
    code.textContent = item.base_code;
    const sub = document.createElement('span');
    sub.className = 'item-sub';
    sub.textContent = item.type === 'variant'
      ? (unresolvedCount(item) === 0 ? '✓' : unresolvedCount(item) + ' open')
      : 'name';
    li.append(dot, code, sub);
    li.onclick = () => selectItem(idx);
    ul.appendChild(li);
  });
}

function selectItem(idx) {
  if (idx < 0 || idx >= data.queue.length) return;
  curIdx = idx;
  selOfficial = null;
  renderSidebar();
  renderItem();
  const active = document.querySelector('#itemList li.active');
  if (active) active.scrollIntoView({ block: 'nearest' });
}

function currentItem() { return data.queue[curIdx]; }

function reasonChip(item, code) {
  const r = (item.reason || {})[code];
  if (!r || !r.rule || r.rule === 'unresolved' || r.rule === 'queued_text_stage') return '';
  if (r.rule === 'count') return '<span class="chip auto">auto · 1:1</span>';
  let s = `<span class="chip auto">auto · pHash d=${r.distance}`;
  if (r.second_best != null) s += `, 2nd ${r.second_best}`;
  return s + '</span>';
}

function renderItem() {
  const item = currentItem();
  if (!item) { $('itemView').hidden = true; $('emptyState').hidden = false; return; }
  $('itemView').hidden = false;
  $('emptyState').hidden = true;

  $('itemTitle').textContent = item.base_code + (item.official_name ? ' — ' + item.official_name : '');
  const st = statusOf(item);
  $('itemMeta').innerHTML =
    `<span class="badge">${item.type === 'variant' ? 'variant matching' : 'name mismatch'}</span>` +
    `<span class="badge">${st}</span>` +
    (resolvedSet.has(item.base_code) ? '<span class="badge">accepted</span>' : '');

  $('nameMismatchBox').hidden = item.type !== 'name_mismatch';
  document.querySelector('#officialRow').parentElement.hidden = item.type !== 'variant';
  document.querySelector('#candidateRow').parentElement.hidden = item.type !== 'variant';
  document.querySelector('#linkTable').parentElement.hidden = item.type !== 'variant';

  if (item.type === 'name_mismatch') return renderNameMismatch(item);

  // official variants
  const orow = $('officialRow');
  orow.innerHTML = '';
  item.official.forEach((o, i) => {
    const div = document.createElement('div');
    const a = finalAssignment(item, o.image_code);
    div.className = 'img-card' +
      (selOfficial === o.image_code ? ' selected' : '') +
      (a === 'manual' ? ' linked' : '');
    const hints = (item.phash_hints || {})[o.image_code] || [];
    let chips = '';
    if (a === 'manual') chips += `<span class="chip manual">manual link</span>`;
    else if (a === 'auto') chips += reasonChip(item, o.image_code);
    else if (a === 'cleared') chips += `<span class="chip dead">cleared</span>`;
    else chips += `<span class="chip warn">unresolved</span>`;
    hints.forEach(h => {
      chips += `<span class="chip hint">→ g${h.group + 1} d=${h.distance}</span>`;
    });
    div.innerHTML =
      `<img loading="lazy" src="${offImg(o.image_code)}" alt="${o.image_code}">` +
      `<div class="label">${o.image_code}</div><div>${chips}</div>`;
    div.onclick = () => {
      selOfficial = (selOfficial === o.image_code) ? null : o.image_code;
      renderItem();
    };
    orow.appendChild(div);
  });

  // candidates (sorted by hint distance for the selected official, if any)
  const cand = $('candidateRow');
  cand.innerHTML = '';
  const hints = selOfficial ? ((item.phash_hints || {})[selOfficial] || []) : [];
  const hintFor = (idx) => hints.find(h => h.group === idx);
  const idxs = item.candidates.map((c, i) => i);
  if (hints.length) {
    idxs.sort((a, b) => {
      const ha = hintFor(a), hb = hintFor(b);
      if (ha && hb) return ha.distance - hb.distance;
      if (ha) return -1;
      if (hb) return 1;
      return 0;
    });
  }
  idxs.forEach(gi => {
    const g = item.candidates[gi];
    const rep = g.entries.find(e => !/未開封|付属品完備/.test(e.name)) || g.entries[0];
    const div = document.createElement('div');
    const linkedTo = item.official.filter(o => {
      const a = finalAssignment(item, o.image_code);
      if (a === 'auto') {
        const t = item.assigned[o.image_code] || [];
        return JSON.stringify(t) === JSON.stringify([...g.tokens, ...(g.illust ? [g.illust] : [])]);
      }
      if (a === 'manual') {
        const pats = state.links[o.image_code] || [];
        return pats.includes(g.entries[0].name);
      }
      return false;
    }).map(o => o.image_code);
    const h = hintFor(gi);
    let chips = '';
    linkedTo.forEach(c => { chips += `<span class="chip auto">→ ${c}</span>`; });
    if (h) chips += `<span class="chip hint">d=${h.distance}${selOfficial && !linkedTo.includes(selOfficial) ? ' (best for selection)' : ''}</span>`;
    div.className = 'img-card' + (selOfficial && linkedTo.includes(selOfficial) ? ' selected' : '');
    div.innerHTML =
      `<img loading="lazy" src="${crImg(rep.image)}" alt="">` +
      `<div class="label">${g.tokens.join(' / ') || '(base)'}</div>` +
      `<div class="sub">${g.illust ? g.illust + '<br>' : ''}` +
      g.entries.map(e => `${e.name}<br><span class="price">${e.amount}</span>`).join('<br>') +
      `</div><div>${chips}</div>`;
    div.onclick = () => {
      if (!selOfficial) {
        toast('select an official variant first (click one on the left)');
        return;
      }
      link(selOfficial, gi);
    };
    cand.appendChild(div);
  });

  renderLinkTable(item);
}

function renderLinkTable(item) {
  const box = $('linkTable');
  box.innerHTML = '';
  item.official.forEach(o => {
    const a = finalAssignment(item, o.image_code);
    const row = document.createElement('div');
    row.className = 'link-row';
    let desc = '';
    let srcChip = '';
    if (a === 'manual') {
      const pats = state.links[o.image_code] || [];
      desc = pats.filter(p => !p.startsWith('http')).join(' · ') || '(url-matched)';
      srcChip = `<span class="chip manual">manual</span>`;
    } else if (a === 'auto') {
      desc = (item.assigned[o.image_code] || []).join(' ');
      srcChip = reasonChip(item, o.image_code);
    } else if (a === 'cleared') {
      desc = 'deliberately unmapped';
      srcChip = `<span class="chip dead">cleared</span>`;
    } else {
      desc = '— unresolved —';
      srcChip = `<span class="chip warn">open</span>`;
    }
    row.innerHTML = `<span class="code">${o.image_code}</span>${srcChip}<span class="desc">${desc}</span>`;
    if (a === 'manual' || a === 'cleared') {
      const x = document.createElement('button');
      x.className = 'danger';
      x.textContent = '✕';
      x.title = a === 'cleared' ? 'restore auto assignment' : 'remove manual link';
      x.onclick = () => {
        delete state.links[o.image_code];
        save();
        renderItem();
      };
      row.appendChild(x);
    }
    box.appendChild(row);
  });
}

function link(imageCode, groupIdx) {
  const item = currentItem();
  const g = item.candidates[groupIdx];
  const patterns = [];
  g.entries.forEach(e => {
    patterns.push(e.name);
    if (e.image) patterns.push(e.image);
  });
  // one art group -> one official slot inside this item
  item.official.forEach(o => {
    if (o.image_code === imageCode) return;
    const existing = state.links[o.image_code];
    if (existing && JSON.stringify(existing) === JSON.stringify(patterns)) {
      delete state.links[o.image_code];
    }
  });
  state.links[imageCode] = patterns;
  save();
  renderItem();
  renderSidebar();
}

function renderNameMismatch(item) {
  const box = $('nmEntry');
  const linked = (state.links[item.base_code] || (data.auto[item.base_code] || []))
    .includes(item.entry.name);
  box.innerHTML =
    `<div><strong>Official:</strong> ${item.official_name} <span class="dim">(${item.base_code})</span></div>` +
    `<div style="margin-top:8px"><img loading="lazy" src="${offImg(item.base_code)}.png" onerror="this.style.display='none'"></div>` +
    `<div style="margin-top:10px"><strong>CardRush entry:</strong> ${item.entry.name}</div>` +
    `<div class="sub">${item.entry.model_number} · <span class="price">${item.entry.amount}</span></div>` +
    `<div><img loading="lazy" src="${crImg(item.entry.image)}" style="width:150px;border-radius:6px;background:#0d0f14"></div>` +
    (linked ? '<div class="chip manual">linked to base card</div>' : '');
}

function nameMismatchAdd() {
  const item = currentItem();
  const base = item.base_code;
  const existing = state.links[base] || data.auto[base] || [];
  const next = [...existing];
  if (!next.includes(item.entry.name)) next.push(item.entry.name);
  if (item.entry.image && !next.includes(item.entry.image)) next.push(item.entry.image);
  state.links[base] = next;
  resolvedSet.add(base);
  save();
  toast('linked to base card');
  advance();
}

function nameMismatchIgnore() {
  const item = currentItem();
  resolvedSet.add(item.base_code);
  save();
  advance();
}

function acceptCurrent() {
  const item = currentItem();
  if (!item) return;
  resolvedSet.add(item.base_code);
  save();
  toast('accepted as-is');
  advance();
}

function advance() {
  const items = filteredItems();
  if (items.length === 0) { curIdx = -1; renderItem(); renderSidebar(); renderProgress(); return; }
  selectItem(data.queue.indexOf(items[0]));
}

function step(dir) {
  const items = filteredItems();
  if (!items.length) return;
  const pos = items.findIndex(i => data.queue.indexOf(i) === curIdx);
  const next = pos + dir;
  if (next >= 0 && next < items.length) selectItem(data.queue.indexOf(items[next]));
}

async function init() {
  const d = await jget('/api/data');
  data = d;
  const s = await jget('/api/state');
  state = { links: s.links || {}, resolved: s.resolved || [] };
  resolvedSet = new Set(state.resolved);

  $('search').oninput = (e) => { search = e.target.value.trim().toLowerCase(); renderSidebar(); };
  $('filter').onchange = (e) => { filter = e.target.value; renderSidebar(); };
  $('prevBtn').onclick = () => step(-1);
  $('nextBtn').onclick = () => step(1);
  $('resolveBtn').onclick = acceptCurrent;
  $('nmAdd').onclick = nameMismatchAdd;
  $('nmIgnore').onclick = nameMismatchIgnore;

  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
    else if (e.key === 'Enter') { e.preventDefault(); acceptCurrent(); }
    else if (/^[1-9]$/.test(e.key)) {
      const item = currentItem();
      if (item && item.type === 'variant') {
        const o = item.official[parseInt(e.key, 10) - 1];
        if (o) { selOfficial = o.image_code; renderItem(); }
      }
    } else if (e.key === 'Backspace' || e.key === 'Delete') {
      const item = currentItem();
      if (item && selOfficial && (state.links[selOfficial] || []).length) {
        delete state.links[selOfficial];
        save();
        renderItem();
      }
    }
  });

  renderProgress();
  renderSidebar();
  const items = filteredItems();
  if (items.length) selectItem(data.queue.indexOf(items[0]));
  else renderItem();
}

init().catch(err => {
  document.getElementById('main').innerHTML =
    '<div class="hint">Failed to load: ' + err + '</div>';
});
