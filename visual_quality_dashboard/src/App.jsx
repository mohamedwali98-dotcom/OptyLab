import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import TopNavBar from './components/TopNavBar'
import SideBar, { SIDEBAR_W } from './components/SideBar'
import UploadImagery from './pages/UploadImagery'
import AnalysisAdmin from './pages/AnalysisAdmin'
import AnalysisResults from './pages/AnalysisResults'
import './index.css'

function App() {
  return (
    <AppProvider>
      <Router>
        {/* Fixed top bar */}
        <TopNavBar />

        {/* Fixed left sidebar */}
        <SideBar />

        {/* Page content — offset from top bar (64px) and sidebar */}
        <div
          style={{ marginTop: '64px', marginLeft: `${SIDEBAR_W}px`, minHeight: 'calc(100vh - 64px)' }}
          className="bg-background text-on-background font-body-md text-body-md"
        >
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/upload"  element={<UploadImagery />} />
            <Route path="/admin"   element={<AnalysisAdmin />} />
            <Route path="/results" element={<AnalysisResults />} />
          </Routes>
        </div>
      </Router>
    </AppProvider>
  )
}

export default App
