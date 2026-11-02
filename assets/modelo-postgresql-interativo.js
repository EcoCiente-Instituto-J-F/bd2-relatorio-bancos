(() => {
  'use strict';

  const model = window.ECOCIENTE_PG_MODEL;
  const svg = document.getElementById('schema-map');
  const areaFilter = document.getElementById('area-filter');
  const searchInput = document.getElementById('table-search');
  const tableList = document.getElementById('table-list');
  const showRelationsControl = document.getElementById('show-all-relations');
  const relationsToggle = document.getElementById('relations-toggle');
  const catalogCount = document.getElementById('catalog-count');
  const details = document.getElementById('table-details');
  const status = document.getElementById('canvas-status');
  const NS = 'http://www.w3.org/2000/svg';
  const CARD_W = 340;
  const ROW_H = 23;
  const CARD_HEADER = 42;
  const H_GAP = 210;
  const V_GAP = 74;
  const FULL_GROUPS = [
    { id: 'cadastros', title: 'Pessoas e condomínios', side: 0 },
    { id: 'referencias', title: 'Tabelas de referência', side: 1 },
    { id: 'coletas', title: 'Cooperativas e coletas', side: 0 },
    { id: 'educacao', title: 'Educação e quizzes', side: 1 },
    { id: 'postagens', title: 'Postagens e pontos', side: 0 },
    { id: 'auditoria', title: 'Conversas e auditoria', side: 1 },
    { id: 'apoio', title: 'Tabelas de apoio', side: 0 },
    { id: 'datamart', title: 'Data Mart', side: 1 },
  ];
  const GROUP_LABELS = Object.fromEntries(FULL_GROUPS.map(group => [group.id, group.title]));
  const tables = model?.tables || [];
  const relations = (model?.relations || []).map((rel, id) => ({ ...rel, id }));
  const byName = new Map(tables.map(table => [table.name, table]));
  const initialView = new URLSearchParams(location.search).get('visao');
  const validViews = new Set(['all', ...FULL_GROUPS.map(group => group.id)]);

  const state = {
    group: initialView === 'todas' ? 'all' : validViews.has(initialView) ? initialView : 'all',
    selected: null, search: '', showAllRelations: true,
    nodes: new Map(), activeRelations: [], nodeElements: new Map(),
    edgeElements: new Map(), view: { x: 20, y: 20, k: 1 },
    regions: [], viewport: null, pointer: null,
  };

  function makeSvg(tag, attrs = {}) {
    const element = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
    return element;
  }

  function makeText(x, y, className, value) {
    const element = makeSvg('text', { x, y, class: className });
    element.textContent = value;
    return element;
  }

  function text(parent, tag, value, className) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    element.textContent = value;
    parent.append(element);
    return element;
  }

  function relationLabel(rel) {
    return `${rel.source}.${rel.sourceColumns.join(', ')} → ${rel.target}.${rel.targetColumns.join(', ')}`;
  }

  function visibleData() {
    if (state.group === 'all') return { names: new Set(tables.map(table => table.name)), edges: relations };
    const names = new Set(tables.filter(table => table.group === state.group).map(table => table.name));
    const edges = relations.filter(rel => names.has(rel.source)
      || (state.selected && (rel.source === state.selected || rel.target === state.selected)));
    for (const rel of edges) {
      names.add(rel.source);
      names.add(rel.target);
    }
    return { names, edges };
  }

  function buildRows(name, edges) {
    const table = byName.get(name);
    const rows = table.pk.map(col => ({ label: col, kind: 'PK', anchor: `pk:${col}` }));
    const outgoing = edges.filter(rel => rel.source === name);
    const incoming = edges.filter(rel => rel.target === name);
    for (const rel of outgoing) {
      rows.push({ label: rel.sourceColumns.join(', '), kind: 'FK', anchor: `source:${rel.id}` });
    }
    for (const rel of incoming) {
      const key = rel.targetColumns.join(', ');
      if (rel.targetColumns.length === 1 && table.pk.includes(key)) continue;
      if (!rows.some(row => row.kind === 'REF' && row.label === key)) {
        rows.push({ label: key, kind: 'REF', anchor: `ref:${key}` });
      }
    }
    if (!rows.length) rows.push({ label: 'Sem chaves neste recorte', kind: '', anchor: 'empty' });
    return rows;
  }

  function layout(names, edges) {
    const depth = new Map([...names].map(name => [name, 0]));
    for (let pass = 0; pass < 9; pass++) {
      let changed = false;
      for (const rel of edges) {
        if (rel.source === rel.target) continue;
        const next = Math.min(8, depth.get(rel.target) + 1);
        if (next > depth.get(rel.source)) {
          depth.set(rel.source, next);
          changed = true;
        }
      }
      if (!changed) break;
    }
    const maxDepth = Math.max(0, ...depth.values());
    const layers = Array.from({ length: maxDepth + 1 }, () => []);
    for (const name of names) layers[maxDepth - depth.get(name)].push(name);
    for (const layer of layers) layer.sort((a, b) => a.localeCompare(b, 'pt-BR'));

    // A ordem de cada coluna aproxima fontes dos destinos de suas FKs.
    for (let layerIndex = layers.length - 2; layerIndex >= 0; layerIndex--) {
      const targetOrder = new Map();
      layers[layerIndex + 1].forEach((name, index) => targetOrder.set(name, index));
      const score = name => {
        const positions = edges.filter(rel => rel.source === name && targetOrder.has(rel.target))
          .map(rel => targetOrder.get(rel.target));
        return positions.length
          ? positions.reduce((sum, value) => sum + value, 0) / positions.length
          : Number.POSITIVE_INFINITY;
      };
      layers[layerIndex].sort((a, b) => score(a) - score(b) || a.localeCompare(b, 'pt-BR'));
    }

    const nodes = new Map();
    const heights = layers.map(layer => layer.reduce((total, name) => {
      const rows = buildRows(name, edges);
      return total + CARD_HEADER + rows.length * ROW_H + 10 + V_GAP;
    }, 0));
    const maxHeight = Math.max(0, ...heights);
    layers.forEach((layer, column) => {
      let y = 70 + Math.max(0, (maxHeight - heights[column]) / 2);
      for (const name of layer) {
        const rows = buildRows(name, edges);
        const height = CARD_HEADER + rows.length * ROW_H + 10;
        nodes.set(name, {
          name, table: byName.get(name), rows,
          x: 60 + column * (CARD_W + H_GAP), y, width: CARD_W, height,
        });
        y += height + V_GAP;
      }
    });
    return nodes;
  }

  function layoutAll(edges) {
    const nodes = new Map();
    const regions = [];
    const nextY = [40, 40];
    for (const config of FULL_GROUPS) {
      const members = tables.filter(table => table.group === config.id)
        .sort((a, b) => a.name.localeCompare(b.name, 'pt-BR'));
      const regionX = config.side === 0 ? 40 : 1150;
      const regionY = nextY[config.side];
      const columnHeights = [0, 0];
      for (const table of members) {
        const rows = buildRows(table.name, edges);
        const height = CARD_HEADER + rows.length * ROW_H + 10;
        const col = columnHeights[0] <= columnHeights[1] ? 0 : 1;
        nodes.set(table.name, {
          name: table.name, table, rows,
          x: regionX + 48 + col * (CARD_W + 150),
          y: regionY + 82 + columnHeights[col],
          width: CARD_W, height,
        });
        columnHeights[col] += height + V_GAP;
      }
      const bodyHeight = Math.max(0, ...columnHeights) - (members.length ? V_GAP : 0);
      const regionHeight = Math.max(190, bodyHeight + 138);
      regions.push({
        ...config, x: regionX, y: regionY, width: 1010,
        height: regionHeight, count: members.length,
      });
      nextY[config.side] += regionHeight + 160;
    }
    return { nodes, regions };
  }

  function rowY(node, anchor) {
    const rowIndex = node.rows.findIndex(row => row.anchor === anchor);
    return node.y + CARD_HEADER + (rowIndex >= 0 ? rowIndex : 0) * ROW_H + ROW_H / 2;
  }

  function targetAnchor(rel) {
    const target = byName.get(rel.target);
    if (rel.targetColumns.length === 1 && target.pk.includes(rel.targetColumns[0])) {
      return `pk:${rel.targetColumns[0]}`;
    }
    return `ref:${rel.targetColumns.join(', ')}`;
  }

  function edgePath(rel) {
    const source = state.nodes.get(rel.source);
    const target = state.nodes.get(rel.target);
    const y1 = rowY(source, `source:${rel.id}`);
    const y2 = rowY(target, targetAnchor(rel));
    if (source.name === target.name) {
      const x1 = source.x + CARD_W;
      const loopX = x1 + 104;
      return `M ${x1} ${y1} C ${loopX} ${y1}, ${loopX} ${y2 - 62}, ${x1} ${y2}`;
    }
    if (source.x + CARD_W < target.x) {
      const x1 = source.x + CARD_W;
      const x2 = target.x;
      const bend = Math.max(35, (x2 - x1) * .5);
      return `M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}`;
    }
    if (target.x + CARD_W < source.x) {
      const x1 = source.x;
      const x2 = target.x + CARD_W;
      const bend = Math.max(35, (x1 - x2) * .5);
      return `M ${x1} ${y1} C ${x1 - bend} ${y1}, ${x2 + bend} ${y2}, ${x2} ${y2}`;
    }
    const x = Math.max(source.x, target.x) + CARD_W + 100 + (rel.id % 4) * 16;
    return `M ${source.x + CARD_W} ${y1} C ${x} ${y1}, ${x} ${y2}, ${target.x + CARD_W} ${y2}`;
  }

  function applyView() {
    state.viewport?.setAttribute('transform',
      `translate(${state.view.x} ${state.view.y}) scale(${state.view.k})`);
    updateStatus();
  }

  function updateStatus() {
    const zoom = Math.round(state.view.k * 100);
    status.textContent = `${state.nodes.size} tabelas · ${state.activeRelations.length} relações · ${zoom}%${zoom < 45 ? ' · amplie para ler' : ''}`;
  }

  function setZoom(newZoom, centerX, centerY) {
    const zoom = Math.max(.08, Math.min(2.4, newZoom));
    const old = state.view.k;
    state.view.x = centerX - (centerX - state.view.x) * zoom / old;
    state.view.y = centerY - (centerY - state.view.y) * zoom / old;
    state.view.k = zoom;
    applyView();
  }

  function fitMap(keepLegible = false) {
    if (!state.nodes.size) return;
    const values = [...state.nodes.values()];
    const bounds = state.regions.length ? state.regions : values;
    const minX = Math.min(...bounds.map(item => item.x));
    const maxX = Math.max(...bounds.map(item => item.x + (item.width || CARD_W)));
    const minY = Math.min(...bounds.map(item => item.y));
    const maxY = Math.max(...bounds.map(item => item.y + item.height));
    const width = Math.max(1, svg.clientWidth);
    const height = Math.max(1, svg.clientHeight);
    const fitted = Math.min((width - 55) / (maxX - minX), (height - 55) / (maxY - minY), 1.1);
    const zoom = keepLegible ? Math.max(.72, fitted) : Math.max(.08, fitted);
    state.view.k = zoom;
    state.view.x = fitted < zoom ? 22 - minX * zoom : (width - (maxX - minX) * zoom) / 2 - minX * zoom;
    state.view.y = fitted < zoom ? 22 - minY * zoom : (height - (maxY - minY) * zoom) / 2 - minY * zoom;
    applyView();
  }

  function updateVisualStates() {
    const selected = state.selected;
    const connected = new Set();
    if (selected) {
      for (const rel of state.activeRelations) {
        if (rel.source === selected) connected.add(rel.target);
        if (rel.target === selected) connected.add(rel.source);
      }
    }
    const query = state.search.toLowerCase();
    for (const [name, group] of state.nodeElements) {
      const matches = !query || name.toLowerCase().includes(query);
      group.classList.toggle('is-selected', name === selected);
      group.classList.toggle('is-connected', selected !== null && connected.has(name) && name !== selected);
      group.classList.toggle('is-dim', selected
        ? name !== selected && !connected.has(name)
        : !matches);
    }
    for (const [id, item] of state.edgeElements) {
      const rel = state.activeRelations.find(edge => edge.id === id);
      const isConnected = selected && (rel.source === selected || rel.target === selected);
      const matches = !query || rel.source.toLowerCase().includes(query) || rel.target.toLowerCase().includes(query);
      const hide = state.group === 'all' && !state.showAllRelations && !isConnected;
      item.path.classList.toggle('is-connected', Boolean(isConnected));
      item.path.classList.toggle('is-hidden', Boolean(hide));
      item.hit.classList.toggle('is-hidden', Boolean(hide));
      item.path.classList.toggle('is-dim', selected ? !isConnected : !matches);
    }
    for (const button of tableList.querySelectorAll('.table-link')) {
      button.setAttribute('aria-current', button.dataset.name === selected ? 'true' : 'false');
    }
  }

  function redrawEdges() {
    for (const rel of state.activeRelations) {
      const item = state.edgeElements.get(rel.id);
      const path = edgePath(rel);
      item.path.setAttribute('d', path);
      item.hit.setAttribute('d', path);
    }
  }

  function renderGraph(keepLegible = true) {
    const { names, edges } = visibleData();
    state.activeRelations = edges;
    if (state.group === 'all') {
      const full = layoutAll(edges);
      state.nodes = full.nodes;
      state.regions = [];
    } else {
      state.nodes = layout(names, edges);
      state.regions = [];
    }
    state.nodeElements.clear();
    state.edgeElements.clear();
    svg.replaceChildren();
    svg.setAttribute('viewBox', `0 0 ${Math.max(1, svg.clientWidth)} ${Math.max(1, svg.clientHeight)}`);

    const defs = makeSvg('defs');
    const marker = makeSvg('marker', {
      id: 'fk-arrow', markerWidth: 9, markerHeight: 9, refX: 8, refY: 4.5,
      orient: 'auto', markerUnits: 'strokeWidth',
    });
    marker.append(makeSvg('path', { d: 'M 1 1 L 8 4.5 L 1 8', fill: 'none', stroke: '#16815e', 'stroke-width': 1.6 }));
    defs.append(marker);
    svg.append(defs);
    const viewport = makeSvg('g');
    state.viewport = viewport;
    svg.append(viewport);
    const edgeLayer = makeSvg('g', { 'aria-hidden': 'true' });
    const nodeLayer = makeSvg('g');
    viewport.append(edgeLayer, nodeLayer);

    for (const rel of edges) {
      const path = makeSvg('path', {
        class: `edge${rel.source === rel.target ? ' self' : ''}`,
        d: edgePath(rel), 'marker-end': 'url(#fk-arrow)',
      });
      const hit = makeSvg('path', { class: 'edge-hit', d: edgePath(rel), 'data-rel-id': rel.id });
      const title = makeSvg('title');
      title.textContent = relationLabel(rel);
      hit.append(title);
      edgeLayer.append(path, hit);
      state.edgeElements.set(rel.id, { path, hit });
    }

    for (const node of state.nodes.values()) {
      const group = makeSvg('g', {
        class: `node${node.table.group === 'datamart' ? ' mart' : ''}${node.table.group === 'apoio' ? ' support' : ''}${state.group !== 'all' && node.table.group !== state.group ? ' external' : ''}`,
        transform: `translate(${node.x} ${node.y})`,
        tabindex: 0, role: 'button',
        'aria-label': `Tabela ${node.name}; chave primária ${node.table.pk.join(', ')}`,
        'data-name': node.name,
      });
      group.append(makeSvg('rect', { x: 0, y: 0, width: CARD_W, height: node.height, rx: 10 }));
      group.append(makeSvg('rect', { class: 'node-head', x: 1, y: 1, width: CARD_W - 2, height: 40, rx: 9 }));
      group.append(makeText(13, 25, 'node-name', node.name));
      node.rows.forEach((row, index) => {
        const y = CARD_HEADER + index * ROW_H;
        if (index) group.append(makeSvg('path', { class: 'node-rule', d: `M 13 ${y} H ${CARD_W - 13}` }));
        group.append(makeText(13, y + 16, 'node-field', row.label));
        if (row.kind) {
          const tag = makeText(CARD_W - 13, y + 16, 'node-key', row.kind);
          tag.setAttribute('text-anchor', 'end');
          group.append(tag);
        }
      });
      group.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          selectTable(node.name);
        }
      });
      nodeLayer.append(group);
      state.nodeElements.set(node.name, group);
    }
    if (state.selected && !state.nodes.has(state.selected)) state.selected = null;
    fitMap(keepLegible);
    updateVisualStates();
    renderDetails();
  }

  function findGroupFor(name) {
    const table = byName.get(name);
    if (table.group !== 'referencias') return table.group;
    const first = relations.find(rel => rel.target === name && byName.get(rel.source).group !== 'datamart');
    return first ? byName.get(first.source).group : 'all';
  }

  function selectTable(name) {
    if (!byName.has(name)) return;
    const table = byName.get(name);
    if (state.group !== 'all' && table.group !== state.group && table.group !== 'referencias') {
      state.group = table.group;
      areaFilter.value = state.group;
    } else if (!state.nodes.has(name)) {
      state.group = findGroupFor(name);
      areaFilter.value = state.group;
    }
    state.selected = name;
    if (state.group !== 'all') renderGraph();
    else {
      updateVisualStates();
      renderDetails();
    }
    const node = state.nodes.get(name);
    if (node) {
      const centerX = node.x + node.width / 2;
      const centerY = node.y + node.height / 2;
      state.view.x = svg.clientWidth / 2 - centerX * state.view.k;
      state.view.y = svg.clientHeight / 2 - centerY * state.view.k;
      applyView();
    }
  }

  function renderCatalog() {
    const query = state.search.toLowerCase();
    const matches = tables.filter(table => table.name.toLowerCase().includes(query));
    catalogCount.textContent = matches.length;
    tableList.replaceChildren();
    if (!matches.length) {
      text(tableList, 'p', 'Nenhuma tabela encontrada.', 'empty-list');
      return;
    }
    for (const table of matches) {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'table-link';
      button.dataset.name = table.name;
      button.setAttribute('aria-current', table.name === state.selected ? 'true' : 'false');
      button.textContent = table.name;
      button.addEventListener('click', () => selectTable(table.name));
      tableList.append(button);
    }
  }

  function relationButton(list, rel, counterpart) {
    const item = document.createElement('li');
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = counterpart;
    const columns = document.createElement('small');
    columns.textContent = `${rel.sourceColumns.join(', ')} → ${rel.targetColumns.join(', ')} · ${GROUP_LABELS[byName.get(counterpart).group]}`;
    button.append(columns);
    button.addEventListener('click', () => selectTable(counterpart));
    item.append(button);
    list.append(item);
  }

  function renderDetails() {
    details.replaceChildren();
    if (!state.selected) {
      text(details, 'p', 'Selecione uma tabela no mapa ou use a busca.', 'placeholder');
      return;
    }
    const table = byName.get(state.selected);
    text(details, 'h3', table.name);
    text(details, 'p', `${table.columns.length} colunas · PK ${table.pk.join(', ')} · ${GROUP_LABELS[table.group]}`, 'meta');
    text(details, 'p', 'Colunas', 'section-title');
    const fields = document.createElement('ul');
    fields.className = 'field-list';
    const foreignCols = new Set(relations.filter(rel => rel.source === table.name)
      .flatMap(rel => rel.sourceColumns));
    for (const col of table.columns) {
      const item = document.createElement('li');
      text(item, 'span', col);
      const badges = document.createElement('span');
      badges.className = 'badges';
      if (table.pk.includes(col)) text(badges, 'span', 'PK', 'badge');
      if (foreignCols.has(col)) text(badges, 'span', 'FK', 'badge fk');
      item.append(badges);
      fields.append(item);
    }
    details.append(fields);
    const outgoing = relations.filter(rel => rel.source === table.name);
    const incoming = relations.filter(rel => rel.target === table.name);
    if (outgoing.length) {
      text(details, 'p', `Referências a outras tabelas (${outgoing.length})`, 'section-title');
      const list = document.createElement('ul');
      list.className = 'relation-list';
      outgoing.forEach(rel => relationButton(list, rel, rel.target));
      details.append(list);
    }
    if (incoming.length) {
      text(details, 'p', `Referenciada por (${incoming.length})`, 'section-title');
      const list = document.createElement('ul');
      list.className = 'relation-list';
      incoming.forEach(rel => relationButton(list, rel, rel.source));
      details.append(list);
    }
  }

  function pointInSvg(event) {
    const bounds = svg.getBoundingClientRect();
    return { x: event.clientX - bounds.left, y: event.clientY - bounds.top };
  }

  svg.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    const group = event.target.closest('.node');
    const edge = event.target.closest('.edge-hit');
    const point = pointInSvg(event);
    state.pointer = {
      id: event.pointerId, name: group?.dataset.name || null,
      edgeId: edge ? Number(edge.dataset.relId) : null,
      startX: point.x, startY: point.y,
      viewX: state.view.x, viewY: state.view.y,
      nodeX: group ? state.nodes.get(group.dataset.name).x : 0,
      nodeY: group ? state.nodes.get(group.dataset.name).y : 0,
      moved: false,
    };
    svg.setPointerCapture(event.pointerId);
    if (!group) svg.classList.add('is-panning');
  });

  svg.addEventListener('pointermove', event => {
    const p = state.pointer;
    if (!p || p.id !== event.pointerId) return;
    const point = pointInSvg(event);
    const dx = point.x - p.startX;
    const dy = point.y - p.startY;
    if (Math.hypot(dx, dy) > 4) p.moved = true;
    if (!p.moved) return;
    if (p.name) {
      const node = state.nodes.get(p.name);
      node.x = p.nodeX + dx / state.view.k;
      node.y = p.nodeY + dy / state.view.k;
      state.nodeElements.get(p.name).setAttribute('transform', `translate(${node.x} ${node.y})`);
      redrawEdges();
    } else {
      state.view.x = p.viewX + dx;
      state.view.y = p.viewY + dy;
      applyView();
    }
  });

  function finishPointer(event) {
    const p = state.pointer;
    if (!p || p.id !== event.pointerId) return;
    if (p.name && !p.moved) selectTable(p.name);
    else if (p.edgeId !== null && !p.moved) {
      const rel = state.activeRelations.find(item => item.id === p.edgeId);
      if (rel) selectTable(rel.source);
    }
    state.pointer = null;
    svg.classList.remove('is-panning');
  }
  svg.addEventListener('pointerup', finishPointer);
  svg.addEventListener('pointercancel', finishPointer);
  svg.addEventListener('wheel', event => {
    event.preventDefault();
    const point = pointInSvg(event);
    setZoom(state.view.k * (event.deltaY < 0 ? 1.13 : 1 / 1.13), point.x, point.y);
  }, { passive: false });

  document.getElementById('zoom-in').addEventListener('click', () =>
    setZoom(state.view.k * 1.2, svg.clientWidth / 2, svg.clientHeight / 2));
  document.getElementById('zoom-out').addEventListener('click', () =>
    setZoom(state.view.k / 1.2, svg.clientWidth / 2, svg.clientHeight / 2));
  document.getElementById('fit-map').addEventListener('click', () => fitMap(false));
  areaFilter.addEventListener('change', () => {
    state.group = areaFilter.value;
    state.selected = null;
    relationsToggle.hidden = state.group !== 'all';
    renderGraph(state.group !== 'all');
  });
  showRelationsControl.addEventListener('change', () => {
    state.showAllRelations = showRelationsControl.checked;
    updateVisualStates();
  });
  searchInput.addEventListener('input', () => {
    state.search = searchInput.value.trim();
    renderCatalog();
    updateVisualStates();
  });
  searchInput.addEventListener('keydown', event => {
    if (event.key !== 'Enter') return;
    const first = tables.find(table => table.name.toLowerCase().includes(state.search.toLowerCase()));
    if (first) selectTable(first.name);
  });
  svg.addEventListener('keydown', event => {
    if (event.target !== svg) return;
    if (event.key === '+' || event.key === '=') {
      event.preventDefault();
      setZoom(state.view.k * 1.2, svg.clientWidth / 2, svg.clientHeight / 2);
    } else if (event.key === '-') {
      event.preventDefault();
      setZoom(state.view.k / 1.2, svg.clientWidth / 2, svg.clientHeight / 2);
    } else if (event.key === '0') {
      event.preventDefault();
      fitMap(false);
    }
  });

  if (tables.length !== 59 || relations.length !== 92) {
    status.textContent = 'Os dados do mapa não foram carregados corretamente.';
    return;
  }
  areaFilter.value = state.group;
  relationsToggle.hidden = state.group !== 'all';
  showRelationsControl.checked = true;
  renderCatalog();
  renderGraph(state.group !== 'all');
  new ResizeObserver(() => {
    svg.setAttribute('viewBox', `0 0 ${Math.max(1, svg.clientWidth)} ${Math.max(1, svg.clientHeight)}`);
  }).observe(svg);
})();
