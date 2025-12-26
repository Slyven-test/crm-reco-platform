/**
 * Main Layout Component
 */

import React, { useState } from 'react'
import {
  BarChart3,
  CheckCircle,
  AlertCircle,
  Settings,
  Menu,
  X,
  LogOut,
} from 'lucide-react'
import { useAppStore } from '../store'
import clsx from 'classnames'

interface MainLayoutProps {
  children: React.ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { currentTab, setCurrentTab } = useAppStore()

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'recommendations', label: 'Recommendations', icon: CheckCircle },
    { id: 'approvals', label: 'Approvals', icon: AlertCircle },
    { id: 'quality', label: 'Quality', icon: BarChart3 },
    { id: 'compliance', label: 'Compliance', icon: CheckCircle },
    { id: 'settings', label: 'Settings', icon: Settings },
  ] as const

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div
        className={clsx(
          'bg-slate-900 text-white transition-all duration-300 ease-in-out',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      >
        <div className="flex items-center justify-between p-4">
          {sidebarOpen && <h1 className="text-xl font-bold">🍷 Wine Reco</h1>}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1 hover:bg-slate-800 rounded"
          >
            {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        <nav className="mt-8 space-y-2 px-4">
          {tabs.map((tab) => {
            const Icon = tab.icon
            const isActive = currentTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setCurrentTab(tab.id)}
                className={clsx(
                  'w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                  isActive ? 'bg-teal-600 text-white' : 'text-gray-300 hover:bg-slate-800'
                )}
              >
                <Icon size={20} />
                {sidebarOpen && <span className="text-sm">{tab.label}</span>}
              </button>
            )
          })}
        </nav>

        <div className="absolute bottom-0 left-0 right-0 p-4">
          <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-slate-800 transition-colors">
            <LogOut size={20} />
            {sidebarOpen && <span className="text-sm">Logout</span>}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">
              {tabs.find((t) => t.id === currentTab)?.label}
            </h2>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-600">
                {new Date().toLocaleDateString()}
              </div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="max-w-7xl mx-auto px-6 py-8">{children}</div>
      </div>
    </div>
  )
}

export default MainLayout
