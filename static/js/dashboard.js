/**
 * Main Dashboard controller
 */
const Dashboard = {
  selectedServiceId: null,
  pollIntervalId: null,
  pollFrequencyMs: 2000,
  audioAlertsEnabled: false,
  alertFilter: 'ACTIVE',
  knownAlertIds: new Set(),
  theme: 'dark',

  init() {
    this.loadPreferences();
    MonitoringCharts.init();
    SimulatorUI.init();
    this.bindEvents();
    this.refresh();
    this.startPolling();
  },

  loadPreferences() {
    const savedTheme = localStorage.getItem('sla_theme') || 'dark';
    this.setTheme(savedTheme);
  },

  setTheme(theme) {
    this.theme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sla_theme', theme);
    const themeBtn = document.getElementById('btnThemeToggle');
    if (themeBtn) {
      themeBtn.innerHTML = theme === 'dark' ? '☀️ Light' : '🌙 Dark';
    }
  },

  bindEvents() {
    // Theme toggle
    const themeBtn = document.getElementById('btnThemeToggle');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        this.setTheme(this.theme === 'dark' ? 'light' : 'dark');
      });
    }

    // Refresh interval selector
    const refreshSelect = document.getElementById('selectRefreshInterval');
    if (refreshSelect) {
      refreshSelect.addEventListener('change', (e) => {
        const val = parseInt(e.target.value);
        if (val === 0) {
          this.stopPolling();
          this.showToast('Live auto-refresh paused', 'warning');
        } else {
          this.pollFrequencyMs = val;
          this.startPolling();
          this.showToast(`Auto-refresh set to ${val / 1000}s`, 'healthy');
        }
      });
    }

    // Chart deep-dive service selector
    const chartServiceSelect = document.getElementById('chartServiceSelect');
    if (chartServiceSelect) {
      chartServiceSelect.addEventListener('change', (e) => {
        this.selectedServiceId = e.target.value;
        this.loadChartData();
      });
    }

    // Alert filter pills
    document.querySelectorAll('.filter-pill').forEach(pill => {
      pill.addEventListener('click', (e) => {
        document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        this.alertFilter = pill.getAttribute('data-status');
        this.loadAlerts();
      });
    });

    // Audio alerts checkbox
    const audioToggle = document.getElementById('checkAudioAlerts');
    if (audioToggle) {
      audioToggle.addEventListener('change', (e) => {
        this.audioAlertsEnabled = e.target.checked;
        if (this.audioAlertsEnabled) {
          this.playAlertSound(600, 0.1); // Test sound
          this.showToast('Audio alert notifications enabled', 'healthy');
        }
      });
    }

    // Clear resolved alerts
    const clearAlertsBtn = document.getElementById('btnClearResolvedAlerts');
    if (clearAlertsBtn) {
      clearAlertsBtn.addEventListener('click', async () => {
        try {
          const res = await API.clearResolvedAlerts();
          this.showToast(res.message, 'healthy');
          this.loadAlerts();
        } catch (err) {
          this.showToast(err.message, 'critical');
        }
      });
    }

    // New Service button and form
    const btnNewService = document.getElementById('btnOpenAddServiceModal');
    if (btnNewService) {
      btnNewService.addEventListener('click', () => this.openAddServiceModal());
    }

    const formAddService = document.getElementById('formAddService');
    if (formAddService) {
      formAddService.addEventListener('submit', (e) => this.handleCreateService(e));
    }

    // SLO Edit Form
    const formEditSlo = document.getElementById('formEditSlo');
    if (formEditSlo) {
      formEditSlo.addEventListener('submit', (e) => this.handleUpdateSlo(e));
    }

    // Modal close buttons
    document.querySelectorAll('.modal-close-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
      });
    });
  },

  startPolling() {
    this.stopPolling();
    this.pollIntervalId = setInterval(() => this.refresh(), this.pollFrequencyMs);
  },

  stopPolling() {
    if (this.pollIntervalId) {
      clearInterval(this.pollIntervalId);
      this.pollIntervalId = null;
    }
  },

  async refresh() {
    try {
      await Promise.all([
        this.loadOverview(),
        this.loadServices(),
        this.loadAlerts()
      ]);

      if (this.selectedServiceId) {
        await this.loadChartData();
      }
    } catch (err) {
      console.error('Error during refresh:', err);
    }
  },

  async loadOverview() {
    const data = await API.getOverview();
    
    // Update Fleet Availability
    const elFleetAvail = document.getElementById('kpiFleetAvailability');
    if (elFleetAvail) {
      elFleetAvail.textContent = `${data.fleet_availability_pct.toFixed(2)}%`;
      elFleetAvail.style.color = data.fleet_availability_pct >= 99.5 ? 'var(--accent-healthy)' :
                                (data.fleet_availability_pct >= 99.0 ? 'var(--accent-warning)' : 'var(--accent-critical)');
    }

    // Update Fleet Error Budget
    const elFleetBudget = document.getElementById('kpiFleetErrorBudget');
    const elBudgetBar = document.getElementById('kpiFleetBudgetBar');
    if (elFleetBudget) {
      elFleetBudget.textContent = `${data.fleet_error_budget_pct.toFixed(1)}%`;
      if (elBudgetBar) {
        elBudgetBar.style.width = `${Math.min(100, Math.max(0, data.fleet_error_budget_pct))}%`;
        elBudgetBar.className = `progress-bar-fill ${data.fleet_error_budget_pct > 50 ? 'progress-healthy' : (data.fleet_error_budget_pct > 20 ? 'progress-warning' : 'progress-critical')}`;
      }
    }

    // Update Active Incidents
    const elAlerts = document.getElementById('kpiActiveIncidents');
    const elAlertsBadge = document.getElementById('kpiActiveIncidentsBadge');
    if (elAlerts) {
      elAlerts.textContent = data.active_alerts_count;
      elAlerts.style.color = data.critical_alerts_count > 0 ? 'var(--accent-critical)' :
                            (data.warning_alerts_count > 0 ? 'var(--accent-warning)' : 'var(--accent-healthy)');
    }
    if (elAlertsBadge) {
      elAlertsBadge.textContent = `${data.critical_alerts_count} Critical / ${data.warning_alerts_count} Warning`;
      elAlertsBadge.className = `kpi-badge ${data.critical_alerts_count > 0 ? 'badge-status critical' : 'badge-status healthy'}`;
    }

    // Update Fleet QPS
    const elQps = document.getElementById('kpiFleetQps');
    if (elQps) {
      elQps.textContent = `${data.fleet_qps} req/s`;
    }

    // System Status Dot & Text
    const statusDot = document.getElementById('navStatusDot');
    const statusText = document.getElementById('navStatusText');
    if (statusDot && statusText) {
      if (data.critical_alerts_count > 0) {
        statusDot.className = 'pulse-dot critical';
        statusText.textContent = 'FLEET CRITICAL (SLA BREACH)';
        statusText.style.color = 'var(--accent-critical)';
      } else if (data.warning_alerts_count > 0) {
        statusDot.className = 'pulse-dot warning';
        statusText.textContent = 'WARNING (SLO AT RISK)';
        statusText.style.color = 'var(--accent-warning)';
      } else {
        statusDot.className = 'pulse-dot';
        statusText.textContent = 'ALL SYSTEMS HEALTHY';
        statusText.style.color = 'var(--accent-healthy)';
      }
    }
  },

  async loadServices() {
    const data = await API.getServices();
    const services = data.services || [];

    // Populate service dropdowns if needed
    this.updateServiceSelects(services);

    // If no service is selected for charts, select first one
    if (!this.selectedServiceId && services.length > 0) {
      this.selectedServiceId = services[0].service.id;
      const chartSelect = document.getElementById('chartServiceSelect');
      if (chartSelect) chartSelect.value = this.selectedServiceId;
    }

    // Render Fleet Grid
    const gridContainer = document.getElementById('servicesGrid');
    if (gridContainer) {
      gridContainer.innerHTML = services.map(item => this.renderServiceCard(item)).join('');
      this.bindServiceCardActions();
    }

    // Render Compliance Matrix Table
    const tableBody = document.getElementById('sloMatrixTableBody');
    if (tableBody) {
      tableBody.innerHTML = this.renderComplianceTableRows(services);
      this.bindSloTableActions();
    }
  },

  updateServiceSelects(services) {
    const selects = [
      document.getElementById('simTargetService'),
      document.getElementById('chartServiceSelect')
    ];

    selects.forEach(select => {
      if (!select) return;
      const currentVal = select.value;
      const isSimSelect = select.id === 'simTargetService';
      
      let html = isSimSelect ? '<option value="all">⚡ All Fleet Services</option>' : '';
      services.forEach(item => {
        const s = item.service;
        html += `<option value="${s.id}">${s.name} (${s.tier})</option>`;
      });

      if (select.children.length !== (services.length + (isSimSelect ? 1 : 0))) {
        select.innerHTML = html;
        if (currentVal) select.value = currentVal;
      }
    });
  },

  renderServiceCard(item) {
    const s = item.service;
    const m = item.latest_metric || {};
    const status = item.overall_status;
    const budget = item.average_error_budget_pct;
    const simCfg = item.simulation_config || {};

    const statusClass = status.toLowerCase();
    const budgetClass = budget > 50 ? 'progress-healthy' : (budget > 20 ? 'progress-warning' : 'progress-critical');

    return `
      <div class="service-card status-${statusClass}" data-service-id="${s.id}">
        <div class="service-top">
          <div class="service-info">
            <h3>${s.name}</h3>
            <div class="service-tier-badge">${s.tier} • <code>${s.endpoint}</code></div>
          </div>
          <span class="badge-status ${statusClass}">${status}</span>
        </div>

        <div class="service-metrics-grid">
          <div class="metric-item">
            <span class="metric-label">Availability</span>
            <span class="metric-val" style="color: ${m.availability_pct >= 99.5 ? 'var(--accent-healthy)' : 'var(--accent-critical)'}">
              ${m.availability_pct ? m.availability_pct.toFixed(2) : '100.00'}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">P95 Latency</span>
            <span class="metric-val">${m.p95_latency_ms ? m.p95_latency_ms.toFixed(0) : '0'}ms</span>
          </div>
          <div class="metric-item">
            <span class="metric-label">Error Rate</span>
            <span class="metric-val" style="color: ${m.error_rate_pct > 1 ? 'var(--accent-critical)' : 'inherit'}">
              ${m.error_rate_pct ? m.error_rate_pct.toFixed(2) : '0.00'}%
            </span>
          </div>
          <div class="metric-item">
            <span class="metric-label">Traffic Rate</span>
            <span class="metric-val">${m.total_requests ? Math.round(m.total_requests / 2) : 0} req/s</span>
          </div>
        </div>

        <div class="budget-section">
          <div class="budget-header">
            <span>Error Budget Remaining</span>
            <strong>${budget.toFixed(1)}%</strong>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill ${budgetClass}" style="width: ${Math.max(0, Math.min(100, budget))}%"></div>
          </div>
        </div>

        <div class="service-actions">
          <div style="font-size: 0.72rem; color: var(--text-dim);">
            Mode: <strong>${simCfg.mode || 'NORMAL'}</strong>
          </div>
          <div style="display: flex; gap: 0.4rem;">
            <button class="btn btn-sm btn-quick-fault" data-id="${s.id}" title="Inject Chaos Fault into this service">
              💥 Chaos
            </button>
            <button class="btn btn-sm btn-primary btn-view-analytics" data-id="${s.id}">
              📈 Charts
            </button>
          </div>
        </div>
      </div>
    `;
  },

  bindServiceCardActions() {
    // Quick Fault trigger button
    document.querySelectorAll('.btn-quick-fault').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = btn.getAttribute('data-id');
        SimulatorUI.quickInject(id, 'LATENCY_SPIKE');
      });
    });

    // View Analytics button
    document.querySelectorAll('.btn-view-analytics').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const id = btn.getAttribute('data-id');
        this.selectedServiceId = id;
        const chartSelect = document.getElementById('chartServiceSelect');
        if (chartSelect) chartSelect.value = id;
        this.loadChartData();
        // Smooth scroll to charts
        document.getElementById('chartsSection').scrollIntoView({ behavior: 'smooth' });
      });
    });
  },

  renderComplianceTableRows(services) {
    let rows = '';
    services.forEach(item => {
      const s = item.service;
      const evals = item.slo_evaluations || [];

      evals.forEach(ev => {
        const statusClass = ev.status.toLowerCase();
        const budgetRemaining = ev.error_budget.budget_remaining_pct;
        const burnRate = ev.error_budget.burn_rate;

        rows += `
          <tr>
            <td><strong>${s.name}</strong> <span style="font-size: 0.7rem; color: var(--text-dim);">(${s.tier})</span></td>
            <td><strong>${ev.sli_name}</strong></td>
            <td><code style="font-size: 0.9rem;">${ev.current_value.toFixed(2)}${ev.unit}</code></td>
            <td>${ev.comparison_op} ${ev.slo_target.toFixed(2)}${ev.unit}</td>
            <td>${ev.comparison_op} ${ev.sla_target.toFixed(2)}${ev.unit}</td>
            <td>
              <div style="display: flex; align-items: center; gap: 0.5rem;">
                <div class="progress-bar-bg" style="width: 70px; height: 5px;">
                  <div class="progress-bar-fill ${budgetRemaining > 50 ? 'progress-healthy' : (budgetRemaining > 20 ? 'progress-warning' : 'progress-critical')}" style="width: ${budgetRemaining}%"></div>
                </div>
                <span>${budgetRemaining.toFixed(1)}%</span>
              </div>
            </td>
            <td>
              <span style="color: ${burnRate > 1.0 ? 'var(--accent-critical)' : 'inherit'}; font-weight: ${burnRate > 1.0 ? '700' : '400'}">
                ${burnRate.toFixed(2)}x
              </span>
            </td>
            <td><span class="badge-status ${statusClass}">${ev.status}</span></td>
            <td>
              <button class="btn btn-sm btn-edit-slo" data-service-id="${s.id}" data-sli-id="${ev.sli_id}" data-name="${s.name} - ${ev.sli_name}" data-slo="${ev.slo_target}" data-warn="${ev.warning_threshold}" data-sla="${ev.sla_target}">
                ✏️ Edit
              </button>
            </td>
          </tr>
        `;
      });
    });
    return rows;
  },

  bindSloTableActions() {
    document.querySelectorAll('.btn-edit-slo').forEach(btn => {
      btn.addEventListener('click', () => {
        const svcId = btn.getAttribute('data-service-id');
        const sliId = btn.getAttribute('data-sli-id');
        const name = btn.getAttribute('data-name');
        const slo = btn.getAttribute('data-slo');
        const warn = btn.getAttribute('data-warn');
        const sla = btn.getAttribute('data-sla');

        this.openEditSloModal(svcId, sliId, name, slo, warn, sla);
      });
    });
  },

  async loadChartData() {
    if (!this.selectedServiceId) return;

    try {
      const [metricsRes, slosRes] = await Promise.all([
        API.getServiceMetrics(this.selectedServiceId, 60),
        API.getServiceSlos(this.selectedServiceId)
      ]);

      MonitoringCharts.updateCharts(metricsRes.metrics || [], slosRes.slos || []);

      // Update badge in chart header
      const targetBadge = document.getElementById('chartHeaderTargetBadge');
      if (targetBadge && slosRes.slos) {
        const availSlo = slosRes.slos.find(s => s.sli_id === 'sli-availability');
        if (availSlo) {
          targetBadge.textContent = `SLO Target: ${availSlo.slo_target}% | SLA: ${availSlo.sla_target}%`;
        }
      }
    } catch (err) {
      console.error('Failed to load chart data:', err);
    }
  },

  async loadAlerts() {
    try {
      const data = await API.getAlerts(this.alertFilter === 'ALL' ? '' : this.alertFilter, 50);
      const alerts = data.alerts || [];

      // Check if there are newly generated critical alerts to play audio
      alerts.forEach(a => {
        if (!this.knownAlertIds.has(a.id)) {
          this.knownAlertIds.add(a.id);
          if (a.status === 'ACTIVE' && a.severity === 'CRITICAL' && this.audioAlertsEnabled) {
            this.playAlertSound(880, 0.25);
          }
        }
      });

      const listContainer = document.getElementById('alertsList');
      if (listContainer) {
        if (alerts.length === 0) {
          listContainer.innerHTML = `
            <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
              ✅ No ${this.alertFilter.toLowerCase()} alerts found. All monitored metrics within threshold.
            </div>
          `;
        } else {
          listContainer.innerHTML = alerts.map(a => this.renderAlertItem(a)).join('');
          this.bindAlertActions();
        }
      }
    } catch (err) {
      console.error('Failed to load alerts:', err);
    }
  },

  renderAlertItem(alert) {
    const sevClass = alert.severity.toLowerCase();
    const isResolved = alert.status === 'RESOLVED';
    const isAck = alert.status === 'ACKNOWLEDGED';
    const timeAgo = this.formatTimeAgo(alert.created_at);

    return `
      <div class="alert-item severity-${isResolved ? 'resolved' : sevClass}">
        <div class="alert-content">
          <div class="alert-title-row">
            <span class="badge-status ${isResolved ? 'healthy' : sevClass}">${alert.severity}</span>
            <span class="alert-title">${alert.title}</span>
            <span class="alert-meta">• ${timeAgo}</span>
          </div>
          <div class="alert-msg">${alert.message}</div>
        </div>

        <div class="alert-actions">
          ${alert.status === 'ACTIVE' ? `
            <button class="btn btn-sm btn-ack-alert" data-id="${alert.id}">
              👁️ Ack
            </button>
          ` : ''}
          ${!isResolved ? `
            <button class="btn btn-sm btn-primary btn-resolve-alert" data-id="${alert.id}">
              ✅ Resolve
            </button>
          ` : `
            <span style="font-size: 0.72rem; color: var(--accent-healthy);">Resolved</span>
          `}
        </div>
      </div>
    `;
  },

  bindAlertActions() {
    document.querySelectorAll('.btn-ack-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        try {
          const res = await API.ackAlert(id);
          this.showToast(res.message, 'healthy');
          this.loadAlerts();
        } catch (err) {
          this.showToast(err.message, 'critical');
        }
      });
    });

    document.querySelectorAll('.btn-resolve-alert').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.getAttribute('data-id');
        try {
          const res = await API.resolveAlert(id);
          this.showToast(res.message, 'healthy');
          this.loadAlerts();
        } catch (err) {
          this.showToast(err.message, 'critical');
        }
      });
    });
  },

  openEditSloModal(serviceId, sliId, name, slo, warn, sla) {
    document.getElementById('editSloModalTitle').textContent = `Edit Target: ${name}`;
    document.getElementById('editSloServiceId').value = serviceId;
    document.getElementById('editSloSliId').value = sliId;
    document.getElementById('inputSloTarget').value = slo;
    document.getElementById('inputWarningTarget').value = warn;
    document.getElementById('inputSlaTarget').value = sla;

    document.getElementById('modalEditSlo').classList.add('active');
  },

  async handleUpdateSlo(e) {
    e.preventDefault();
    const serviceId = document.getElementById('editSloServiceId').value;
    const sliId = document.getElementById('editSloSliId').value;

    const data = {
      slo_target: parseFloat(document.getElementById('inputSloTarget').value),
      warning_threshold: parseFloat(document.getElementById('inputWarningTarget').value),
      sla_target: parseFloat(document.getElementById('inputSlaTarget').value)
    };

    try {
      // Find the slo_id by querying service slos
      const slosRes = await API.getServiceSlos(serviceId);
      const targetSlo = slosRes.slos.find(s => s.sli_id === sliId);
      if (!targetSlo) throw new Error('Target SLO not found');

      await API.updateServiceSlo(serviceId, targetSlo.id, data);
      document.getElementById('modalEditSlo').classList.remove('active');
      this.showToast('SLO thresholds updated successfully', 'healthy');
      this.refresh();
    } catch (err) {
      this.showToast(err.message, 'critical');
    }
  },

  openAddServiceModal() {
    document.getElementById('modalAddService').classList.add('active');
  },

  async handleCreateService(e) {
    e.preventDefault();
    const data = {
      id: document.getElementById('newServiceId').value.trim(),
      name: document.getElementById('newServiceName').value.trim(),
      tier: document.getElementById('newServiceTier').value,
      description: document.getElementById('newServiceDesc').value.trim(),
      base_qps: parseInt(document.getElementById('newServiceQps').value) || 100
    };

    try {
      const res = await API.createService(data);
      document.getElementById('modalAddService').classList.remove('active');
      document.getElementById('formAddService').reset();
      this.showToast(`Service "${data.name}" added to monitoring`, 'healthy');
      this.refresh();
    } catch (err) {
      this.showToast(err.message, 'critical');
    }
  },

  playAlertSound(frequency = 750, duration = 0.2) {
    try {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (!AudioContext) return;
      const ctx = new AudioContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(frequency, ctx.currentTime);
      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + duration);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + duration);
    } catch (e) {
      // Audio play blocked or unsupported
    }
  },

  formatTimeAgo(epochSec) {
    const diff = Math.floor(Date.now() / 1000 - epochSec);
    if (diff < 10) return 'just now';
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    return `${Math.floor(diff / 3600)}h ago`;
  },

  showToast(message, type = 'healthy') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background-color: var(--bg-card);
      color: var(--text-main);
      padding: 0.75rem 1.25rem;
      border-radius: var(--radius-sm);
      border: 1px solid ${type === 'critical' ? 'var(--accent-critical)' : (type === 'warning' ? 'var(--accent-warning)' : 'var(--accent-healthy)')};
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
      font-size: 0.82rem;
      font-weight: 600;
      z-index: 9999;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      animation: fadeIn 0.3s ease;
    `;
    toast.innerHTML = `
      <span>${type === 'critical' ? '🚨' : (type === 'warning' ? '⚠️' : '✅')}</span>
      <span>${message}</span>
    `;

    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.4s ease';
      setTimeout(() => toast.remove(), 400);
    }, 3500);
  }
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  Dashboard.init();
});
