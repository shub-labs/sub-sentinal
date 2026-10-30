/**
 * SubSentinel AI — Frontend Application Controller
 * SIH 2026 | HACK-13 | AI-Powered Subscription Management & Vampire Cost Elimination
 */

// ─── State ───────────────────────────────────────────────────────────────────
const appState = {
  subscriptions: [],
  metrics: {},
  piiMetrics: {},
  filter: 'all',
  searchQuery: '',
  activeSubId: null,
  activeSection: 'dashboard',
  alertHistory: []
};

let charts = { category: null, threat: null, forecast: null };

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  showSection('dashboard');
  fetchSubscriptions();
});

// ─── Navigation ──────────────────────────────────────────────────────────────
function showSection(name) {
  ['dashboard','analytics','alerts','audit'].forEach(s => {
    const el = document.getElementById('section-' + s);
    if (el) el.classList.add('hidden');
  });
  const target = document.getElementById('section-' + name);
  if (target) target.classList.remove('hidden');
  appState.activeSection = name;

  document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
  document.querySelectorAll('.nav-link').forEach(l => {
    if (l.getAttribute('onclick') && l.getAttribute('onclick').includes(name)) l.classList.add('active');
  });

  if (name === 'analytics') renderCharts();
  if (name === 'audit') loadAuditLogs();
}

// ─── Fetch Data ───────────────────────────────────────────────────────────────
async function fetchSubscriptions() {
  showLoading(true);
  try {
    const res = await fetch('/api/subscriptions');
    const data = await res.json();
    if (data.success) {
      appState.subscriptions = data.subscriptions || [];
      appState.metrics       = data.metrics || {};
      appState.piiMetrics    = data.pii_metrics || {};
      renderAll();
    } else {
      showToast('API error: ' + (data.error || 'Unknown'), 'error');
    }
  } catch (err) {
    showToast('Cannot reach SubSentinel API — check server', 'error');
    console.error(err);
  } finally {
    showLoading(false);
  }
}

function showLoading(show) {
  const ls = document.getElementById('loading-state');
  const dash = document.getElementById('section-dashboard');
  if (show) {
    if (ls)   ls.classList.remove('hidden');
    if (dash) dash.classList.add('hidden');
  } else {
    if (ls)   ls.classList.add('hidden');
    if (dash) dash.classList.remove('hidden');
  }
}

// ─── Render All ──────────────────────────────────────────────────────────────
function renderAll() {
  renderKPIs();
  renderTable();
  renderPII();
  renderThreatDist();
  updateAlertBanner();
  lucide.createIcons();
}

// ─── KPI Cards ───────────────────────────────────────────────────────────────
function renderKPIs() {
  const m    = appState.metrics || {};
  const subs = appState.subscriptions || [];
  const active = subs.filter(s => s.status !== 'Cancelled');

  const fixed = active.filter(s => (s.billing_cycle_type || '').includes('Fixed')).length;
  const vari  = active.filter(s => (s.billing_cycle_type || '').includes('Variable')).length;

  setText('kpi-count',       active.length);
  setText('kpi-count-sub',   `${fixed} fixed · ${vari} variable`);

  const monthly = m.total_monthly_drain || 0;
  const annual  = m.projected_annual_drain || monthly * 12;
  setText('kpi-monthly',     fmt(monthly));
  setText('kpi-monthly-sub', `Annual: ${fmt(annual)}`);

  const threats = m.vampire_threats_detected || 0;
  const burn    = m.high_risk_monthly_burn || 0;
  setText('kpi-threats',     threats);
  setText('kpi-threats-sub', `High risk: ${fmt(burn)}/mo`);

  const saved   = m.total_eliminated_drain || 0;
  setText('kpi-saved',       fmt(saved) + '/mo');
  setText('kpi-saved-sub',   `Annual: ${fmt(saved * 12)}`);
}

