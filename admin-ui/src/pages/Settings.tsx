/**
 * Settings Page
 */

import React, { useState } from 'react'
import { Settings as SettingsIcon, Save } from 'lucide-react'

const Settings: React.FC = () => {
  const [settings, setSettings] = useState({
    apiUrl: localStorage.getItem('api_url') || 'http://localhost:8000',
    theme: localStorage.getItem('theme') || 'light',
    refreshInterval: localStorage.getItem('refresh_interval') || '30',
    defaultScenario: localStorage.getItem('default_scenario') || 'default',
    maxRecommendations: localStorage.getItem('max_recommendations') || '5',
    approverName: localStorage.getItem('approver_name') || 'admin',
  })

  const handleChange = (field: string, value: string) => {
    setSettings((prev) => ({ ...prev, [field]: value }))
  }

  const handleSave = () => {
    Object.entries(settings).forEach(([key, value]) => {
      localStorage.setItem(key, String(value))
    })
    alert('Settings saved successfully!')
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <SettingsIcon /> Settings
        </h2>
        <p className="text-gray-600 mt-1">Configure your admin dashboard</p>
      </div>

      {/* Settings Form */}
      <div className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* API Configuration */}
        <div>
          <h3 className="text-lg font-semibold mb-4">API Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API URL
              </label>
              <input
                type="text"
                value={settings.apiUrl}
                onChange={(e) => handleChange('apiUrl', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              />
              <p className="text-xs text-gray-500 mt-1">Backend API endpoint</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Refresh Interval (seconds)
              </label>
              <input
                type="number"
                value={settings.refreshInterval}
                onChange={(e) => handleChange('refreshInterval', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              />
              <p className="text-xs text-gray-500 mt-1">Auto-refresh dashboard data</p>
            </div>
          </div>
        </div>

        {/* Recommendation Settings */}
        <div>
          <h3 className="text-lg font-semibold mb-4">Recommendation Defaults</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Default Scenario
              </label>
              <select
                value={settings.defaultScenario}
                onChange={(e) => handleChange('defaultScenario', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              >
                <option value="default">Default</option>
                <option value="new_customer">New Customer</option>
                <option value="high_value">High Value</option>
                <option value="retention">Retention</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Max Recommendations
              </label>
              <input
                type="number"
                value={settings.maxRecommendations}
                onChange={(e) => handleChange('maxRecommendations', e.target.value)}
                min="1"
                max="20"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              />
            </div>
          </div>
        </div>

        {/* User Settings */}
        <div>
          <h3 className="text-lg font-semibold mb-4">User Settings</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Approver Name
              </label>
              <input
                type="text"
                value={settings.approverName}
                onChange={(e) => handleChange('approverName', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              />
              <p className="text-xs text-gray-500 mt-1">
                Your name for approval tracking
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Theme
              </label>
              <select
                value={settings.theme}
                onChange={(e) => handleChange('theme', e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-teal-500"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="pt-4 border-t border-gray-200">
          <button
            onClick={handleSave}
            className="w-full px-6 py-3 bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors flex items-center justify-center gap-2 font-medium"
          >
            <Save size={20} />
            Save Settings
          </button>
        </div>
      </div>

      {/* Additional Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-semibold text-blue-900">ℹ️ About</h4>
        <p className="text-sm text-blue-800 mt-2">
          Wine Recommendation CRM Platform v1.0.0
        </p>
        <p className="text-sm text-blue-800">
          Platform Status: <span className="font-semibold text-green-600">🟢 OPERATIONAL</span>
        </p>
        <p className="text-sm text-blue-800 mt-2">
          Last updated: {new Date().toLocaleDateString()}
        </p>
      </div>
    </div>
  )
}

export default Settings
