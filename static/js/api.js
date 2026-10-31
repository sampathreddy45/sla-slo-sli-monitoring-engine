/**
 * API client module for SLA, SLO, SLI Monitoring Engine
 */
const API = {
  async getOverview() {
    const res = await fetch('/api/overview');
    if (!res.ok) throw new Error('Failed to load overview data');
    return await res.json();
  },

  async getServices() {
    const res = await fetch('/api/services');
    if (!res.ok) throw new Error('Failed to load services');
    return await res.json();
  },

  async getServiceMetrics(serviceId, limit = 50) {
    const res = await fetch(`/api/services/${serviceId}/metrics?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to load metrics for ${serviceId}`);
    return await res.json();
  },

  async getServiceSlos(serviceId) {
    const res = await fetch(`/api/services/${serviceId}/slos`);
    if (!res.ok) throw new Error(`Failed to load SLOs for ${serviceId}`);
    return await res.json();
  },

  async updateServiceSlo(serviceId, sloId, data) {
    const res = await fetch(`/api/services/${serviceId}/slos/${sloId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to update SLO target');
    return await res.json();
  },

  async createService(data) {
    const res = await fetch('/api/services', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.error || 'Failed to create service');
    }
    return await res.json();
  },

  async getAlerts(status = '', limit = 50) {
    const url = status ? `/api/alerts?status=${status}&limit=${limit}` : `/api/alerts?limit=${limit}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return await res.json();
  },

  async ackAlert(alertId) {
    const res = await fetch(`/api/alerts/${alertId}/ack`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to acknowledge alert');
    return await res.json();
  },

  async resolveAlert(alertId) {
    const res = await fetch(`/api/alerts/${alertId}/resolve`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to resolve alert');
    return await res.json();
  },

  async clearResolvedAlerts() {
    const res = await fetch('/api/alerts/clear-resolved', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to clear resolved alerts');
    return await res.json();
  },

  async injectChaos(data) {
    const res = await fetch('/api/simulator/inject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error('Failed to inject simulation condition');
    return await res.json();
  },

  async resetChaos() {
    const res = await fetch('/api/simulator/reset', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset simulation');
    return await res.json();
  },

  async toggleSimulator() {
    const res = await fetch('/api/simulator/toggle', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to toggle simulator');
    return await res.json();
  },

  async forceTick() {
    const res = await fetch('/api/simulator/tick', { method: 'POST' });
    if (!res.ok) throw new Error('Failed to trigger manual tick');
    return await res.json();
  }
};