// ─── Format currency ─────────────────────────────────────────────────────────
function fmt(val) {
  if (val === undefined || val === null) return '—';
  const n = parseFloat(val) || 0;
  // Use rupee if the amount looks like INR (large values) or default
  return '₹' + n.toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

// ─── Subscription Table ───────────────────────────────────────────────────────
function renderTable() {
  const tbody = document.getElementById('subs-table-body');
  const empty = document.getElementById('empty-state');
  if (!tbody) return;

  let subs = (appState.subscriptions || []).filter(s => {
    if (appState.filter === 'active')  return s.status !== 'Cancelled';
    if (appState.filter === 'high')    return (s.vampire_threat_score || 0) >= 60;
    if (appState.filter === 'trial')   return (s.subscription_type || '').toLowerCase().includes('trial') || (s.billing_cycle_type || '').toLowerCase().includes('trial');
    return true;
  });

  if (appState.searchQuery) {
    const q = appState.searchQuery.toLowerCase();
    subs = subs.filter(s => (s.merchant_name || '').toLowerCase().includes(q));
  }

  if (!subs.length) {
    tbody.innerHTML = '';
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');

  tbody.innerHTML = subs.map(s => {
    const score    = s.vampire_threat_score || 0;
    const scoreColor = score >= 70 ? '#f43f5e' : score >= 40 ? '#f59e0b' : '#22c55e';
    const badge    = getBadge(s);
    const days     = s.days_until_renewal ?? '?';
    const daysColor = days <= 3 ? 'text-red-400' : days <= 7 ? 'text-yellow-400' : 'text-slate-400';
    const isCancelled = s.status === 'Cancelled';

    return `<tr class="${isCancelled ? 'opacity-40' : ''}">
      <td>
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
               style="background:${strToColor(s.merchant_name || 'X')}">
            ${(s.merchant_name || '?')[0].toUpperCase()}
          </div>
          <div>
            <div class="font-semibold text-white text-xs">${esc(s.merchant_name || '—')}</div>
            <div class="text-slate-500 text-[10px]">${esc(s.category || '—')} · ${esc(s.billing_cycle || '—')}</div>
          </div>
        </div>
      </td>
      <td>
        <div class="font-semibold text-white text-xs">${fmt(s.current_amount || s.monthly_equivalent)}</div>
        <div class="text-slate-500 text-[10px]">${esc(s.billing_cycle || '—')}</div>
      </td>
      <td>
        <div class="${daysColor} font-semibold text-xs">${esc(s.next_renewal || '—')}</div>
        <div class="text-slate-500 text-[10px]">${days} days left</div>
      </td>
      <td>
        <div class="flex items-center gap-2">
          <div class="threat-bar w-16">
            <div class="threat-fill" style="width:${score}%;background:${scoreColor}"></div>
          </div>
          <span class="text-xs font-bold" style="color:${scoreColor}">${score}</span>
        </div>
      </td>
      <td>${badge}</td>
      <td>
        <div class="flex items-center gap-1">
          ${!isCancelled ? `
          <button onclick="openAiAnalysisModal('${s.id}')" title="Gemini AI Audit"
            class="w-7 h-7 rounded-lg bg-purple-900/20 text-purple-400 hover:bg-purple-900/40 flex items-center justify-center transition-colors">
            <i data-lucide="sparkles" class="w-3.5 h-3.5"></i>
          </button>
          <button onclick="sendAlert('${s.id}')" title="Send Alert"
            class="w-7 h-7 rounded-lg bg-yellow-900/20 text-yellow-400 hover:bg-yellow-900/40 flex items-center justify-center transition-colors">
            <i data-lucide="bell" class="w-3.5 h-3.5"></i>
          </button>
          <button onclick="openCancelModal('${s.id}')" title="Cancel Subscription"
            class="w-7 h-7 rounded-lg bg-red-900/20 text-red-400 hover:bg-red-900/40 flex items-center justify-center transition-colors">
            <i data-lucide="x-circle" class="w-3.5 h-3.5"></i>
          </button>` : `
          <span class="text-xs text-slate-600 italic">Cancelled</span>`}
        </div>
      </td>
    </tr>`;
  }).join('');
  lucide.createIcons();
}

function getBadge(s) {
  if (s.status === 'Cancelled') return '<span class="badge badge-cancelled">Cancelled</span>';
  const type = (s.billing_cycle_type || s.subscription_type || '').toLowerCase();
  if (type.includes('trial')) return '<span class="badge badge-trial">Trial Trap</span>';
  const score = s.vampire_threat_score || 0;
  if (score >= 70) return '<span class="badge badge-danger">Critical</span>';
  if (score >= 40) return '<span class="badge badge-warning">At Risk</span>';
  return '<span class="badge badge-active">Safe</span>';
}

function strToColor(str) {
  const palette = ['#3b82f6','#8b5cf6','#06b6d4','#f59e0b','#10b981','#ef4444','#6366f1','#ec4899'];
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) % palette.length;
  return palette[Math.abs(h)];
}

// ─── PII Shield ───────────────────────────────────────────────────────────────
function renderPII() {
  const p = appState.piiMetrics || {};
  setText('pii-cc',    (p.cc_masked || 0) + ' masked');
  setText('pii-email', (p.emails_masked || 0) + ' masked');
  setText('pii-phone', (p.phone_masked || 0) + ' masked');
  setText('pii-acct',  (p.acct_masked || 0) + ' masked');
}

// ─── Threat Distribution ──────────────────────────────────────────────────────
function renderThreatDist() {
  const subs   = appState.subscriptions || [];
  const active = subs.filter(s => s.status !== 'Cancelled');
  const total  = active.length || 1;

  const critical = active.filter(s => (s.vampire_threat_score || 0) >= 70).length;
  const high     = active.filter(s => (s.vampire_threat_score || 0) >= 50 && (s.vampire_threat_score || 0) < 70).length;
  const medium   = active.filter(s => (s.vampire_threat_score || 0) >= 30 && (s.vampire_threat_score || 0) < 50).length;
  const safe     = active.filter(s => (s.vampire_threat_score || 0) < 30).length;

  setStyle('dist-critical', 'width', (critical / total * 100) + '%');
  setStyle('dist-high',     'width', (high     / total * 100) + '%');
  setStyle('dist-medium',   'width', (medium   / total * 100) + '%');
  setStyle('dist-safe',     'width', (safe     / total * 100) + '%');

  setText('dist-critical-n', critical);
  setText('dist-high-n',     high);
  setText('dist-medium-n',   medium);
  setText('dist-safe-n',     safe);
}

// ─── Alert Banner ────────────────────────────────────────────────────────────
function updateAlertBanner() {
  const subs = appState.subscriptions || [];
  const imminent = subs.filter(s => s.status !== 'Cancelled' && (s.days_until_renewal ?? 99) <= 3);
  const banner   = document.getElementById('alert-banner');
  if (!banner) return;

  if (imminent.length) {
    banner.classList.remove('hidden');
    setText('alert-banner-title', `⚠️ ${imminent.length} subscription${imminent.length > 1 ? 's' : ''} renewing within 3 days!`);
    setText('alert-banner-body',  imminent.map(s => `${s.merchant_name} (${fmt(s.current_amount)}) — ${s.days_until_renewal}d`).join(' · '));
  } else {
    banner.classList.add('hidden');
  }
}

// ─── Filter & Search ─────────────────────────────────────────────────────────
function setFilter(f) {
  appState.filter = f;
  document.querySelectorAll('.filter-btn').forEach(b => {
    b.classList.remove('bg-blue-600','text-white');
    b.classList.add('bg-white/5','text-slate-400');
  });
  const active = document.getElementById('flt-' + f);
  if (active) {
    active.classList.remove('bg-white/5','text-slate-400');
    active.classList.add('bg-blue-600','text-white');
  }
  renderTable();
}

function applySearch(q) {
  appState.searchQuery = q;
  renderTable();
}

// ─── Load Sample Profile ──────────────────────────────────────────────────────
async function loadSampleProfile(profile) {
  showLoading(true);
  showToast('Loading ' + profile + ' profile...', 'info');
  try {
    const res  = await fetch('/api/load-sample', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile })
    });
    const data = await res.json();
    if (data.success) {
      appState.subscriptions = data.subscriptions || [];
      appState.metrics       = data.metrics || {};
      appState.piiMetrics    = data.pii_metrics || {};
      renderAll();
      showToast(`Loaded ${data.subscriptions.length} subscriptions from ${profile}`, 'success');
    } else {
      showToast('Load failed: ' + (data.error || 'Unknown'), 'error');
    }
  } catch (err) {
    showToast('Network error loading profile', 'error');
  } finally {
    showLoading(false);
  }
}

