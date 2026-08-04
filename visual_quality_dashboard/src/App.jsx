import React, { useEffect, useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext'
import TopNavBar from './components/TopNavBar'
import SideBar, { SIDEBAR_W } from './components/SideBar'
import AuthModal from './components/AuthModal'
import AccountModal from './components/AccountModal'
import UploadImagery from './pages/UploadImagery'
import AnalysisAdmin from './pages/AnalysisAdmin'
import AnalysisResults from './pages/AnalysisResults'
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

// Smooth page-to-page transition: the page content gently fades + lifts in
// (300ms) on every route change instead of snapping. We key the wrapper on the
// pathname so React remounts it and replays the CSS animation. The fade is
// purely visual — protected routes still gate exactly as before.
const ANIM_KEYFRAMES = `
  @keyframes pageFadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }
`;

const AnimatedRoutes = () => {
  const location = useLocation();
  return (
    <div
      key={location.pathname}
      style={{ animation: 'pageFadeIn 300ms ease', willChange: 'opacity, transform' }}
    >
      <Routes location={location}>
        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route path="/upload"  element={<Protected><UploadImagery /></Protected>} />
        <Route path="/results" element={<Protected><AnalysisResults /></Protected>} />
        <Route path="/access"  element={<AdminProtected><AccessControl /></AdminProtected>} />
        <Route path="/admin"   element={<AdminProtected><AnalysisAdmin /></AdminProtected>} />
      </Routes>
    </div>
  );
};

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
      <style>{ANIM_KEYFRAMES}</style>
      {!signedOut && <TopNavBar />}
      {!signedOut && <SideBar />}
      <AuthModal />
      <AccountModal />

      {!signedOut && (
        <div
          style={{ marginTop: '64px', marginLeft: SIDEBAR_W + 'px', minHeight: 'calc(100vh - 64px)' }}
          className="bg-background text-on-background font-body-md text-body-md"
        >
          <AnimatedRoutes />
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
