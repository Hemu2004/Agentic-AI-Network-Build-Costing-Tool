const API = '/api';

// --- Server status ---
async function checkServerStatus() {
  const el = document.getElementById('server-status');
  if (!el) return;
  try {
    const r = await fetch('/health');
    el.classList.toggle('offline', !r.ok);
    el.innerHTML = (r.ok ? '<span class="status-dot"></span> Online' : '<span class="status-dot"></span> Offline');
  } catch (e) {
    el.classList.add('offline');
    el.innerHTML = '<span class="status-dot"></span> Offline';
  }
}
checkServerStatus();
setInterval(checkServerStatus, 30000);

async function checkOllamaStatus() {
  const el = document.getElementById('ollama-status');
  if (!el) return;
  try {
    const r = await fetch(API + '/ollama-status');
    const data = await r.json();
    el.classList.remove('online', 'offline');
    el.classList.add(data.available ? 'online' : 'offline');
    el.textContent = data.available ? 'Ollama: Online' : 'Ollama: Offline';
    el.title = data.message || (data.available ? 'AI explanations enabled' : 'Start ollama serve and pull a model for AI text');
  } catch (e) {
    el.classList.add('offline');
    el.textContent = 'Ollama: —';
    el.title = 'Could not check Ollama status';
  }
}
checkOllamaStatus();
setInterval(checkOllamaStatus, 45000);

// --- Summary cards ---
function updateSummaryCards(data) {
  if (!data) return;
  const spend = document.getElementById('card-spend');
  const sites = document.getElementById('card-sites');
  const ai = document.getElementById('card-ai');
  const sym = data.currency_symbol || '₹';
  const curr = data.currency || 'INR';
  if (spend) spend.textContent = data.total_cost != null ? formatMoney(data.total_cost, curr, sym) : '—';
  const premises = data.quantities?.onts ?? data.inputs_used?.total_premises ?? data.feasible_premises ?? 0;
  if (sites) sites.textContent = premises || '—';
  if (ai) ai.textContent = (data.optimization_suggestions && data.optimization_suggestions.length) ? '+' + (data.optimization_suggestions.length * 5) + '% potential' : '—';
}

// --- Navigation ---
document.querySelectorAll('.nav-item').forEach(el => {
  el.addEventListener('click', function () {
    const panelId = this.dataset.panel;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    this.classList.add('active');
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const panel = document.getElementById('panel-' + panelId);
    if (panel) panel.classList.add('active');
    if (panelId === 'maps-planner') initMapOnce();
    if (panelId === 'projects') loadProjects();
  });
});

// --- AI Estimator sub-options ---
function showEstimatorOption(option) {
  document.querySelectorAll('.estimator-option').forEach(el => { el.style.display = 'none'; });
  const opt = document.getElementById('estimator-option-' + option);
  if (opt) opt.style.display = 'block';
  document.querySelectorAll('[data-estimator-option]').forEach(b => {
    b.classList.remove('btn-primary');
    b.classList.add('btn-secondary');
    if (b.dataset.estimatorOption === option) { b.classList.add('btn-primary'); b.classList.remove('btn-secondary'); }
  });
  const btnCost = document.getElementById('btn-run-cost');
  if (btnCost) {
    btnCost.textContent = option === 'cost' ? 'Run Estimation' : option === 'budget' ? 'Run Budget Planning' : 'Run Upgrade Plan';
    btnCost.dataset.currentOption = option;
  }
}
document.querySelectorAll('[data-estimator-option]').forEach(btn => {
  btn.addEventListener('click', () => showEstimatorOption(btn.dataset.estimatorOption));
});
const btnRun = document.getElementById('btn-run-cost');
if (btnRun) { btnRun.dataset.currentOption = 'cost'; }

function escapeHtml(s) {
  if (s == null) return '';
  const div = document.createElement('div');
  div.textContent = String(s);
  return div.innerHTML;
}

function formatMoney(amount, currency, symbol) {
  if (amount == null || isNaN(amount)) return (symbol || '$') + '0';
  const num = Number(amount);
  const sym = symbol || '$';
  const locale = (currency || '').toUpperCase() === 'INR' ? 'en-IN' : (currency || '').toUpperCase() === 'EUR' ? 'de-DE' : 'en-US';
  const formatted = num.toLocaleString(locale, { maximumFractionDigits: 0, minimumFractionDigits: 0 });
  if (sym === '₹') return '₹' + formatted;
  if (sym === '£' || sym === '€') return sym + formatted;
  return '$' + formatted;
}

