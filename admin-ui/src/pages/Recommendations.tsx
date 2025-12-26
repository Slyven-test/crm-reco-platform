/**
 * Recommendations Page - View and Filter Recommendations
 */

import React, { useEffect, useState } from 'react'
import { Search, Filter } from 'lucide-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

interface RecoItem {
  rank: number
  product_key: string
  product_name: string
  scenario: string
  score: { final_score: number }
  explanation: { reason: string }
}

const Recommendations: React.FC = () => {
  const { setIsLoading, setError, isLoading } = useAppStore()
  const [recos, setRecos] = useState<RecoItem[]>([])
  const [customerCode, setCustomerCode] = useState('')
  const [scenario, setScenario] = useState('default')
  const [minScore, setMinScore] = useState(0.5)

  const handleSearch = async () => {
    if (!customerCode) {
      setError('Please enter a customer code')
      return
    }
    setIsLoading(true)
    try {
      const res = await api.getRecommendationsFiltered(customerCode, scenario, minScore)
      setRecos(res.data.recommendations || [])
    } catch (error: any) {
      setError(error.message || 'Failed to load recommendations')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Search & Filter */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <input
            type="text"
            placeholder="Customer Code"
            value={customerCode}
            onChange={(e) => setCustomerCode(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
          />
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
          >
            <option value="default">Default</option>
            <option value="new_customer">New Customer</option>
            <option value="high_value">High Value</option>
            <option value="retention">Retention</option>
          </select>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={minScore}
            onChange={(e) => setMinScore(parseFloat(e.target.value))}
            className="px-4 py-2"
          />
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors flex items-center gap-2"
          >
            <Search size={18} />
            Search
          </button>
        </div>
      </div>

      {/* Results */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Loading...</div>
        ) : recos.length === 0 ? (
          <div className="p-6 text-center text-gray-500">No recommendations found</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Rank</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Product</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Scenario</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Score</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {recos.map((reco, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-semibold text-gray-900">{reco.rank}</td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      <div>
                        <p className="font-semibold">{reco.product_key}</p>
                        <p className="text-gray-600">{reco.product_name}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{reco.scenario}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-full bg-gray-200 rounded-full h-2 max-w-xs">
                          <div
                            className="bg-teal-600 h-2 rounded-full"
                            style={{ width: `${reco.score.final_score * 100}%` }}
                          ></div>
                        </div>
                        <span className="ml-2 text-sm font-semibold text-gray-900">
                          {(reco.score.final_score * 100).toFixed(1)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{reco.explanation.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Recommendations
