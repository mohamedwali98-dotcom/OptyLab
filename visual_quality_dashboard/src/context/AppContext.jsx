import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { api, getToken, setToken, clearToken, onUnauthorized } from '../api';
import { BACKEND_URL } from '../backend';

const AppContext = createContext(null);

let _notifId = 0;

export const AppProvider = ({ children }) => {
  const [notifications, setNotifications] = useState([]);
  const [darkMode, setDarkMode] = useState(() => {
    return localStorage.getItem('optylab-dark') === 'true';
  });
  const [settings, setSettings] = useState({
    autoRefresh:       false,
    showConfidence:    true,
    compactView:       false,
    notificationSound: false,
    exportFormat:      'json',
  });

  // Auth state. `user` = { id, email, name } or null. `adminAccess` = boolean.
  const [user, setUser]             = useState(null);
  const [adminAccess, setAdminAccess] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  // Full-screen sign-in modal: { open, mode: 'login' | 'register' }
  const [authModal, setAuthModal]   = useState({ open: false, mode: 'login' });
  // Account hub modal (opened from the top-nav account button): a window with
  // two choices — change password / recent activity — instead of a page tab.
  const [accountOpen, setAccountOpen] = useState(false);

  // Transfer queue (Upload page). Held here — not inside the Upload page — so it
  // survives navigation between pages (Upload <-> Results) without being wiped
  // on remount. It is reset only when the signed-in identity changes.
  const [queue, setQueue] = useState([]);

  const openAuth   = useCallback((mode = 'login') => setAuthModal({ open: true, mode }), []);
  const closeAuth  = useCallback(() => setAuthModal({ open: false, mode: 'login' }), []);
  const openAccount  = useCallback(() => setAccountOpen(true), []);
  const closeAccount = useCallback(() => setAccountOpen(false), []);

  // Clear backend state (uploads, results, heatmaps) - called on project launch, sign in, sign out
  const clearBackendState = useCallback(async () => {
    try {
      await fetch(`${BACKEND_URL}/clear-uploads`, { method: 'DELETE' });
    } catch (e) {
      // Ignore errors - backend might be offline
      console.warn('Could not clear backend state:', e);
    }
  }, []);

  const applySession = useCallback((payload) => {
    setUser(payload.user);
    setAdminAccess(!!payload.admin_access);
    if (payload.token) setToken(payload.token);
  }, []);

  const signIn = useCallback(async (email, password) => {
    // Clear backend state on sign in to ensure clean slate
    await clearBackendState();
    const data = await api.login(email, password);
    applySession(data);
    closeAuth();
    return data;
  }, [applySession, closeAuth, clearBackendState]);

  const signUp = useCallback(async (email, name, password) => {
    // Clear backend state on sign up to ensure clean slate
    await clearBackendState();
    const data = await api.register(email, name, password);
    applySession(data);
    closeAuth();
    return data;
  }, [applySession, closeAuth, clearBackendState]);

  const signOut = useCallback(async () => {
    try {
      await api.clearUploads();
    } catch (e) {
      // Backend error or offline — ignore so logout is never blocked
    }
    // Also clear backend state on sign out to ensure clean slate for next user
    await clearBackendState();
    clearToken();
    setUser(null);
    setAdminAccess(false);
    setQueue([]);
    setAccountOpen(false);
    setAuthModal({ open: true, mode: 'login' });
  }, [clearBackendState]);

  // Listen for automatic 401 unauthorized signals from api.js
  useEffect(() => {
    onUnauthorized(() => {
      signOut();
    });
  }, [signOut]);

  // On mount, restore a session from a stored token (if still valid).
  // Also clear backend state on project launch to ensure clean slate.
  useEffect(() => {
    let cancelled = false;
    
    // Clear backend state on project launch (first load)
    clearBackendState();
    
    const token = getToken();
    if (!token) { setAuthLoading(false); return; }
    api.me()
      .then(data => { if (!cancelled) { setUser(data.user); setAdminAccess(!!data.admin_access); } })
      .catch(() => { if (!cancelled) clearToken(); })
      .finally(() => { if (!cancelled) setAuthLoading(false); });
    return () => { cancelled = true; };
  }, [clearBackendState]);

  // Clear the transfer queue when the signed-in identity changes (sign-out /
  // sign-in to a different account). This does NOT fire on plain navigation
  // between pages, so uploaded files stay visible when switching Upload<->Results.
  const prevUserId = useRef(user?.id);
  useEffect(() => {
    if (prevUserId.current !== user?.id) {
      prevUserId.current = user?.id;
      setQueue([]);
    }
  }, [user?.id]);

  // Dark mode
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('optylab-dark', darkMode);
  }, [darkMode]);

  // Notifications
  const addNotification = useCallback((type, message) => {
    const id = ++_notifId;
    setNotifications(prev => [{ id, type, message, time: new Date() }, ...prev].slice(0, 20));

    setSettings(currentSettings => {
      if (currentSettings.notificationSound) {
        try {
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();
          osc.connect(gain);
          gain.connect(ctx.destination);
          if (type === 'error') {
            osc.frequency.setValueAtTime(300, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(150, ctx.currentTime + 0.3);
          } else {
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.1);
          }
          gain.gain.setValueAtTime(0.1, ctx.currentTime);
          gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
          osc.start(ctx.currentTime);
          osc.stop(ctx.currentTime + 0.3);
        } catch (e) { /* blocked before interaction */ }
      }
      return currentSettings;
    });
  }, []);

  const clearNotifications  = useCallback(() => setNotifications([]), []);
  const removeNotification  = useCallback((id) => setNotifications(prev => prev.filter(n => n.id !== id)), []);
  const toggleDarkMode      = useCallback(() => setDarkMode(d => !d), []);
  const updateSetting       = useCallback((key, value) => setSettings(prev => ({ ...prev, [key]: value })), []);

  return (
    <AppContext.Provider value={{
      notifications, addNotification, clearNotifications, removeNotification,
      darkMode, toggleDarkMode,
      settings, updateSetting,
      user, adminAccess, authLoading, signIn, signUp, signOut, openAuth, closeAuth, authModal,
      accountOpen, openAccount, closeAccount,
      queue, setQueue,
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const AppContextRef = AppContext;

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside AppProvider');
  return ctx;
};