function _numOrNull(v) {
  if (v == null) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function readCostParameters(prefix) {
  const p = prefix || 'cp-';
  const keys = [
    'fiber_per_km',
    'splitter_1_32',
    'splitter_1_64',
    'olt_port',
    'ont_unit',
    'cabinet',
    'civil_per_km',
    'labor_per_premise',
    'maintenance_year_pct'
  ];
  const out = {};
  keys.forEach(k => {
    const el = document.getElementById(p + k);
    if (!el) return;
    const n = _numOrNull(el.value);
    if (n == null || n < 0) return; // ignore invalid/negative
    out[k] = n;
  });
  return out;
}

// --- Render result: Total bar, Tabs (Quote, Hardware, Strategy), Agent log ---
let resultChart = null;
function buildResultHtml(d, quantities, chartData, total, roi, payback, agentLog) {
  const breakdown = d.cost_breakdown || {};
  const sym = d.currency_symbol || '₹';
  const curr = d.currency || 'INR';
  let html = `
    <div class="total-estimate-bar">
      <div><span class="label">TOTAL ESTIMATE</span><div class="amount">${formatMoney(total, curr, sym)}</div></div>
      ${d.error_margin != null ? '<span class="risk-badge">Margin ±' + (d.error_margin * 100) + '%</span>' : ''}
    </div>
    <div class="result-tabs">
      <button type="button" class="tab active" data-tab="quote">Quote</button>
      <button type="button" class="tab" data-tab="hardware">Hardware</button>
      <button type="button" class="tab" data-tab="strategy">Strategy</button>
    </div>
    <div id="tab-quote" class="tab-content active">
      <div class="result-summary">
        <div class="result-stat"><div class="value">${formatMoney(total, curr, sym)}</div><div class="label">Total Cost</div></div>
        <div class="result-stat"><div class="value">${roi}%</div><div class="label">ROI</div></div>
        <div class="result-stat"><div class="value">${payback}</div><div class="label">Payback (mo)</div></div>
        ${d.feasible_premises != null ? `<div class="result-stat"><div class="value">${d.feasible_premises}</div><div class="label">Feasible Premises</div></div>` : ''}
      </div>
      <div class="roi-payback-section">
        <div class="card-title">ROI &amp; Payback</div>
        <div class="roi-payback-grid">
          <div class="roi-row"><span class="roi-label">Total Investment</span><span class="roi-value">${formatMoney(total, curr, sym)}</span></div>
          <div class="roi-row"><span class="roi-label">Annual Revenue</span><span class="roi-value">${formatMoney(d.annual_revenue, curr, sym)}</span></div>
          <div class="roi-row"><span class="roi-label">Annual OPEX</span><span class="roi-value">${formatMoney(d.annual_opex, curr, sym)}</span></div>
          <div class="roi-row"><span class="roi-label">Net Annual</span><span class="roi-value">${formatMoney(d.net_annual, curr, sym)}</span></div>
          <div class="roi-row"><span class="roi-label">Payback</span><span class="roi-value">${payback} months</span></div>
          <div class="roi-row"><span class="roi-label">ROI</span><span class="roi-value">${roi}%</span></div>
        </div>
        ${d.roi_payback_explanation ? `<div class="roi-payback-explanation">${escapeHtml(d.roi_payback_explanation)}</div>` : ''}
      </div>
      <div class="card-title">Cost Breakdown</div>
      <div class="chart-container"><canvas id="result-chart-canvas"></canvas></div>
    </div>
    <div id="tab-hardware" class="tab-content">
      <div class="card-title">Items required for field engineers</div>
      <ul class="hardware-list">
        <li><span class="item-desc">Single-Mode Fiber (includes slack)</span><span class="item-qty">${(quantities.fiber_km || 0) * 1000}m</span></li>
        <li><span class="item-desc">Splitters (1:32)</span><span class="item-qty">${quantities.splitters_1_32 || 0} Unit(s)</span></li>
        <li><span class="item-desc">OLT ports</span><span class="item-qty">${quantities.olt_ports || 0}</span></li>
        <li><span class="item-desc">ONTs</span><span class="item-qty">${quantities.onts || 0} Unit(s)</span></li>
        <li><span class="item-desc">Splice Enclosure / Cabinets</span><span class="item-qty">${quantities.cabinets || 0} Unit(s)</span></li>
      </ul>
    </div>
    <div id="tab-strategy" class="tab-content">
      ${d.deployment_strategy ? `<div class="card-title">Deployment Strategy</div><div class="explanation-box">${escapeHtml(d.deployment_strategy)}</div>` : ''}
      ${(d.optimization_suggestions && d.optimization_suggestions.length) ? `<div class="card-title" style="margin-top:16px">Cost Optimization</div><p class="optimization-intro">Ways to reduce deployment cost:</p><ul class="suggestions-list">${d.optimization_suggestions.map(s => '<li>' + escapeHtml(String(s).trim()) + '</li>').join('')}</ul>` : ''}
      ${d.llm_explanation ? `<div class="card-title" style="margin-top:16px">Explanation</div><div class="explanation-box">${escapeHtml(d.llm_explanation)}</div>` : ''}
    </div>
  `;
  if (agentLog && agentLog.length) {
    html += '<div class="agent-log">' + agentLog.map(l => {
      const idx = l.indexOf(']');
      if (idx > 0) {
        const agent = l.slice(0, idx + 1);
        const msg = l.slice(idx + 1).trim();
        return '<div class="log-line"><span class="log-agent">' + escapeHtml(agent) + '</span> ' + escapeHtml(msg) + '</div>';
      }
      return '<div class="log-line">' + escapeHtml(l) + '</div>';
    }).join('') + '</div>';
  }
  html += '<button type="button" class="btn btn-secondary btn-save-project" style="margin-top:16px">Save to Projects</button>';
  return html;
}

function renderResult(containerId, data, options) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const d = data || {};
  if (!d.currency || !d.currency_symbol) {
    const syms = { USD: '$', INR: '₹', GBP: '£', EUR: '€' };
    const reqCurr = (window.lastEstimationInputs && window.lastEstimationInputs.currency) || 'INR';
    d.currency = d.currency || reqCurr;
    d.currency_symbol = d.currency_symbol || syms[d.currency] || '₹';
  }
  const breakdown = d.cost_breakdown || {};
  const total = d.total_cost != null ? d.total_cost : 0;
  const roi = d.roi != null ? d.roi : 0;
  const payback = d.payback_period_months != null ? d.payback_period_months : 0;
  const quantities = d.quantities || {};
  const chartData = d.charts_data || { breakdown_labels: Object.keys(breakdown), breakdown_values: Object.values(breakdown) };
  const agentLog = d.agent_log || [];
  container.innerHTML = buildResultHtml(d, quantities, chartData, total, roi, payback, agentLog);
  container.querySelector('.btn-save-project')?.addEventListener('click', saveCurrentProject);
  container.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', function () {
      container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      container.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      this.classList.add('active');
      const content = document.getElementById('tab-' + this.dataset.tab);
      if (content) content.classList.add('active');
    });
  });
  const canvas = document.getElementById('result-chart-canvas');
  if (canvas && chartData.breakdown_labels && chartData.breakdown_values && chartData.breakdown_values.length) {
    if (resultChart) resultChart.destroy();
    resultChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: chartData.breakdown_labels,
        datasets: [{ label: 'Cost (' + (d.currency || 'INR') + ')', data: chartData.breakdown_values, backgroundColor: ['#0ea5e9','#22c55e','#eab308','#a78bfa'] }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,0.2)' }, ticks: { color: '#94a3b8' } },
          x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }
  updateSummaryCards(d);
}

