/**
 * Chaos and Traffic Simulator controller
 */
const SimulatorUI = {
  currentScenario: 'NORMAL',

  init() {
    this.bindEvents();
  },

  bindEvents() {
    // Preset scenario buttons
    document.querySelectorAll('.scenario-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const scenario = btn.getAttribute('data-scenario');
        this.selectScenario(scenario);
      });
    });

    // Apply button
    const applyBtn = document.getElementById('btnApplyChaos');
    if (applyBtn) {
      applyBtn.addEventListener('click', () => this.applyChaos());
    }

    // Reset button
    const resetBtn = document.getElementById('btnResetChaos');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => this.resetChaos());
    }

    // Force tick button
    const tickBtn = document.getElementById('btnForceTick');
    if (tickBtn) {
      tickBtn.addEventListener('click', () => this.forceTick());
    }

    // Toggle simulator button
    const toggleBtn = document.getElementById('btnToggleSimulator');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => this.toggleSimulator());
    }
  },

  selectScenario(scenario) {
    this.currentScenario = scenario;
    document.querySelectorAll('.scenario-btn').forEach(btn => {
      if (btn.getAttribute('data-scenario') === scenario) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });

    // Auto update sliders depending on scenario
    const latencyInput = document.getElementById('inputAddedLatency');
    const errorInput = document.getElementById('inputInjectedErrors');

    if (scenario === 'NORMAL') {
      if (latencyInput) latencyInput.value = 0;
      if (errorInput) errorInput.value = 0;
    } else if (scenario === 'LATENCY_SPIKE') {
      if (latencyInput) latencyInput.value = 750;
      if (errorInput) errorInput.value = 0;
    } else if (scenario === 'ERROR_FLOOD') {
      if (latencyInput) latencyInput.value = 150;
      if (errorInput) errorInput.value = 25;
    } else if (scenario === 'PARTIAL_OUTAGE') {
      if (latencyInput) latencyInput.value = 400;
      if (errorInput) errorInput.value = 50;
    } else if (scenario === 'TOTAL_OUTAGE') {
      if (latencyInput) latencyInput.value = 2000;
      if (errorInput) errorInput.value = 100;
    } else if (scenario === 'TRAFFIC_SPIKE') {
      if (latencyInput) latencyInput.value = 100;
      if (errorInput) errorInput.value = 1;
    }
  },

  async applyChaos() {
    const serviceSelect = document.getElementById('simTargetService');
    const serviceId = serviceSelect ? serviceSelect.value : 'all';
    const latencyInput = document.getElementById('inputAddedLatency');
    const errorInput = document.getElementById('inputInjectedErrors');

    const payload = {
      service_id: serviceId,
      scenario: this.currentScenario,
      added_latency_ms: latencyInput ? parseFloat(latencyInput.value) : 0,
      error_injection_pct: errorInput ? parseFloat(errorInput.value) : 0
    };

    try {
      const res = await API.injectChaos(payload);
      Dashboard.showToast(res.message, 'warning');
      Dashboard.refresh();
    } catch (err) {
      Dashboard.showToast(err.message, 'critical');
    }
  },

  async quickInject(serviceId, scenario) {
    try {
      const res = await API.injectChaos({
        service_id: serviceId,
        scenario: scenario
      });
      Dashboard.showToast(`Injected ${scenario} into ${serviceId}`, 'warning');
      Dashboard.refresh();
    } catch (err) {
      Dashboard.showToast(err.message, 'critical');
    }
  },

  async resetChaos() {
    try {
      const res = await API.resetChaos();
      this.selectScenario('NORMAL');
      Dashboard.showToast(res.message, 'healthy');
      Dashboard.refresh();
    } catch (err) {
      Dashboard.showToast(err.message, 'critical');
    }
  },

  async forceTick() {
    try {
      const res = await API.forceTick();
      Dashboard.showToast(`Simulated tick generated`, 'healthy');
      Dashboard.refresh();
    } catch (err) {
      Dashboard.showToast(err.message, 'critical');
    }
  },

  async toggleSimulator() {
    try {
      const res = await API.toggleSimulator();
      Dashboard.showToast(res.message, 'healthy');
      Dashboard.refresh();
    } catch (err) {
      Dashboard.showToast(err.message, 'critical');
    }
  }
};
