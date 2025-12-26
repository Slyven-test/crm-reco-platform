/**
 * Dashboard Page - Main Analytics View
 */

import React, { useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { AlertCircle, CheckCircle, TrendingUp, Users } from 'lucide-react'
import { api } from '../api/client'
import { useAppStore } from '../store'

const Dashboard: React.FC = () => {
  const { setIsLoading, setError } = useAppStore()
  const [stats, setStats] = useState<any>(null)
  const [qualityData, setQualityData] = useState<any>(null)
  const [complianceData, setComplianceData] = useState<any>(null)

  useEffect(() => {
    loadDashboardData()
  }, [])

  const loadDashboardData = async () => {
    setIsLoading(true)
    try {
      // Load statistics
      const statsRes = await api.getStatistics()
      setStats(statsRes.data)

      // Load quality report
      const qualityRes = await api.getQualityReport(7)
      setQualityData(qualityRes.data)

      // Load compliance summary
      const complianceRes = await api.getComplianceSummary()
      setComplianceData(complianceRes.data)
    } catch (error: any) {
      setError(error.message || 'Failed to load dashboard data')
    } finally {
      setIsLoading(false)
    }
  }

  const COLORS = ['#14b8a6', '#3b82f6', '#f59e0b', '#ef4444']

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Recommendations"
          value={stats?.total_recommendations || 0}
          icon={<TrendingUp className="text-teal-600" />}
          change="+12.5%"
        />
        <KPICard
          title="Unique Customers"
          value={stats?.unique_customers || 0}
          icon={<Users className="text-blue-600" />}
          change="+8.2%"
        />
        <KPICard
          title="Approval Rate"
          value={`${complianceData?.approval_rate || 0}%`}
          icon={<CheckCircle className="text-green-600" />}
          change="+4.3%"
        />
        <KPICard
          title="Pending Approvals"
          value={complianceData?.approval_summary?.PENDING || 0}
          icon={<AlertCircle className="text-orange-600" />}
          change="-2.1%"
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quality Trends */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Quality Trends (7 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={qualityData?.recent_runs || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="run_id" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="coverage_score"
                stroke="#14b8a6"
                name="Coverage"
              />
              <Line
                type="monotone"
                dataKey="accuracy_score"
                stroke="#3b82f6"
                name="Accuracy"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Approval Status Distribution */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Approval Status</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={Object.entries(complianceData?.approval_summary || {}).map(
                  ([name, value]) => ({ name, value })
                )}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {COLORS.map((color, index) => (
                  <Cell key={`cell-${index}`} fill={color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Quality Distribution */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">Quality Level Distribution</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={getQualityDistribution(qualityData?.quality_distribution)}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="count" fill="#14b8a6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ActivityCard title="Latest Statistics" data={stats} />
        <ActivityCard title="Quality Summary" data={qualityData} />
      </div>
    </div>
  )
}

interface KPICardProps {
  title: string
  value: string | number
  icon: React.ReactNode
  change: string
}

const KPICard: React.FC<KPICardProps> = ({ title, value, icon, change }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-600 text-sm">{title}</p>
        <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        <p className="text-green-600 text-sm mt-2">{change} from last week</p>
      </div>
      <div className="text-4xl">{icon}</div>
    </div>
  </div>
)

interface ActivityCardProps {
  title: string
  data: any
}

const ActivityCard: React.FC<ActivityCardProps> = ({ title, data }) => (
  <div className="bg-white rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold mb-4">{title}</h3>
    <div className="space-y-3">
      {Object.entries(data || {}).map(([key, value]) => (
        <div key={key} className="flex justify-between text-sm">
          <span className="text-gray-600">{formatKey(key)}</span>
          <span className="font-semibold text-gray-900">
            {typeof value === 'number' ? value.toFixed(2) : String(value)}
          </span>
        </div>
      ))}
    </div>
  </div>
)

function formatKey(key: string): string {
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

function getQualityDistribution(distribution: any): any[] {
  if (!distribution) return []
  return Object.entries(distribution).map(([name, count]) => ({ name, count }))
}

export default Dashboard