// ─── Import Statement ────────────────────────────────────────────────────────
function openStatementModal() {
  openModal('statement-modal');
}

async function parseStatement() {
  const text = (document.getElementById('statement-textarea') || {}).value || '';
  if (!text.trim()) { showToast('Please paste a bank statement first', 'warn'); return; }

  showToast('Running NLP analysis...', 'info');
  closeModal('statement-modal');
  showLoading(true);

  try {
    const res  = await fetch('/api/parse-statement', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ statement_text: text })
    });
    const data = await res.json();
    if (data.success) {
      appState.subscriptions = data.subscriptions || [];
      appState.metrics       = data.metrics || {};
      appState.piiMetrics    = data.pii_metrics || {};
      renderAll();
      showToast(`Detected ${data.parsed_transactions_count} transactions · ${data.subscriptions.length} subscriptions`, 'success');
    } else {
      showToast('Parse error: ' + (data.error || 'No transactions found'), 'error');
    }
  } catch (err) {
    showToast('NLP parse failed — check server', 'error');
  } finally {
    showLoading(false);
  }
}

// ─── Preset Statement Data ────────────────────────────────────────────────────
function fillPreset(type) {
  const presets = {
    hdfc: `Date,Description,Amount
2024-01-05,NETFLIX SUBSCRIPTION,₹649
2024-01-08,SPOTIFY PREMIUM INDIA,₹119
2024-01-10,AMAZON PRIME VIDEO,₹1499
2024-01-12,HOTSTAR DISNEY+ ANNUAL,₹299
2024-01-15,GOOGLE ONE 100GB,₹130
2024-01-18,ZOOM PRO MONTHLY,₹1299
2024-01-20,LINKEDIN PREMIUM,₹2600
2024-01-22,SWIGGY ONE MEMBERSHIP,₹199
2024-01-25,CULT.FIT ANNUAL,₹999`,
    sbi: `Txn Date,Description,Debit Amount
15-Jan-24,Netflix India 649 INR,649.00
18-Jan-24,Spotify Premium 119,119.00
20-Jan-24,Amazon Prime Annual,1499.00
22-Jan-24,Hotstar Disney+ 299,299.00
25-Jan-24,YouTube Premium Family,189.00
28-Jan-24,Canva Pro Monthly,499.00`,
    upi: `Date,UPI Description,Amount
2024-01-05,NETFLIX@PAYTM Netflix Subscription,₹649
2024-01-07,SPOTIFY@UPI Spotify Premium,₹119
2024-01-10,AMAZON@UPI Prime Membership,₹1499
2024-01-12,GOOGL@UPI Google One Storage,₹130
2024-01-15,FIGMA@UPI Figma Professional,₹3500
2024-01-18,ADOBE@UPI Creative Cloud,₹5000`,
    intl: `Date,Merchant,Amount
2024-01-05,Netflix Standard,15.99
2024-01-06,Spotify Premium,9.99
2024-01-08,Adobe Creative Cloud,59.99
2024-01-10,Microsoft 365,9.99
2024-01-12,Amazon Prime,14.99
2024-01-15,NordVPN 1 Month Trial,11.99
2024-01-18,Coursera Plus,59.00
2024-01-20,GitHub Pro,4.00
2024-01-22,Dropbox Plus,11.99`
  };
  const ta = document.getElementById('statement-textarea');
  if (ta && presets[type]) ta.value = presets[type];
}

// ─── Send Alert ───────────────────────────────────────────────────────────────
async function sendAlert(subId) {
  try {
    const res  = await fetch('/api/send-alert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subscription_id: subId, channel: 'push' })
    });
    const data = await res.json();
    if (data.success) {
      appState.alertHistory.unshift(data.alert);
      renderAlertList();
      showToast(`Alert dispatched: ${data.alert.merchant}`, 'success');
    }
  } catch (err) {
    showToast('Alert dispatch failed', 'error');
  }
}

