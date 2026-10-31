/**
 * Chart rendering module using Chart.js for SLA/SLO observability
 */
const MonitoringCharts = {
  availabilityChart: null,
  latencyChart: null,
  errorRateChart: null,
  errorBudgetChart: null,

  init() {
    if (typeof Chart === 'undefined') {
      console.warn('Chart.js not loaded yet');
      return;
    }

    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.08)';
    Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';

    this.initAvailabilityChart();
    this.initLatencyChart();
    this.initErrorRateChart();
    this.initErrorBudgetChart();
  },

  formatTime(epochSec) {
    const d = new Date(epochSec * 1000);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  },

  initAvailabilityChart() {
    const ctx = document.getElementById('availabilityChartCanvas');
    if (!ctx) return;

    this.availabilityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Availability (%)',
            data: [],
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 2
          },
          {
            label: 'Success Rate (%)',
            data: [],
            borderColor: '#3b82f6',
            backgroundColor: 'transparent',
            borderDash: [4, 4],
            tension: 0.3,
            borderWidth: 1.5,
            pointRadius: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } },
          tooltip: { padding: 8 }
        },
        scales: {
          y: {
            min: 80,
            max: 100.5,
            ticks: {
              callback: (val) => `${val}%`,
              font: { size: 10 }
            }
          },
          x: {
            ticks: { maxTicksLimit: 8, font: { size: 10 } }
          }
        }
      }
    });
  },

  initLatencyChart() {
    const ctx = document.getElementById('latencyChartCanvas');
    if (!ctx) return;

    this.latencyChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'P95 Latency (ms)',
            data: [],
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.1)',
            fill: true,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 2
          },
          {
            label: 'Avg Latency (ms)',
            data: [],
            borderColor: '#06b6d4',
            backgroundColor: 'transparent',
            tension: 0.3,
            borderWidth: 1.5,
            pointRadius: 1
          },
          {
            label: 'P99 Latency (ms)',
            data: [],
            borderColor: '#ec4899',
            backgroundColor: 'transparent',
            borderDash: [3, 3],
            tension: 0.3,
            borderWidth: 1.5,
            pointRadius: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => `${val}ms`,
              font: { size: 10 }
            }
          },
          x: {
            ticks: { maxTicksLimit: 8, font: { size: 10 } }
          }
        }
      }
    });
  },

  initErrorRateChart() {
    const ctx = document.getElementById('errorRateChartCanvas');
    if (!ctx) return;

    this.errorRateChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Error Rate (%)',
            data: [],
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            fill: true,
            tension: 0.2,
            borderWidth: 2,
            pointRadius: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (val) => `${val}%`,
              font: { size: 10 }
            }
          },
          x: {
            ticks: { maxTicksLimit: 8, font: { size: 10 } }
          }
        }
      }
    });
  },

  initErrorBudgetChart() {
    const ctx = document.getElementById('errorBudgetChartCanvas');
    if (!ctx) return;

    this.errorBudgetChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Remaining Error Budget (%)',
            data: [],
            borderColor: '#8b5cf6',
            backgroundColor: 'rgba(139, 92, 246, 0.15)',
            fill: true,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
        },
        scales: {
          y: {
            min: 0,
            max: 100,
            ticks: {
              callback: (val) => `${val}%`,
              font: { size: 10 }
            }
          },
          x: {
            ticks: { maxTicksLimit: 8, font: { size: 10 } }
          }
        }
      }
    });
  },

  updateCharts(metricsList, sloList = []) {
    if (!metricsList || metricsList.length === 0) return;

    const labels = metricsList.map(m => this.formatTime(m.timestamp));
    const availData = metricsList.map(m => m.availability_pct);
    const successData = metricsList.map(m => m.success_rate_pct);
    const p95Data = metricsList.map(m => m.p95_latency_ms);
    const avgData = metricsList.map(m => m.avg_latency_ms);
    const p99Data = metricsList.map(m => m.p99_latency_ms);
    const errorData = metricsList.map(m => m.error_rate_pct);

    // Calculate approximate historical error budget remaining based on availability SLO
    const availSlo = sloList.find(s => s.sli_id === 'sli-availability');
    const sloTarget = availSlo ? availSlo.slo_target : 99.5;
    const allowableFailure = Math.max(0.001, 100.0 - sloTarget);

    const budgetData = availData.map(val => {
      const actualFailure = Math.max(0, 100.0 - val);
      const remaining = Math.max(0, Math.min(100, (1 - (actualFailure / allowableFailure)) * 100));
      return Math.round(remaining * 10) / 10;
    });

    // Update Availability Chart
    if (this.availabilityChart) {
      this.availabilityChart.data.labels = labels;
      this.availabilityChart.data.datasets[0].data = availData;
      this.availabilityChart.data.datasets[1].data = successData;
      // Dynamically adjust scale minimum if availability drops low
      const minVal = Math.min(...availData);
      this.availabilityChart.options.scales.y.min = Math.max(0, Math.floor(minVal - 5));
      this.availabilityChart.update('none');
    }

    // Update Latency Chart
    if (this.latencyChart) {
      this.latencyChart.data.labels = labels;
      this.latencyChart.data.datasets[0].data = p95Data;
      this.latencyChart.data.datasets[1].data = avgData;
      this.latencyChart.data.datasets[2].data = p99Data;
      this.latencyChart.update('none');
    }

    // Update Error Rate Chart
    if (this.errorRateChart) {
      this.errorRateChart.data.labels = labels;
      this.errorRateChart.data.datasets[0].data = errorData;
      this.errorRateChart.update('none');
    }

    // Update Error Budget Chart
    if (this.errorBudgetChart) {
      this.errorBudgetChart.data.labels = labels;
      this.errorBudgetChart.data.datasets[0].data = budgetData;
      this.errorBudgetChart.update('none');
    }
  }
};
