/**
 * Main App Component
 */

import React from 'react'
import { useAppStore } from './store'
import MainLayout from './layouts/MainLayout'
import Dashboard from './pages/Dashboard'
import Approvals from './pages/Approvals'
import Quality from './pages/Quality'
import Recommendations from './pages/Recommendations'
import Compliance from './pages/Compliance'
import Settings from './pages/Settings'

const App: React.FC = () => {
  const { currentTab, error, isLoading } = useAppStore()

  const renderContent = () => {
    switch (currentTab) {
      case 'dashboard':
        return <Dashboard />
      case 'recommendations':
        return <Recommendations />
      case 'approvals':
        return <Approvals />
      case 'quality':
        return <Quality />
      case 'compliance':
        return <Compliance />
      case 'settings':
        return <Settings />
      default:
        return <Dashboard />
    }
  }

  return (
    <MainLayout>
      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}
      {isLoading && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      )}
      {renderContent()}
    </MainLayout>
  )
}

export default App