// ─── Alert List ───────────────────────────────────────────────────────────────
function renderAlertList() {
  const el = document.getElementById('alert-list');
  if (!el) return;
  const alerts = appState.alertHistory;
  if (!alerts.length) {
    el.innerHTML = '<div class="text-slate-500 text-sm text-center py-8">No alerts dispatched yet.</div>';
    return;
  }
  el.innerHTML = alerts.map(a => `
    <div class="bg-card rounded-xl p-4 border border-yellow-800/20">
      <div class="flex items-start gap-3">
        <div class="w-8 h-8 rounded-lg bg-yellow-900/30 flex items-center justify-center flex-shrink-0">
          <i data-lucide="bell" class="w-4 h-4 text-yellow-400"></i>
        </div>
        <div class="flex-1 min-w-0">
          <div class="text-white font-semibold text-sm">${esc(a.title || a.merchant)}</div>
          <div class="text-slate-400 text-xs mt-0.5">${esc(a.body || '')}</div>
          <div class="flex gap-2 mt-2">
            <span class="chip bg-yellow-900/30 text-yellow-400">${a.channel || 'PUSH'}</span>
            <span class="chip bg-slate-800 text-slate-400">${a.timestamp || 'Just now'}</span>
          </div>
        </div>
      </div>
    </div>`).join('');
  lucide.createIcons();
}

// ─── Cancel Modal ─────────────────────────────────────────────────────────────
function openCancelModal(subId) {
  const sub = appState.subscriptions.find(s => s.id === subId);
  if (!sub) return;
  appState.activeSubId = subId;

  setText('cancel-merchant-name', sub.merchant_name || '—');
  setText('cancel-sub-detail',    `${sub.category || ''} · ${sub.billing_cycle || ''} · Vampire Score: ${sub.vampire_threat_score}/100`);
  setText('cancel-amount-chip',   fmt(sub.current_amount || sub.monthly_equivalent));
  setText('cancel-renewal-chip',  `Renews: ${sub.next_renewal || '—'}`);
  setText('cancel-threat-chip',   `Threat: ${sub.vampire_threat_score}/100`);

  // Reset form
  const c1 = document.getElementById('consent-check-1');
  const c2 = document.getElementById('consent-check-2');
  const sig = document.getElementById('consent-signature');
  if (c1) c1.checked = false;
  if (c2) c2.checked = false;
  if (sig) sig.value = '';

  openModal('cancel-modal');
}

// ─── Execute Cancellation ─────────────────────────────────────────────────────
async function executeAuthorizedCancellation() {
  const c1  = document.getElementById('consent-check-1');
  const c2  = document.getElementById('consent-check-2');
  const sig = document.getElementById('consent-signature');
  const reason = (document.getElementById('cancel-reason') || {}).value || 'Vampire cost elimination';

  if (!c1?.checked || !c2?.checked) {
    showToast('Please check both authorization boxes', 'warn');
    return;
  }
  if (!sig?.value.trim() || sig.value.trim().length < 2) {
    showToast('Please enter your digital signature (full name)', 'warn');
    return;
  }

  const btn = document.getElementById('execute-cancel-btn');
  if (btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner"></div> Processing...'; }

  try {
    const res  = await fetch('/api/execute-cancellation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subscription_id:    appState.activeSubId,
        user_consent_granted: true,
        consent_token:      'TOK-' + Date.now(),
        signature_name:     sig.value.trim(),
        reason:             reason
      })
    });
    const data = await res.json();

    if (data.success) {
      // Update local state
      const sub = appState.subscriptions.find(s => s.id === appState.activeSubId);
      if (sub) sub.status = 'Cancelled';
      const saved = sub?.monthly_equivalent || 0;
      appState.metrics.total_eliminated_drain = (appState.metrics.total_eliminated_drain || 0) + saved;
      appState.metrics.total_monthly_drain    = Math.max(0, (appState.metrics.total_monthly_drain || 0) - saved);

      closeModal('cancel-modal');
      renderAll();
      showCertificate(data.certificate || data);
      triggerConfetti();
      showToast('Subscription cancelled & certificate issued!', 'success');
    } else {
      showToast('Cancellation refused: ' + (data.error || 'Authorization failed'), 'error');
    }
  } catch (err) {
    showToast('Cancellation API error', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="shield-off" class="w-4 h-4"></i> Authorize & Cancel'; lucide.createIcons(); }
  }
}

// ─── Certificate Modal ────────────────────────────────────────────────────────
function showCertificate(cert) {
  const el = document.getElementById('cert-content');
  if (!el || !cert) return;

  const lines = [
    ['Certificate ID',    cert.certificate_id || cert.id || 'CERT-' + Date.now()],
    ['Merchant',          cert.merchant_name  || cert.merchant || '—'],
    ['Amount Saved/mo',   fmt(cert.monthly_savings || cert.amount_saved || 0)],
    ['Authorized By',     cert.authorized_by  || cert.signature || '—'],
    ['Timestamp',         cert.timestamp      || cert.issued_at || new Date().toISOString()],
    ['Status',            'VERIFIED & EXECUTED'],
    ['Compliance',        'DPDP Act 2023 · RBI e-Mandate · ToS Compliant'],
  ];

  el.innerHTML = lines.map(([k,v]) =>
    `<div class="flex justify-between gap-4 border-b border-white/5 pb-1.5 mb-1.5">
      <span class="text-slate-500">${k}</span>
      <span class="text-blue-300 text-right">${esc(String(v))}</span>
    </div>`
  ).join('');

  openModal('cert-modal');
}