// --- AI Estimator: one button runs current option ---
document.getElementById('btn-run-cost')?.addEventListener('click', async () => {
  const option = document.getElementById('btn-run-cost')?.dataset.currentOption || 'cost';
  const btn = document.getElementById('btn-run-cost');
  btn.disabled = true;
  btn.textContent = 'Running...';
  document.getElementById('estimator-result').style.display = 'none';
  try {
    let url, body;
    if (option === 'cost') {
      url = API + '/estimate/cost';
      const costParams = readCostParameters('cp-');
      body = {
        area_name: document.getElementById('cost-area').value || 'Area',
        area_type: document.getElementById('cost-area-type').value,
        total_premises: parseInt(document.getElementById('cost-premises').value, 10),
        distance_km: parseFloat(document.getElementById('cost-distance').value),
        architecture_type: document.getElementById('cost-arch').value,
        currency: 'INR',
        ...costParams
      };
    } else if (option === 'budget') {
      url = API + '/estimate/budget';
      const costParams = readCostParameters('cp-');
      body = {
        budget: parseFloat(document.getElementById('budget-amount').value),
        area_type: document.getElementById('budget-area-type').value,
        distance_km: parseFloat(document.getElementById('budget-distance').value),
        architecture_type: document.getElementById('budget-arch').value,
        currency: 'INR',
        ...costParams
      };
    } else {
      url = API + '/estimate/upgrade';
      const costParams = readCostParameters('cp-');
      body = {
        existing_network_type: document.getElementById('upgrade-existing').value,
        current_capacity: parseInt(document.getElementById('upgrade-current').value, 10),
        target_capacity: parseInt(document.getElementById('upgrade-target').value, 10),
        area_type: 'Urban',
        distance_km: parseFloat(document.getElementById('upgrade-distance').value),
        currency: 'INR',
        ...costParams
      };
    }
    const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    document.getElementById('estimator-result').style.display = 'block';
    renderResult('estimator-result-content', data);
    window.lastEstimationResult = data;
    window.lastEstimationType = option === 'cost' ? 'cost_estimation' : option === 'budget' ? 'budget_planning' : 'upgrade_planner';
    window.lastEstimationInputs = body;
  } catch (e) {
    document.getElementById('estimator-result-content').innerHTML = '<p class="error-msg">' + escapeHtml(e.message) + '</p>';
    document.getElementById('estimator-result').style.display = 'block';
  }
  btn.disabled = false;
  btn.textContent = option === 'cost' ? 'Run Estimation' : option === 'budget' ? 'Run Budget Planning' : 'Run Upgrade Plan';
});

