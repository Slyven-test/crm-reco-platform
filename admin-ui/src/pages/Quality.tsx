/**
 * Quality Metrics Page
 */

import React, { useEffect, useState } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, AlertCircle, CheckCircle } from 'lucide-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

const Quality: React.FC = () => {
  const { setIsLoading, setError, isLoading } = useAppStore()
  const [report, setReport] = useState<any>(null)
  const [selectedRun, setSelectedRun] = useState<string>('')
  const [metrics, setMetrics] = useState<any>(null)

  useEffect(() => {
    loadQualityData()
  }, [])

  const loadQualityData = async () => {
    setIsLoading(true)
    try {
      const res = await api.getQualityReport(7)
      setReport(res.data)
      if (res.data.recent_runs?.[0]) {
        setSelectedRun(res.data.recent_runs[0].run_id)
      }
    } catch (error: any) {
      setError(error.message || 'Failed to load quality data')
    } finally {
      setIsLoading(false)
    }
  }

  const loadMetrics = async (runId: string) => {
    try {
      const res = await api.getQualityMetrics(runId)
      setMetrics(res.data)
    } catch (error: any) {
      setError(error.message || 'Failed to load metrics')
    }
  }

  const handleRunSelect = (runId: string) => {
    setSelectedRun(runId)
    loadMetrics(runId)
  }

  const getQualityColor = (level: string) => {
    switch (level) {
      case 'EXCELLENT':
        return 'bg-green-100 text-green-800'
      case 'GOOD':
        return 'bg-blue-100 text-blue-800'
      case 'ACCEPTABLE':
        return 'bg-yellow-100 text-yellow-800'
      case 'POOR':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Avg Coverage</p>
          <p className="text-3xl font-bold mt-2">{(report?.average_coverage || 0).toFixed(1)}%</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Avg Diversity</p>
          <p className="text-3xl font-bold mt-2">{(report?.average_diversity || 0).toFixed(1)}%</p>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600 text-sm">Avg Accuracy</p>
          <p className="text-3xl font-bold mt-2">{(report?.average_accuracy || 0).toFixed(1)}%</p>
        </div>
      </div>

      {/* Quality Metrics Detail */}
      {metrics && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Run Details: {selectedRun}</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Total" value={metrics.total_recommendations} />
            <MetricCard label="Coverage" value={`${(metrics.coverage_score * 100).toFixed(1)}%`} />
            <MetricCard label="Diversity" value={`${(metrics.diversity_score * 100).toFixed(1)}%`} />
            <MetricCard label="Accuracy" value={`${(metrics.accuracy_score * 100).toFixed(1)}%`} />
            <MetricCard label="Avg Score" value={metrics.avg_score.toFixed(1)} />
            <MetricCard label="Median Score" value={metrics.median_score.toFixed(1)} />
            <div className="col-span-2">
              <p className="text-sm text-gray-600">Quality Level</p>
              <div className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mt-1 ${getQualityColor(metrics.quality_level)}`}>
                {metrics.quality_level}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recent Runs */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Runs</h3>
        {isLoading ? (
          <p className="text-gray-500">Loading...</p>
        ) : (
          <div className="space-y-2">
            {report?.recent_runs?.map((run: any) => (
              <button
                key={run.run_id}
                onClick={() => handleRunSelect(run.run_id)}
                className={`w-full text-left p-4 rounded-lg border transition-colors ${
                  selectedRun === run.run_id
                    ? 'border-teal-600 bg-teal-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <p className="font-semibold">{run.run_id}</p>
                    <p className="text-sm text-gray-600">{run.total_recommendations} recommendations</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-semibold px-2 py-1 rounded ${getQualityColor(run.quality_level)}`}>
                      {run.quality_level}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">{new Date(run.timestamp).toLocaleDateString()}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Quality Distribution */}
      {report?.quality_distribution && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Quality Distribution (7 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={Object.entries(report.quality_distribution).map(([level, count]) => ({ level, count }))}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="level" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="count" fill="#14b8a6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

interface MetricCardProps {
  label: string
  value: string | number
}

const MetricCard: React.FC<MetricCardProps> = ({ label, value }) => (
  <div className="p-4 bg-gray-50 rounded-lg">
    <p className="text-sm text-gray-600">{label}</p>
    <p className="text-xl font-bold mt-1">{value}</p>
  </div>
)

export default Quality