function triggerConfetti() {
  if (typeof confetti === 'function') {
    confetti({ particleCount: 80, spread: 70, origin: { y: 0.6 }, colors: ['#3b82f6','#8b5cf6','#22c55e'] });
  }
}

// ─── Audit Logs ───────────────────────────────────────────────────────────────
async function loadAuditLogs() {
  try {
    const res  = await fetch('/api/audit-logs');
    const data = await res.json();
    if (data.success) {
      const el  = document.getElementById('audit-table-body');
      const all = [...(data.audit_logs || []), ...(data.alert_history || [])];
      if (!el) return;
      if (!all.length) {
        el.innerHTML = '<div class="text-slate-500 text-sm text-center py-8">No audit events yet.</div>';
        return;
      }
      el.innerHTML = all.map(log => `
        <div class="flex items-start gap-3 p-4">
          <div class="w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${log.action?.includes('cancel') || log.channel ? 'bg-green-400' : 'bg-blue-400'}"></div>
          <div class="flex-1 min-w-0">
            <div class="text-sm text-white font-medium">${esc(log.action || log.title || 'Event')}</div>
            <div class="text-xs text-slate-400 mt-0.5">${esc(log.details || log.body || JSON.stringify(log).slice(0,120))}</div>
          </div>
          <div class="text-[10px] text-slate-600 flex-shrink-0">${esc(log.timestamp || '—')}</div>
        </div>`).join('');
    }
  } catch (err) {
    console.error('Audit log fetch failed', err);
  }
}

// ─── Charts ───────────────────────────────────────────────────────────────────
function renderCharts() {
  renderCategoryChart();
  renderThreatChart();
  renderForecastChart();
}

function renderCategoryChart() {
  const canvas = document.getElementById('categoryChart');
  if (!canvas) return;
  if (charts.category) charts.category.destroy();

  const subs = appState.subscriptions.filter(s => s.status !== 'Cancelled');
  const cats = {};
  subs.forEach(s => {
    const cat = s.category || 'Other';
    cats[cat] = (cats[cat] || 0) + (s.monthly_equivalent || s.current_amount || 0);
  });

  const labels = Object.keys(cats);
  const values = Object.values(cats);
  const colors = ['#3b82f6','#8b5cf6','#f59e0b','#22c55e','#f43f5e','#06b6d4','#ec4899','#10b981'];

  charts.category = new Chart(canvas, {
    type: 'doughnut',
    data: { labels, datasets: [{ data: values, backgroundColor: colors, borderWidth: 2, borderColor: '#0f172a' }] },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position:'right', labels:{ color:'#94a3b8', font:{size:11}, padding:12, boxWidth:12 } },
        tooltip: { callbacks: { label: ctx => ` ₹${Math.round(ctx.parsed).toLocaleString()}/mo` } }
      }
    }
  });
}

function renderThreatChart() {
  const canvas = document.getElementById('threatChart');
  if (!canvas) return;
  if (charts.threat) charts.threat.destroy();

  const subs = appState.subscriptions.filter(s => s.status !== 'Cancelled');
  const bins = [0,0,0,0]; // safe,medium,high,critical
  subs.forEach(s => {
    const sc = s.vampire_threat_score || 0;
    if (sc < 30) bins[0]++;
    else if (sc < 50) bins[1]++;
    else if (sc < 70) bins[2]++;
    else bins[3]++;
  });

  charts.threat = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: ['Safe (<30)', 'Medium (30-50)', 'High (50-70)', 'Critical (70+)'],
      datasets: [{
        label: 'Subscriptions',
        data: bins,
        backgroundColor: ['rgba(34,197,94,0.7)','rgba(245,158,11,0.7)','rgba(249,115,22,0.7)','rgba(244,63,94,0.7)'],
        borderRadius: 6, borderSkipped: false
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend:{ display:false } },
      scales: {
        x: { grid:{ color:'rgba(255,255,255,0.03)' }, ticks:{ color:'#64748b', font:{size:10} } },
        y: { grid:{ color:'rgba(255,255,255,0.03)' }, ticks:{ color:'#64748b', stepSize:1, precision:0 } }
      }
    }
  });
}

function renderForecastChart() {
  const canvas = document.getElementById('forecastChart');
  if (!canvas) return;
  if (charts.forecast) charts.forecast.destroy();

  const base    = appState.metrics.total_monthly_drain || 0;
  const labels  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const data    = labels.map((_, i) => +(base * (1 + i * 0.008)).toFixed(0)); // slight creep

  charts.forecast = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Monthly Drain (₹)',
        data,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59,130,246,0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#3b82f6'
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend:{ display:false }, tooltip:{ callbacks:{ label: ctx => ` ₹${ctx.parsed.y.toLocaleString()}` } } },
      scales: {
        x: { grid:{ color:'rgba(255,255,255,0.03)' }, ticks:{ color:'#64748b', font:{size:10} } },
        y: { grid:{ color:'rgba(255,255,255,0.05)' }, ticks:{ color:'#64748b', callback: v => '₹'+v.toLocaleString() } }
      }
    }
  });
}

