import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { api, getToken, setToken, clearToken } from '../api';

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

  const openAuth   = useCallback((mode = 'login') => setAuthModal({ open: true, mode }), []);
  const closeAuth  = useCallback(() => setAuthModal(m => ({ ...m, open: false })), []);

  const applySession = useCallback((payload) => {
    setUser(payload.user);
    setAdminAccess(!!payload.admin_access);
    if (payload.token) setToken(payload.token);
  }, []);

  const signIn = useCallback(async (email, password) => {
    const data = await api.login(email, password);
    applySession(data);
    closeAuth();
    return data;
  }, [applySession, closeAuth]);

  const signUp = useCallback(async (email, name, password) => {
    const data = await api.register(email, name, password);
    applySession(data);
    closeAuth();
    return data;
  }, [applySession, closeAuth]);

  const signOut = useCallback(() => {
    clearToken();
    setUser(null);
    setAdminAccess(false);
  }, []);

  // On mount, restore a session from a stored token (if still valid).
  useEffect(() => {
    let cancelled = false;
    const token = getToken();
    if (!token) { setAuthLoading(false); return; }
    api.me()
      .then(data => { if (!cancelled) { setUser(data.user); setAdminAccess(!!data.admin_access); } })
      .catch(() => { if (!cancelled) clearToken(); })
      .finally(() => { if (!cancelled) setAuthLoading(false); });
    return () => { cancelled = true; };
  }, []);

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
