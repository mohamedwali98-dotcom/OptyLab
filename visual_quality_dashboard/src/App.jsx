import React, { useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext'
import TopNavBar from './components/TopNavBar'
import SideBar, { SIDEBAR_W } from './components/SideBar'
import AuthModal from './components/AuthModal'
import UploadImagery from './pages/UploadImagery'
import AnalysisAdmin from './pages/AnalysisAdmin'
import AnalysisResults from './pages/AnalysisResults'
import Account from './pages/Account'
import AccessControl from './pages/AccessControl'
import './index.css'

// Gate: shows the full-screen sign-in modal and BLOCKS the protected page until
// the user is authenticated. We must not call setState during render (that
// white-screens the app), so the modal is opened via an effect and the page
// content is only painted once `user` exists. While loading or signed-out the
// page area stays empty so the site "opens" straight to the sign-in window.
const AuthGate = ({ children, admin = false }) => {
  const { user, adminAccess, authLoading, openAuth } = useApp();

  useEffect(() => {
    if (authLoading) return;            // wait for session restore
    if (!user) openAuth('login');
    else if (admin && !adminAccess) openAuth('login');
  }, [authLoading, user, adminAccess, admin, openAuth]);

  // Block the protected content until authenticated.
  if (authLoading || !user) return null;
  if (admin && !adminAccess) return null;
  return children;
};

const Protected = ({ children }) => <AuthGate>{children}</AuthGate>;
const AdminProtected = ({ children }) => <AuthGate admin>{children}</AuthGate>;

// Full app shell. Until the user is authenticated we render NOTHING but the
// sign-in modal — so opening the site shows only the sign-in window, with no
// nav bar, sidebar, or page content peeking behind it. The modal is opened by
// THIS component (which always renders) rather than a gated route, otherwise a
// signed-out user would see a blank screen.
function Shell() {
  const { user, authLoading, openAuth } = useApp();

  // Open the sign-in modal as soon as we know there's no session.
  useEffect(() => {
    if (!authLoading && !user) openAuth('login');
  }, [authLoading, user, openAuth]);

  // While the session is still loading, show nothing (avoids a flash).
  if (authLoading) return null;

  const signedOut = !user;

  return (
    <Router>
      {!signedOut && <TopNavBar />}
      {!signedOut && <SideBar />}
      <AuthModal />

      {!signedOut && (
        <div
          style={{ marginTop: '64px', marginLeft: SIDEBAR_W + 'px', minHeight: 'calc(100vh - 64px)' }}
          className="bg-background text-on-background font-body-md text-body-md"
        >
          <Routes>
            <Route path="/" element={<Navigate to="/upload" replace />} />
            <Route path="/upload"  element={<Protected><UploadImagery /></Protected>} />
            <Route path="/results" element={<Protected><AnalysisResults /></Protected>} />
            <Route path="/account" element={<Protected><Account /></Protected>} />
            <Route path="/access"  element={<AdminProtected><AccessControl /></AdminProtected>} />
            <Route path="/admin"   element={<AdminProtected><AnalysisAdmin /></AdminProtected>} />
          </Routes>
        </div>
      )}
    </Router>
  );
}

function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}

export default App