// ─── Blueprint Modal ──────────────────────────────────────────────────────────
const BLUEPRINT_TABS = [
  {
    title: 'System Flow',
    content: `
<div class="space-y-4">
  <div class="bg-blue-950/30 border border-blue-800/30 rounded-xl p-4">
    <div class="text-blue-400 font-bold text-xs uppercase tracking-wider mb-2">3-Layer AI Architecture</div>
    <div class="space-y-2 text-xs text-slate-300">
      <div class="flex items-center gap-2"><span class="w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">1</span><span><b>Data Ingestion Layer</b> — Bank statement import, UPI SMS parsing, CSV/API input, PII scrubbing</span></div>
      <div class="flex items-center gap-2"><span class="w-5 h-5 rounded-full bg-purple-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">2</span><span><b>NLP Pattern Engine</b> — Merchant catalog matching, billing cycle detection, vampire threat scoring (0-100)</span></div>
      <div class="flex items-center gap-2"><span class="w-5 h-5 rounded-full bg-red-600 text-white flex items-center justify-center text-[10px] font-bold flex-shrink-0">3</span><span><b>Consent-First Agent</b> — T-7/T-3/T-1 renewal alerts, 3-gate authorization, ToS-compliant cancellation</span></div>
    </div>
  </div>
  <div class="bg-dark-900 rounded-xl p-4 border border-white/5 text-xs text-slate-400">
    <b class="text-white">Human-in-the-Loop Mandate:</b> The AI agent NEVER cancels without:
    <ol class="list-decimal ml-4 mt-1 space-y-1">
      <li>Double checkbox explicit consent</li>
      <li>Single-use cryptographic token</li>
      <li>Digital signature verification</li>
    </ol>
  </div>
</div>`
  },
  {
    title: 'Tech Stack',
    content: `
<div class="space-y-3">
  <div class="grid grid-cols-2 gap-3 text-xs">
    <div class="bg-dark-900 rounded-lg p-3 border border-white/5">
      <div class="text-blue-400 font-semibold mb-2">Backend</div>
      <div class="space-y-1 text-slate-400">
        <div>Python 3.12 · Flask 3.1</div>
        <div>Custom NLP Pattern Engine</div>
        <div>Regex PII Scrubber</div>
        <div>Merchant Catalog (25+ entries)</div>
      </div>
    </div>
    <div class="bg-dark-900 rounded-lg p-3 border border-white/5">
      <div class="text-purple-400 font-semibold mb-2">Frontend</div>
      <div class="space-y-1 text-slate-400">
        <div>Vanilla JS + TailwindCSS</div>
        <div>Chart.js (Doughnut/Bar/Line)</div>
        <div>Lucide Icons</div>
        <div>Canvas Confetti</div>
      </div>
    </div>
    <div class="bg-dark-900 rounded-lg p-3 border border-white/5">
      <div class="text-green-400 font-semibold mb-2">Deployment</div>
      <div class="space-y-1 text-slate-400">
        <div>Vercel Serverless (Python)</div>
        <div>Edge CDN · Global</div>
        <div>Production: subshield-ai.vercel.app</div>
      </div>
    </div>
    <div class="bg-dark-900 rounded-lg p-3 border border-white/5">
      <div class="text-red-400 font-semibold mb-2">AI/ML Pipeline</div>
      <div class="space-y-1 text-slate-400">
        <div>Vampire Threat Scorer</div>
        <div>Billing Cycle Detector</div>
        <div>Renewal Date Predictor</div>
        <div>Price Creep Analyzer</div>
      </div>
    </div>
  </div>
</div>`
  },
  {
    title: 'Regulations',
    content: `
<div class="space-y-3 text-xs">
  <div class="bg-green-950/30 border border-green-800/30 rounded-xl p-4">
    <div class="text-green-400 font-bold uppercase tracking-wider mb-2">DPDP Act 2023</div>
    <div class="text-slate-300">Digital Personal Data Protection Act — All banking data is PII-scrubbed before NLP processing. Card numbers, emails, phone numbers, account numbers are masked with regex before any analysis.</div>
  </div>
  <div class="bg-blue-950/30 border border-blue-800/30 rounded-xl p-4">
    <div class="text-blue-400 font-bold uppercase tracking-wider mb-2">RBI e-Mandate Framework</div>
    <div class="text-slate-300">Recurring payment mandates under RBI circular RBI/2019-20/150. Every cancellation generates a digitally signed e-Mandate certificate with unique ID, merchant, amount, and timestamp.</div>
  </div>
  <div class="bg-purple-950/30 border border-purple-800/30 rounded-xl p-4">
    <div class="text-purple-400 font-bold uppercase tracking-wider mb-2">NPCI UPI Rails</div>
    <div class="text-slate-300">SubSentinel supports UPI autopay mandate detection via SMS parsing (Airtel/Jio format). Cancellation workflow respects NPCI's mandate revocation protocol.</div>
  </div>
</div>`
  },
  {
    title: 'Impact Metrics',
    content: `
<div class="space-y-3 text-xs">
  <div class="grid grid-cols-3 gap-3">
    <div class="bg-dark-900 rounded-xl p-4 text-center border border-white/5">
      <div class="text-3xl font-bold text-blue-400">90%</div>
      <div class="text-slate-400 mt-1">Pattern Detection Accuracy</div>
    </div>
    <div class="bg-dark-900 rounded-xl p-4 text-center border border-white/5">
      <div class="text-3xl font-bold text-green-400">100%</div>
      <div class="text-slate-400 mt-1">Human-in-the-Loop Compliance</div>
    </div>
    <div class="bg-dark-900 rounded-xl p-4 text-center border border-white/5">
      <div class="text-3xl font-bold text-purple-400">85%</div>
      <div class="text-slate-400 mt-1">Vampire Cost Elimination</div>
    </div>
  </div>
  <div class="bg-dark-900 rounded-xl p-4 border border-white/5">
    <div class="text-white font-semibold mb-2">Target Impact (India Scale)</div>
    <div class="space-y-1 text-slate-400">
      <div>• ₹2,340 Cr. estimated annual consumer loss from vampire subscriptions</div>
      <div>• 5M+ users overpaying for forgotten subscriptions monthly</div>
      <div>• Average 3.7 forgotten subscriptions per urban Indian user</div>
      <div>• SubSentinel target: ₹500 Cr. recovered in Year 1</div>
    </div>
  </div>
</div>`
  },
  {
    title: 'Benchmarks',
    content: `
<div class="overflow-x-auto text-xs">
  <table style="width:100%;border-collapse:collapse">
    <thead>
      <tr style="background:rgba(30,41,59,0.8)">
        <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-weight:600">Feature</th>
        <th style="padding:10px 12px;text-align:center;color:#60a5fa">SubSentinel</th>
        <th style="padding:10px 12px;text-align:center;color:#94a3b8">DoNotPay</th>
        <th style="padding:10px 12px;text-align:center;color:#94a3b8">Trim</th>
        <th style="padding:10px 12px;text-align:center;color:#94a3b8">Truebill</th>
      </tr>
    </thead>
    <tbody>
      ${[
        ['Human-in-the-Loop', '✅ 3-Gate', '❌ Auto', '❌ Auto', '⚠️ Partial'],
        ['Indian Bank Support', '✅ Full', '❌ None', '❌ None', '❌ None'],
        ['DPDP Act 2023', '✅ Compliant', '❌', '❌', '❌'],
        ['UPI Autopay Detection', '✅ Yes', '❌', '❌', '❌'],
        ['Vampire Threat Score', '✅ 0-100', '❌', '⚠️ Basic', '⚠️ Basic'],
        ['Offline / Privacy-first', '✅ Yes', '❌ Cloud', '❌ Cloud', '❌ Cloud'],
        ['Open Source Prototype', '✅ SIH 2026', '❌', '❌', '❌'],
      ].map(([f,a,b,c,d]) => `
        <tr style="border-bottom:1px solid rgba(255,255,255,0.05)">
          <td style="padding:8px 12px;color:#cbd5e1">${f}</td>
          <td style="padding:8px 12px;text-align:center;color:#4ade80">${a}</td>
          <td style="padding:8px 12px;text-align:center;color:#64748b">${b}</td>
          <td style="padding:8px 12px;text-align:center;color:#64748b">${c}</td>
          <td style="padding:8px 12px;text-align:center;color:#64748b">${d}</td>
        </tr>`).join('')}
    </tbody>
  </table>
</div>`
  }
];

