/**
 * Zustand Store for Admin UI State Management
 */

import { create } from 'zustand'

interface Recommendation {
  rank: number
  product_key: string
  product_name: string
  scenario: string
  score: {
    base_score: number
    affinity_score: number
    popularity_score: number
    profit_score: number
    final_score: number
  }
  explanation: {
    title: string
    reason: string
    components: string[]
  }
}

interface QualityMetrics {
  run_id: string
  total_recommendations: number
  coverage_score: number
  diversity_score: number
  accuracy_score: number
  avg_score: number
  median_score: number
  quality_level: 'EXCELLENT' | 'GOOD' | 'ACCEPTABLE' | 'POOR'
  timestamp: string
}

interface AuditLog {
  audit_id: string
  run_id: string
  customer_code: string
  product_key: string
  scenario: string
  recommendation_score: number
  approval_status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'FLAGGED'
  created_at: string
  approved_at?: string
  approved_by?: string
}

interface AppStore {
  // UI State
  currentTab: 'dashboard' | 'recommendations' | 'approvals' | 'quality' | 'compliance' | 'settings'
  setCurrentTab: (tab: AppStore['currentTab']) => void

  // Data State
  recommendations: Recommendation[]
  setRecommendations: (recos: Recommendation[]) => void

  qualityMetrics: QualityMetrics | null
  setQualityMetrics: (metrics: QualityMetrics) => void

  auditLogs: AuditLog[]
  setAuditLogs: (logs: AuditLog[]) => void

  pendingApprovals: AuditLog[]
  setPendingApprovals: (approvals: AuditLog[]) => void

  // Loading State
  isLoading: boolean
  setIsLoading: (loading: boolean) => void

  // Error State
  error: string | null
  setError: (error: string | null) => void

  // Filters
  selectedCustomer: string | null
  setSelectedCustomer: (customer: string | null) => void

  selectedScenario: string | null
  setSelectedScenario: (scenario: string | null) => void

  dateRange: {
    from: Date | null
    to: Date | null
  }
  setDateRange: (from: Date | null, to: Date | null) => void
}

export const useAppStore = create<AppStore>((set) => ({
  // UI State
  currentTab: 'dashboard',
  setCurrentTab: (tab) => set({ currentTab: tab }),

  // Data State
  recommendations: [],
  setRecommendations: (recos) => set({ recommendations: recos }),

  qualityMetrics: null,
  setQualityMetrics: (metrics) => set({ qualityMetrics: metrics }),

  auditLogs: [],
  setAuditLogs: (logs) => set({ auditLogs: logs }),

  pendingApprovals: [],
  setPendingApprovals: (approvals) => set({ pendingApprovals: approvals }),

  // Loading State
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),

  // Error State
  error: null,
  setError: (error) => set({ error }),

  // Filters
  selectedCustomer: null,
  setSelectedCustomer: (customer) => set({ selectedCustomer: customer }),

  selectedScenario: null,
  setSelectedScenario: (scenario) => set({ selectedScenario: scenario }),

  dateRange: { from: null, to: null },
  setDateRange: (from, to) => set({ dateRange: { from, to } }),
}))
