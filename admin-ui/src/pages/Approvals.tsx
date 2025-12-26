/**
 * Approvals Page - Manage Recommendation Approvals
 */

import React, { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

interface ApprovalItem {
  audit_id: string
  customer_code: string
  product_key: string
  scenario: string
  score: number
  created_at: string
  approval_status: string
}

const Approvals: React.FC = () => {
  const { setIsLoading, setError, isLoading } = useAppStore()
  const [pending, setPending] = useState<ApprovalItem[]>([])
  const [flagged, setFlagged] = useState<ApprovalItem[]>([])
  const [activeTab, setActiveTab] = useState<'pending' | 'flagged'>('pending')
  const [approverName, setApproverName] = useState('admin')

  useEffect(() => {
    loadApprovals()
  }, [])

  const loadApprovals = async () => {
    setIsLoading(true)
    try {
      const [pendingRes, flaggedRes] = await Promise.all([
        api.getPendingApprovals(),
        api.getFlaggedRecommendations(),
      ])
      setPending(pendingRes.data.pending || [])
      setFlagged(flaggedRes.data.flagged || [])
    } catch (error: any) {
      setError(error.message || 'Failed to load approvals')
    } finally {
      setIsLoading(false)
    }
  }

  const handleApprove = async (auditId: string) => {
    try {
      await api.approveRecommendation(auditId, approverName, 'Approved by admin')
      loadApprovals()
    } catch (error: any) {
      setError(error.message || 'Failed to approve')
    }
  }

  const handleReject = async (auditId: string, reason = 'Does not meet quality standards') => {
    try {
      await api.rejectRecommendation(auditId, approverName, reason)
      loadApprovals()
    } catch (error: any) {
      setError(error.message || 'Failed to reject')
    }
  }

  const handleFlag = async (auditId: string) => {
    try {
      await api.flagRecommendation(auditId, 'Flagged for manual review')
      loadApprovals()
    } catch (error: any) {
      setError(error.message || 'Failed to flag')
    }
  }

  const items = activeTab === 'pending' ? pending : flagged

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Approval Workflows</h2>
          <p className="text-gray-600 mt-1">Review and manage recommendations</p>
        </div>
        <div>
          <input
            type="text"
            value={approverName}
            onChange={(e) => setApproverName(e.target.value)}
            placeholder="Approver name"
            className="px-4 py-2 border border-gray-300 rounded-lg"
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 flex">
          <button
            onClick={() => setActiveTab('pending')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'pending'
                ? 'text-teal-600 border-b-2 border-teal-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Pending ({pending.length})
          </button>
          <button
            onClick={() => setActiveTab('flagged')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'flagged'
                ? 'text-orange-600 border-b-2 border-orange-600'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            Flagged ({flagged.length})
          </button>
        </div>

        {/* Items List */}
        <div className="divide-y">
          {isLoading ? (
            <div className="p-6 text-center text-gray-500">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-6 text-center text-gray-500">
              No {activeTab} items
            </div>
          ) : (
            items.map((item) => (
              <div key={item.audit_id} className="p-6 hover:bg-gray-50">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-gray-600">Customer</p>
                    <p className="text-lg font-semibold">{item.customer_code}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Product</p>
                    <p className="text-lg font-semibold">{item.product_key}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Score</p>
                    <p className="text-lg font-semibold text-teal-600">
                      {item.score.toFixed(1)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Scenario</p>
                    <p className="text-lg font-semibold">{item.scenario}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Created</p>
                    <p className="text-lg font-semibold">
                      {new Date(item.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Status</p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-sm font-medium">
                        {item.approval_status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3 mt-4">
                  <button
                    onClick={() => handleApprove(item.audit_id)}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <CheckCircle size={18} />
                    Approve
                  </button>
                  <button
                    onClick={() => handleReject(item.audit_id)}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                  >
                    <XCircle size={18} />
                    Reject
                  </button>
                  {activeTab === 'pending' && (
                    <button
                      onClick={() => handleFlag(item.audit_id)}
                      className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
                    >
                      <AlertCircle size={18} />
                      Flag
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

export default Approvals