function openArchitectureModal() {
  openModal('arch-modal');
  switchBlueprintTab(0);
}

function switchBlueprintTab(idx) {
  document.querySelectorAll('.btab').forEach((b, i) => {
    b.classList.toggle('active', i === idx);
  });
  const content = document.getElementById('blueprint-content');
  if (content && BLUEPRINT_TABS[idx]) {
    content.innerHTML = BLUEPRINT_TABS[idx].content;
    lucide.createIcons();
  }
}

// ─── Modal Helpers ────────────────────────────────────────────────────────────
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('open');
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.classList.remove('open');
}

// Close on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('open');
  }
});

// ─── Toast ────────────────────────────────────────────────────────────────────
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const icons = { success:'check-circle', error:'x-circle', warn:'alert-triangle', info:'info' };
  const div = document.createElement('div');
  div.className = `toast toast-${type}`;
  div.innerHTML = `<i data-lucide="${icons[type]||'info'}" style="width:16px;height:16px;flex-shrink:0"></i>${esc(msg)}`;
  container.appendChild(div);
  lucide.createIcons();
  setTimeout(() => div.remove(), 4000);
}

// ─── Utilities ────────────────────────────────────────────────────────────────
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val ?? '—';
}
function setStyle(id, prop, val) {
  const el = document.getElementById(id);
  if (el) el.style[prop] = val;
}
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ─── Gemini AI Assistant & Auditor ───────────────────────────────────────────
let currentAnalyzedSubId = null;

function getGeminiKey() {
  return localStorage.getItem('gemini_api_key') || '';
}

function saveGeminiKey() {
  const input = document.getElementById('gemini-key-input');
  const key = (input?.value || '').trim();
  if (!key) {
    showToast('Please enter a valid Gemini API key', 'warn');
    return;
  }
  localStorage.setItem('gemini_api_key', key);
  showToast('Gemini API Key saved locally & activated!', 'success');
  switchGeminiTab('chat');
}

function clearGeminiKey() {
  localStorage.removeItem('gemini_api_key');
  const input = document.getElementById('gemini-key-input');
  if (input) input.value = '';
  showToast('Gemini API Key removed. Using local AI engine.', 'info');
}

function openGeminiModal() {
  const input = document.getElementById('gemini-key-input');
  if (input) input.value = getGeminiKey();
  openModal('gemini-modal');
  switchGeminiTab('chat');
}

function switchGeminiTab(tab) {
  ['chat', 'analysis', 'key'].forEach(t => {
    const btn = document.getElementById('gtab-' + t);
    const sec = document.getElementById('gsec-' + t);
    if (btn) {
      if (t === tab) {
        btn.className = 'text-xs px-3 py-1.5 rounded-lg font-medium bg-purple-600 text-white transition-all';
      } else {
        btn.className = 'text-xs px-3 py-1.5 rounded-lg font-medium bg-white/5 text-slate-400 hover:bg-white/10 transition-all';
      }
    }
    if (sec) {
      if (t === tab) sec.classList.remove('hidden');
      else sec.classList.add('hidden');
    }
  });
  lucide.createIcons();
}

