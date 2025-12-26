/**
 * Compliance Page - Compliance & Gating Dashboard
 */

import React, { useEffect, useState } from 'react'
import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

const Compliance: React.FC = () => {
  const { setIsLoading, setError, isLoading } = useAppStore()
  const [summary, setSummary] = useState<any>(null)
  const [selectedPolicy, setSelectedPolicy] = useState('standard')
  const [auditLogs, setAuditLogs] = useState<any[]>([])

  useEffect(() => {
    loadComplianceData()
  }, [])

  const loadComplianceData = async () => {
    setIsLoading(true)
    try {
      const [summaryRes, logsRes] = await Promise.all([
        api.getComplianceSummary(),
        api.getAuditLogs(),
      ])
      setSummary(summaryRes.data)
      setAuditLogs(logsRes.data.logs || [])
    } catch (error: any) {
      setError(error.message || 'Failed to load compliance data')
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'APPROVED':
        return <CheckCircle className="text-green-600" />
      case 'REJECTED':
        return <XCircle className="text-red-600" />
      case 'FLAGGED':
        return <AlertTriangle className="text-orange-600" />
      default:
        return <AlertTriangle className="text-yellow-600" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {summary?.approval_summary && Object.entries(summary.approval_summary).map(([status, count]) => (
          <div key={status} className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-600 text-sm">{status}</p>
            <p className="text-3xl font-bold mt-2">{count as number}</p>
          </div>
        ))}
      </div>

      {/* Gating Policies */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Gating Policies</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {['strict', 'standard', 'permissive'].map((policy) => (
            <button
              key={policy}
              onClick={() => setSelectedPolicy(policy)}
              className={`p-4 rounded-lg border-2 transition-colors text-left ${
                selectedPolicy === policy
                  ? 'border-teal-600 bg-teal-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <p className="font-semibold capitalize">{policy}</p>
              <p className="text-sm text-gray-600 mt-1">
                {policy === 'strict'
                  ? 'Highest quality standards'
                  : policy === 'standard'
                  ? 'Balanced approach'
                  : 'More flexible rules'}
              </p>
              <p className="text-xs text-gray-500 mt-2">{getPassRate(policy)}% pass rate</p>
            </button>
          ))}
        </div>
      </div>

      {/* Audit Logs */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Audit Logs</h3>
        {isLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : (
          <div className="space-y-4">
            {auditLogs.slice(0, 10).map((log) => (
              <div key={log.audit_id} className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    {getStatusIcon(log.approval_status)}
                    <div>
                      <p className="font-semibold">{log.customer_code}</p>
                      <p className="text-sm text-gray-600">{log.product_key}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        Score: {log.recommendation_score.toFixed(1)}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${
                      log.approval_status === 'APPROVED'
                        ? 'bg-green-100 text-green-800'
                        : log.approval_status === 'REJECTED'
                        ? 'bg-red-100 text-red-800'
                        : log.approval_status === 'FLAGGED'
                        ? 'bg-orange-100 text-orange-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {log.approval_status}
                    </span>
                    <p className="text-xs text-gray-500 mt-2">
                      {new Date(log.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Compliance Summary */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Approval Rate</h3>
            <div className="text-center">
              <p className="text-5xl font-bold text-teal-600">{summary.approval_rate}%</p>
              <p className="text-gray-600 mt-2">of recommendations approved</p>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-semibold mb-4">Compliance Score</h3>
            <div className="text-center">
              <p className="text-5xl font-bold text-blue-600">{summary.compliance_score || 'N/A'}</p>
              <p className="text-gray-600 mt-2">overall compliance</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function getPassRate(policy: string): number {
  switch (policy) {
    case 'strict':
      return 65
    case 'standard':
      return 82
    case 'permissive':
      return 95
    default:
      return 0
  }
}

export default Compliance
