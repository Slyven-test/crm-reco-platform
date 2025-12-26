/**
 * API Client for Admin UI
 */

import axios from 'axios'

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for auth token (if needed)
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Add response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client

// API methods
export const api = {
  // Recommendations
  getRecommendations: (customerCode: string, maxRecommendations = 5) =>
    client.get(`/recommendations/${customerCode}`, {
      params: { max_recommendations: maxRecommendations },
    }),

  getRecommendationsFiltered: (
    customerCode: string,
    scenario?: string,
    minScore?: number
  ) =>
    client.get(`/recommendations/${customerCode}/filtered`, {
      params: { scenario, min_score: minScore },
    }),

  getRecommendationHistory: (customerCode: string, limit = 50) =>
    client.get(`/recommendations/${customerCode}/history`, {
      params: { limit },
    }),

  getStatistics: (fromDate?: string, toDate?: string) =>
    client.get('/recommendations/stats/overview', {
      params: { from_date: fromDate, to_date: toDate },
    }),

  batchGenerateRecommendations: (customerCodes?: string[], limit = 100) =>
    client.post('/recommendations/batch', {
      customer_codes: customerCodes,
      limit,
      save_results: true,
    }),

  // Audit
  getAuditLogs: (customerCode?: string, limit = 100) =>
    client.get('/audit/logs', {
      params: { customer_code: customerCode, limit },
    }),

  getPendingApprovals: (limit = 100) =>
    client.get('/audit/pending', { params: { limit } }),

  getFlaggedRecommendations: (limit = 100) =>
    client.get('/audit/flagged', { params: { limit } }),

  approveRecommendation: (auditId: string, approvedBy: string, reason?: string) =>
    client.post(`/audit/approve/${auditId}`, null, {
      params: { approved_by: approvedBy, reason },
    }),

  rejectRecommendation: (auditId: string, approvedBy: string, reason: string) =>
    client.post(`/audit/reject/${auditId}`, null, {
      params: { approved_by: approvedBy, reason },
    }),

  flagRecommendation: (auditId: string, reason: string) =>
    client.post(`/audit/flag/${auditId}`, null, {
      params: { reason },
    }),

  // Quality
  getQualityMetrics: (runId: string, totalCustomers = 1000) =>
    client.get(`/audit/quality/metrics/${runId}`, {
      params: { total_customers: totalCustomers },
    }),

  getQualityReport: (days = 7) =>
    client.get('/audit/quality/report', { params: { days } }),

  // Gating
  checkRecommendationGating: (recommendationId: string, policy = 'standard') =>
    client.post(`/audit/gating/check/${recommendationId}`, null, {
      params: { policy },
    }),

  checkBatchGating: (runId: string, policy = 'standard') =>
    client.post('/audit/gating/check-batch', null, {
      params: { run_id: runId, policy },
    }),

  // Compliance
  getComplianceSummary: () => client.get('/audit/compliance/summary'),
}