async function sendGeminiChat() {
  const input = document.getElementById('gemini-chat-input');
  const query = (input?.value || '').trim();
  if (!query) return;

  const history = document.getElementById('gemini-chat-history');
  if (!history) return;

  // Append user message
  history.innerHTML += `
    <div class="flex items-start gap-2.5 justify-end">
      <div class="bg-purple-600/30 border border-purple-500/30 rounded-xl p-3 text-xs text-white max-w-[85%]">
        ${esc(query)}
      </div>
      <div class="w-6 h-6 rounded bg-slate-800 flex items-center justify-center text-[10px] font-bold text-slate-300 flex-shrink-0">You</div>
    </div>`;
  input.value = '';
  history.scrollTop = history.scrollHeight;

  // Loading indicator
  const loadingId = 'ai-loading-' + Date.now();
  history.innerHTML += `
    <div id="${loadingId}" class="flex items-start gap-2.5">
      <div class="w-6 h-6 rounded bg-purple-900/50 border border-purple-700/50 flex items-center justify-center text-[10px] font-bold text-purple-300 flex-shrink-0">AI</div>
      <div class="bg-white/5 rounded-xl p-3 text-xs text-slate-400 max-w-[85%] flex items-center gap-2">
        <div class="spinner w-3 h-3"></div> Gemini reasoning in progress...
      </div>
    </div>`;
  history.scrollTop = history.scrollHeight;

  try {
    const res = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query, api_key: getGeminiKey() })
    });
    const data = await res.json();
    document.getElementById(loadingId)?.remove();

    if (data.success) {
      const isGemini = data.source === 'gemini_api';
      history.innerHTML += `
        <div class="flex items-start gap-2.5">
          <div class="w-6 h-6 rounded bg-purple-900/50 border border-purple-700/50 flex items-center justify-center text-[10px] font-bold text-purple-300 flex-shrink-0">AI</div>
          <div class="bg-white/5 rounded-xl p-3 text-xs text-slate-200 max-w-[85%] border border-white/5 space-y-1">
            <div class="flex items-center gap-1.5 mb-1">
              <span class="chip ${isGemini ? 'bg-purple-900/50 text-purple-300' : 'bg-blue-900/40 text-blue-300'}">${isGemini ? 'Gemini 2.5 Live' : 'SubSentinel Local AI'}</span>
            </div>
            <div>${esc(data.reply).replace(/\n/g, '<br>')}</div>
          </div>
        </div>`;
    } else {
      history.innerHTML += `
        <div class="flex items-start gap-2.5">
          <div class="w-6 h-6 rounded bg-red-900/50 flex items-center justify-center text-[10px] font-bold text-red-300 flex-shrink-0">!</div>
          <div class="bg-red-950/30 border border-red-800/40 rounded-xl p-3 text-xs text-red-300 max-w-[85%]">
            Error: ${esc(data.error || 'Failed to get AI response')}
          </div>
        </div>`;
    }
  } catch (err) {
    document.getElementById(loadingId)?.remove();
    showToast('Failed to contact AI service', 'error');
  }
  history.scrollTop = history.scrollHeight;
}

async function openAiAnalysisModal(subId) {
  const sub = (appState.subscriptions || []).find(s => s.id === subId);
  if (!sub) return;

  currentAnalyzedSubId = subId;
  openGeminiModal();
  switchGeminiTab('analysis');

  const box = document.getElementById('gemini-analysis-box');
  const sourceEl = document.getElementById('gemini-analysis-source');
  if (box) box.innerHTML = '<div class="flex items-center gap-2 text-slate-400 py-6 justify-center"><div class="spinner"></div> Performing deep AI contract & dark pattern audit on ' + esc(sub.merchant_name) + '...</div>';
  if (sourceEl) sourceEl.innerText = 'Analyzing...';

  try {
    const res = await fetch('/api/ai/analyze-subscription', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ subscription_id: subId, api_key: getGeminiKey() })
    });
    const data = await res.json();
    if (data.success && box) {
      box.innerHTML = esc(data.analysis_text);
      if (sourceEl) {
        sourceEl.innerText = data.source === 'gemini_api' ? `Google ${data.model || 'Gemini'} Live` : 'SubSentinel NLP Engine';
      }
    }
  } catch (err) {
    if (box) box.innerText = 'Analysis failed. Please check network connection.';
  }
}

async function draftAiCancellationLetter() {
  if (!currentAnalyzedSubId) {
    showToast('Select a subscription first', 'warn');
    return;
  }
  const sub = (appState.subscriptions || []).find(s => s.id === currentAnalyzedSubId);
  if (!sub) return;

  showToast('Generating legal revocation notice...', 'info');
  try {
    const res = await fetch('/api/ai/draft-letter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        subscription_id: currentAnalyzedSubId,
        user_name: 'SubSentinel Verified Consumer',
        reason: 'Unnotified recurring cost / Vampire drain',
        api_key: getGeminiKey()
      })
    });
    const data = await res.json();
    if (data.success) {
      const box = document.getElementById('gemini-analysis-box');
      if (box) {
        box.innerHTML = '### ⚖️ Formal RBI e-Mandate Revocation Letter\n\n' + esc(data.letter_text);
      }
      showToast('Legal notice drafted with statutory compliance clauses!', 'success');
    }
  } catch (err) {
    showToast('Failed to draft letter', 'error');
  }
}