// --- Maps Planner: Handled by maps.js ---
function initMapOnce() {
  if (window.mapsInvalidateSize) window.mapsInvalidateSize();
}

// --- Projects ---
async function loadProjects() {
  const listEl = document.getElementById('projects-list');
  const loadingEl = document.getElementById('projects-loading');
  const emptyEl = document.getElementById('projects-empty');
  listEl.innerHTML = '';
  loadingEl.style.display = 'inline-flex';
  emptyEl.style.display = 'none';
  try {
    const uid = typeof getUserId === 'function' ? getUserId() : '';
    const res = await fetch(API + '/projects?user_id=' + encodeURIComponent(uid));
    const data = await res.json();
    loadingEl.style.display = 'none';
    if (!data.projects || data.projects.length === 0) {
      emptyEl.style.display = 'block';
      return;
    }
    data.projects.forEach(p => {
      const li = document.createElement('li');
      li.innerHTML = `
        <div><strong>${escapeHtml(p.title || p.type)}</strong><div class="project-meta">${p.type} · ${p.created_at ? new Date(p.created_at).toLocaleString() : ''}</div></div>
        <div class="project-actions">
          <button type="button" class="btn btn-secondary btn-view-project" data-id="${p.id}">View</button>
          <button type="button" class="btn btn-danger btn-delete-project" data-id="${p.id}">Delete</button>
        </div>
      `;
      listEl.appendChild(li);
    });
    listEl.querySelectorAll('.btn-view-project').forEach(b => b.addEventListener('click', () => viewProject(b.dataset.id)));
    listEl.querySelectorAll('.btn-delete-project').forEach(b => b.addEventListener('click', () => deleteProject(b.dataset.id)));
  } catch (e) {
    loadingEl.style.display = 'none';
    emptyEl.style.display = 'block';
    emptyEl.textContent = 'Failed to load: ' + e.message;
  }
}

async function viewProject(id) {
  try {
    const res = await fetch(API + '/projects/' + id);
    const p = await res.json();
    if (!res.ok) throw new Error(p.detail || 'Failed');
    document.getElementById('project-detail').style.display = 'block';
    renderResult('project-detail-content', p.result, {});
    document.getElementById('project-detail-content').insertAdjacentHTML('afterbegin', '<p style="color:var(--text-muted);margin-bottom:12px"><strong>' + escapeHtml(p.title) + '</strong> · ' + (p.type || '') + ' · ' + (p.created_at ? new Date(p.created_at).toLocaleString() : '') + '</p>');
  } catch (e) {
    document.getElementById('project-detail-content').innerHTML = '<p class="error-msg">' + escapeHtml(e.message) + '</p>';
    document.getElementById('project-detail').style.display = 'block';
  }
}

async function deleteProject(id) {
  if (!confirm('Delete this project?')) return;
  try {
    await fetch(API + '/projects/' + id, { method: 'DELETE' });
    document.getElementById('project-detail').style.display = 'none';
    loadProjects();
  } catch (e) {
    alert('Delete failed: ' + e.message);
  }
}

function saveCurrentProject() {
  const title = prompt('Project title:', (window.lastEstimationType || 'Estimation') + ' - ' + new Date().toLocaleDateString());
  if (title == null) return;
  if (!window.lastEstimationResult || !window.lastEstimationInputs) { alert('No estimation to save. Run an estimation first.'); return; }
  fetch(API + '/projects/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      title: title || 'Untitled',
      type: window.lastEstimationType || 'cost_estimation',
      inputs: window.lastEstimationInputs || {},
      result: window.lastEstimationResult,
      user_id: typeof getUserId === 'function' ? getUserId() : ''
    })
  })
    .then(r => r.json())
    .then(() => { alert('Saved.'); loadProjects(); })
    .catch(e => alert('Save failed: ' + e.message));
}
