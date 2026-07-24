import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const AppContext = createContext(null);

let _notifId = 0;

/* ── Mock user loaded from localStorage (simulates a persisted session) ───── */
const loadUser = () => {
  try { return JSON.parse(localStorage.getItem('optylab-user')) || null; }
  catch { return null; }
};

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

  /* ── Auth state ─────────────────────────────────────────────────────────── */
  const [user, setUser] = useState(loadUser);   // null = logged out

  const signInMock = useCallback((profile) => {
    // profile = { name, email, picture }
    localStorage.setItem('optylab-user', JSON.stringify(profile));
    setUser(profile);
  }, []);

  const signOut = useCallback(() => {
    localStorage.removeItem('optylab-user');
    setUser(null);
  }, []);

  /* ── Dark mode ──────────────────────────────────────────────────────────── */
  useEffect(() => {
    document.documentElement.classList.toggle('dark', darkMode);
    localStorage.setItem('optylab-dark', darkMode);
  }, [darkMode]);

  /* ── Notifications ──────────────────────────────────────────────────────── */
  const addNotification = useCallback((type, message) => {
    const id = ++_notifId;
    setNotifications(prev => [{ id, type, message, time: new Date() }, ...prev].slice(0, 20));
    
    // Play sound alert if enabled
    setSettings(currentSettings => {
      if (currentSettings.notificationSound) {
        // Simple synthetic ping using Web Audio API
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
        } catch (e) {
          // AudioContext might be blocked by browser policy before user interaction
        }
      }
      return currentSettings;
    });
  }, []);

  const clearNotifications = useCallback(() => setNotifications([]), []);
  const removeNotification = useCallback((id) =>
    setNotifications(prev => prev.filter(n => n.id !== id)), []);

  const toggleDarkMode  = useCallback(() => setDarkMode(d => !d), []);
  const updateSetting   = useCallback((key, value) =>
    setSettings(prev => ({ ...prev, [key]: value })), []);

  return (
    <AppContext.Provider value={{
      notifications, addNotification, clearNotifications, removeNotification,
      darkMode, toggleDarkMode,
      settings, updateSetting,
      user, signInMock, signOut,
    }}>
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used inside AppProvider');
  return ctx;
};
