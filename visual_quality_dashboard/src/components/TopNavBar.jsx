import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';

/* ── Small helper: format relative time ───────────────────────────────────── */
const relTime = (date) => {
  const s = Math.floor((Date.now() - date) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return date.toLocaleDateString();
};

/* ── Icon map for notification types ─────────────────────────────────────── */
const NOTIF_ICON = {
  success: { icon: 'check_circle', color: '#2a6918' },
  error:   { icon: 'error',        color: '#ba1a1a' },
  info:    { icon: 'info',         color: '#1a6891' },
  warning: { icon: 'warning',      color: '#a16207' },
};

/* ── Toggle Switch component ─────────────────────────────────────────────── */
const Toggle = ({ value, onChange, label, sublabel }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', gap: '12px' }}>
    <div>
      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--color-on-surface, #191c1e)' }}>{label}</div>
      {sublabel && <div style={{ fontSize: '11px', color: 'var(--color-secondary, #777)', marginTop: '1px' }}>{sublabel}</div>}
    </div>
    <button
      onClick={() => onChange(!value)}
      aria-label={label}
      style={{
        width: '40px', height: '22px', borderRadius: '11px', border: 'none',
        background: value ? 'var(--color-primary, #2a6918)' : 'var(--color-surface-variant, #e0e3e5)',
        cursor: 'pointer', position: 'relative', flexShrink: 0,
        transition: 'background 0.2s',
      }}
    >
      <span style={{
        position: 'absolute', top: '3px',
        left: value ? '21px' : '3px',
        width: '16px', height: '16px', borderRadius: '50%',
        background: value ? '#fff' : 'var(--color-outline, #717a6b)',
        transition: 'left 0.2s',
        display: 'block',
      }} />
    </button>
  </div>
);

/* ── Dropdown panel wrapper ──────────────────────────────────────────────── */
const Panel = ({ children, style }) => (
  <div
    style={{
      position: 'absolute', top: 'calc(100% + 10px)', right: 0,
      width: '300px', background: 'var(--color-surface-container-lowest, #fff)',
      border: '1px solid var(--color-surface-variant, #e0e3e5)',
      borderRadius: '12px', boxShadow: '0 8px 32px rgba(0,0,0,0.14)',
      zIndex: 200, overflow: 'hidden',
      animation: 'panelIn 0.15s ease',
      ...style,
    }}
  >
    {children}
  </div>
);

/* ═══════════════════════════════════════════════════════════════════════════ */
const TopNavBar = () => {
  const {
    notifications, clearNotifications, removeNotification,
    darkMode, toggleDarkMode,
    settings, updateSetting,
    user, signInMock, signOut,
  } = useApp();

  const [showNotifs,   setShowNotifs]   = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showProfile,  setShowProfile]  = useState(false);

  const notifsRef   = useRef(null);
  const settingsRef = useRef(null);
  const profileRef  = useRef(null);

  const unread = notifications.length;

  /* Close panels when clicking outside */
  useEffect(() => {
    const handler = (e) => {
      if (notifsRef.current   && !notifsRef.current.contains(e.target))   setShowNotifs(false);
      if (settingsRef.current && !settingsRef.current.contains(e.target)) setShowSettings(false);
      if (profileRef.current  && !profileRef.current.contains(e.target))  setShowProfile(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const toggleNotifs   = () => { setShowNotifs(v => !v);   setShowSettings(false); setShowProfile(false); };
  const toggleSettings = () => { setShowSettings(v => !v); setShowNotifs(false);   setShowProfile(false); };
  const toggleProfile  = () => { setShowProfile(v => !v);  setShowNotifs(false);   setShowSettings(false); };

  return (
    <>
      <style>{`
        @keyframes panelIn {
          from { opacity: 0; transform: translateY(-6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <header style={{
        position: 'fixed', top: 0, left: 0, right: 0, height: '64px', zIndex: 50,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 24px',
        background: 'var(--color-surface-container-lowest, #fff)',
        borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
      }}>

        {/* Logo */}
        <img
          src="https://lh3.googleusercontent.com/aida-public/AB6AXuA5Oy1uZrGc-3lrWxiE00vAqLq0ioa1XoTpI_93qwdgFYxIhu5Z46MqAezeZIy7B6MmiomQQZ03BojhqprfCRp9U36M4UAvt_PVxbRY9_vLwaak7cDRMpJDkhrkCwmpN807UXFehfWZYi925fF0gfo_9JgP3CsyfhfFy3WYScGHrKiBJreEqaUlwbfBo0ClGS3z7v5iNI4UGKO6NFyO6w5152kRLwv8UUD9f9JL5jGoSIREPZZg4Bw8zujVKWCML188ODlW6I2XIfIj"
          alt="Optylab Logo"
          style={{ height: '40px', width: 'auto', objectFit: 'contain' }}
        />

        {/* Trailing actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>

          {/* ── Notifications button ──────────────────────────────────────── */}
          <div ref={notifsRef} style={{ position: 'relative' }}>
            <button
              onClick={toggleNotifs}
              title="Notifications"
              style={{
                background: showNotifs ? 'var(--color-surface-container-low, #f5f5f5)' : 'none',
                border: 'none', cursor: 'pointer', padding: '8px', borderRadius: '8px',
                color: 'var(--color-primary, #2a6918)',
                display: 'flex', alignItems: 'center', position: 'relative',
              }}
            >
              <span className="material-symbols-outlined">notifications</span>
              {unread > 0 && (
                <span style={{
                  position: 'absolute', top: '4px', right: '4px',
                  minWidth: '16px', height: '16px', borderRadius: '8px',
                  background: '#ba1a1a', color: '#fff',
                  fontSize: '10px', fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  padding: '0 3px',
                }}>
                  {unread > 9 ? '9+' : unread}
                </span>
              )}
            </button>

            {showNotifs && (
              <Panel>
                {/* Header */}
                <div style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '12px 16px', borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)',
                }}>
                  <span style={{ fontWeight: 700, fontSize: '14px' }}>Notifications</span>
                  {notifications.length > 0 && (
                    <button
                      onClick={clearNotifications}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '12px', color: 'var(--color-secondary, #777)' }}
                    >
                      Clear all
                    </button>
                  )}
                </div>

                {/* List */}
                <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
                  {notifications.length === 0 ? (
                    <div style={{ padding: '28px 16px', textAlign: 'center', color: 'var(--color-secondary, #777)', fontSize: '13px' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: '28px', display: 'block', marginBottom: '6px', opacity: 0.5 }}>notifications_none</span>
                      No notifications yet
                    </div>
                  ) : (
                    notifications.map(n => {
                      const { icon, color } = NOTIF_ICON[n.type] || NOTIF_ICON.info;
                      return (
                        <div key={n.id} style={{
                          display: 'flex', alignItems: 'flex-start', gap: '10px',
                          padding: '10px 16px',
                          borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)',
                          background: 'transparent',
                        }}>
                          <span className="material-symbols-outlined" style={{ fontSize: '18px', color, marginTop: '1px', flexShrink: 0, fontVariationSettings: "'FILL' 1" }}>
                            {icon}
                          </span>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: '13px', color: 'var(--color-on-surface, #191c1e)', lineHeight: '1.4', wordBreak: 'break-word' }}>
                              {n.message}
                            </div>
                            <div style={{ fontSize: '11px', color: 'var(--color-secondary, #777)', marginTop: '3px' }}>
                              {relTime(n.time)}
                            </div>
                          </div>
                          <button
                            onClick={() => removeNotification(n.id)}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-secondary, #777)', padding: '0', flexShrink: 0, marginTop: '2px' }}
                          >
                            <span className="material-symbols-outlined" style={{ fontSize: '14px' }}>close</span>
                          </button>
                        </div>
                      );
                    })
                  )}
                </div>
              </Panel>
            )}
          </div>

          {/* ── Settings button ───────────────────────────────────────────── */}
          <div ref={settingsRef} style={{ position: 'relative' }}>
            <button
              onClick={toggleSettings}
              title="Settings"
              style={{
                background: showSettings ? 'var(--color-surface-container-low, #f5f5f5)' : 'none',
                border: 'none', cursor: 'pointer', padding: '8px', borderRadius: '8px',
                color: 'var(--color-primary, #2a6918)',
                display: 'flex', alignItems: 'center',
              }}
            >
              <span className="material-symbols-outlined">settings</span>
            </button>

            {showSettings && (
              <Panel>
                {/* Header */}
                <div style={{
                  padding: '12px 16px',
                  borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)',
                  fontWeight: 700, fontSize: '14px',
                }}>
                  Settings
                </div>

                <div style={{ padding: '8px 16px 4px' }}>
                  {/* ── Appearance ─────────────────────────────── */}
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--color-secondary, #777)', marginBottom: '4px', textTransform: 'uppercase' }}>
                    Appearance
                  </div>

                  <Toggle
                    value={darkMode}
                    onChange={toggleDarkMode}
                    label="Dark Mode"
                    sublabel="Switch between light and dark theme"
                  />

                  <Toggle
                    value={settings.compactView}
                    onChange={v => updateSetting('compactView', v)}
                    label="Compact View"
                    sublabel="Reduce row height in results table"
                  />

                  <div style={{ borderTop: '1px solid var(--color-surface-variant, #e0e3e5)', margin: '8px 0' }} />

                  {/* ── Workflow ────────────────────────────────── */}
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--color-secondary, #777)', marginBottom: '4px', textTransform: 'uppercase' }}>
                    Workflow
                  </div>

                  <Toggle
                    value={settings.autoRefresh}
                    onChange={v => updateSetting('autoRefresh', v)}
                    label="Auto-refresh Results"
                    sublabel="Poll results every 10 s automatically"
                  />

                  <Toggle
                    value={settings.showConfidence}
                    onChange={v => updateSetting('showConfidence', v)}
                    label="Show Confidence Bar"
                    sublabel="Display confidence score in results"
                  />

                  <div style={{ borderTop: '1px solid var(--color-surface-variant, #e0e3e5)', margin: '8px 0' }} />

                  {/* ── Notifications ───────────────────────────── */}
                  <div style={{ fontSize: '10px', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--color-secondary, #777)', marginBottom: '4px', textTransform: 'uppercase' }}>
                    Notifications
                  </div>

                  <Toggle
                    value={settings.notificationSound}
                    onChange={v => updateSetting('notificationSound', v)}
                    label="Sound Alerts"
                    sublabel="Play a sound on upload / classify events"
                  />

                  <div style={{ borderTop: '1px solid var(--color-surface-variant, #e0e3e5)', margin: '8px 0' }} />
                </div>

                <div style={{ padding: '10px 16px', borderTop: '1px solid var(--color-surface-variant, #e0e3e5)' }}>
                  <p style={{ fontSize: '11px', color: 'var(--color-secondary, #777)', margin: 0 }}>
                    Settings are saved locally. More options coming soon.
                  </p>
                </div>
              </Panel>
            )}
          </div>

          {/* ── Profile / Auth button ─────────────────────────────────────── */}
          <div ref={profileRef} style={{ position: 'relative', marginLeft: '4px' }}>
            <div
              onClick={toggleProfile}
              title={user ? user.name : 'Sign in'}
              style={{
                width: '36px', height: '36px', borderRadius: '50%', overflow: 'hidden',
                border: `2px solid ${showProfile ? 'var(--color-primary, #2a6918)' : 'var(--color-outline-variant, #ccc)'}`,
                cursor: 'pointer', flexShrink: 0,
                background: user ? 'transparent' : 'var(--color-surface-container-low, #f5f5f5)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'border-color 0.15s',
              }}
            >
              {user?.picture ? (
                <img alt={user.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} src={user.picture} />
              ) : user ? (
                <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--color-primary, #2a6918)' }}>
                  {user.name?.[0]?.toUpperCase() || '?'}
                </span>
              ) : (
                <span className="material-symbols-outlined" style={{ fontSize: '20px', color: 'var(--color-secondary, #777)' }}>person</span>
              )}
            </div>

            {showProfile && (
              <Panel style={{ width: '260px' }}>
                {user ? (
                  /* ── Signed-in view ── */
                  <>
                    {/* User info */}
                    <div style={{ padding: '16px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)' }}>
                      <div style={{
                        width: '44px', height: '44px', borderRadius: '50%', flexShrink: 0,
                        background: 'var(--color-primary-container, #d0e4ff)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        overflow: 'hidden',
                      }}>
                        {user.picture
                          ? <img src={user.picture} alt={user.name} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                          : <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--color-primary, #2a6918)' }}>{user.name?.[0]?.toUpperCase()}</span>
                        }
                      </div>
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: '14px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.name}</div>
                        <div style={{ fontSize: '12px', color: 'var(--color-secondary, #777)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.email}</div>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '4px', background: 'var(--color-primary-container, #d0e4ff)', borderRadius: '99px', padding: '2px 8px' }}>
                          <span className="material-symbols-outlined" style={{ fontSize: '12px', color: 'var(--color-primary, #2a6918)', fontVariationSettings: "'FILL' 1" }}>verified</span>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--color-primary, #2a6918)' }}>Google Account</span>
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div style={{ padding: '8px' }}>
                      <button style={{
                        width: '100%', padding: '9px 12px', borderRadius: '8px', border: 'none',
                        background: 'none', cursor: 'pointer', textAlign: 'left',
                        display: 'flex', alignItems: 'center', gap: '10px',
                        fontSize: '13px', color: 'var(--color-on-surface, #191c1e)',
                      }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-surface-container-low, #f5f5f5)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'none'}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>manage_accounts</span>
                        Manage Google Account
                      </button>
                      <button
                        onClick={() => { signOut(); setShowProfile(false); }}
                        style={{
                          width: '100%', padding: '9px 12px', borderRadius: '8px', border: 'none',
                          background: 'none', cursor: 'pointer', textAlign: 'left',
                          display: 'flex', alignItems: 'center', gap: '10px',
                          fontSize: '13px', color: 'var(--color-error, #ba1a1a)',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'var(--color-error-container, #ffdad6)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'none'}
                      >
                        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>logout</span>
                        Sign out
                      </button>
                    </div>
                  </>
                ) : (
                  /* ── Signed-out view ── */
                  <>
                    <div style={{ padding: '20px 16px 12px', textAlign: 'center', borderBottom: '1px solid var(--color-surface-variant, #e0e3e5)' }}>
                      <span className="material-symbols-outlined" style={{ fontSize: '40px', color: 'var(--color-secondary, #777)', display: 'block', marginBottom: '8px' }}>account_circle</span>
                      <div style={{ fontWeight: 700, fontSize: '15px', marginBottom: '4px' }}>Sign in to OptyLab</div>
                      <div style={{ fontSize: '12px', color: 'var(--color-secondary, #777)' }}>Access your analysis history and sync results across devices.</div>
                    </div>

                    <div style={{ padding: '12px 16px 16px' }}>
                      {/* Google Sign-In button (mock) */}
                      <button
                        onClick={() => {
                          /* ── PRODUCTION: replace this block with real Google OAuth ──
                             import { googleLogIn } from './auth';
                             googleLogIn().then(profile => signInMock(profile));
                          ─────────────────────────────────────────────────────────── */
                          signInMock({
                            name: 'Mohammed (Demo)',
                            email: 'user@optylab.ai',
                            picture: null,
                          });
                          setShowProfile(false);
                        }}
                        style={{
                          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px',
                          padding: '10px 16px', borderRadius: '8px',
                          border: '1px solid var(--color-outline-variant, #ccc)',
                          background: '#fff', cursor: 'pointer',
                          fontSize: '14px', fontWeight: 600,
                          boxShadow: '0 1px 3px rgba(0,0,0,0.10)',
                          transition: 'box-shadow 0.15s',
                        }}
                        onMouseEnter={e => e.currentTarget.style.boxShadow = '0 3px 8px rgba(0,0,0,0.15)'}
                        onMouseLeave={e => e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.10)'}
                      >
                        {/* Google G logo */}
                        <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
                          <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
                          <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18z" fill="#34A853"/>
                          <path d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
                          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
                        </svg>
                        Sign in with Google
                      </button>

                      <p style={{ fontSize: '11px', color: 'var(--color-secondary, #777)', textAlign: 'center', marginTop: '10px', lineHeight: '1.4' }}>
                        By signing in you agree to our Terms of Service.
                        <br />OAuth 2.0 — your password is never shared.
                      </p>
                    </div>
                  </>
                )}
              </Panel>
            )}
          </div>
        </div>
      </header>
    </>
  );
};

export default TopNavBar;
