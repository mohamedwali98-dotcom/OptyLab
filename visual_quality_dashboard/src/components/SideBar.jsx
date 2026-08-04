import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApp } from '../context/AppContext';

export const SIDEBAR_W = 200; // px — exported so App.jsx can import it

const NAV_ITEMS = [
  { path: '/upload',  label: 'Upload',  icon: 'cloud_upload'        },
  { path: '/results', label: 'Results', icon: 'analytics'           },
  // Admin is rendered separately (red, and only for users with admin access).
];

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
      position: 'absolute', bottom: 'calc(100% + 10px)', left: 0,
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

/* ── Reusable nav link (matches the existing NAV_ITEMS style) ─────────────────── */
const NavLinkStyled = ({ to, label, icon, active }) => (
  <Link
    to={to}
    title={label}
    style={{
      display: 'flex',
      flexDirection: 'row',
      alignItems: 'center',
      gap: '12px',
      padding: '11px 14px',
      borderRadius: '12px',
      textDecoration: 'none',
      transition: 'background 0.15s, color 0.15s',
      background: active ? 'var(--color-primary-container, #d0e4ff)' : 'transparent',
      color: active ? 'var(--color-primary, #2a6918)' : 'var(--color-secondary, #777)',
      fontWeight: active ? 700 : 500,
    }}
    onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--color-surface-container-low, #f5f5f5)'; }}
    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
  >
    <span className="material-symbols-outlined" style={{ fontSize: '22px', flexShrink: 0, fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0" }}>
      {icon}
    </span>
    <span style={{ fontSize: '14px', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>{label}</span>
  </Link>
);

const SideBar = () => {
  const { pathname } = useLocation();
  const { darkMode, toggleDarkMode, settings, updateSetting, user, adminAccess } = useApp();
  const [showSettings, setShowSettings] = useState(false);
  const settingsRef = useRef(null);

  const isActive = (p) =>
    pathname === p || (pathname === '/' && p === '/upload');

  useEffect(() => {
    const handler = (e) => {
      if (settingsRef.current && !settingsRef.current.contains(e.target)) setShowSettings(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <aside
      style={{
        width: `${SIDEBAR_W}px`,
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        paddingTop: '80px',
        paddingBottom: '16px',
        paddingLeft: '12px',
        paddingRight: '12px',
        gap: '4px',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 40,
        background: 'var(--color-surface-container-lowest, #fff)',
        borderRight: '1px solid var(--color-surface-variant, #e0e0e0)',
      }}
    >
      <style>{`
        @keyframes panelIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
      
      {NAV_ITEMS.map(({ path, label, icon }) => {
        const active = isActive(path);
        return (
          <Link
            key={path}
            to={path}
            title={label}
            style={{
              display: 'flex',
              flexDirection: 'row',
              alignItems: 'center',
              gap: '12px',
              padding: '11px 14px',
              borderRadius: '12px',
              textDecoration: 'none',
              transition: 'background 0.15s, color 0.15s',
              background: active
                ? 'var(--color-primary-container, #d0e4ff)'
                : 'transparent',
              color: active
                ? 'var(--color-primary, #2a6918)'
                : 'var(--color-secondary, #777)',
              fontWeight: active ? 700 : 500,
            }}
            onMouseEnter={e => {
              if (!active) e.currentTarget.style.background = 'var(--color-surface-container-low, #f5f5f5)';
            }}
            onMouseLeave={e => {
              if (!active) e.currentTarget.style.background = 'transparent';
            }}
          >
            <span
              className="material-symbols-outlined"
              style={{
                fontSize: '22px',
                flexShrink: 0,
                fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
              }}
            >
              {icon}
            </span>
            <span style={{ fontSize: '14px', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>
              {label}
            </span>
          </Link>
        );
      })}

      {/* ── Account (only when logged in) ──────────────────────────── */}
      {user && (
        <NavLinkStyled to="/account" label="Account" icon="account_circle" active={isActive('/account')} />
      )}

      {/* ── Admin tab: red, only for users with admin access ──────── */}
      {user && adminAccess && (
        <Link
          to="/admin"
          title="Admin"
          style={{
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: '12px',
            padding: '11px 14px',
            borderRadius: '12px',
            textDecoration: 'none',
            transition: 'background 0.15s, color 0.15s',
            background: isActive('/admin') ? '#ba1a1a' : 'transparent',
            color: isActive('/admin') ? '#ffffff' : '#ba1a1a',
            fontWeight: isActive('/admin') ? 700 : 600,
            border: isActive('/admin') ? 'none' : '1px solid rgba(186,26,26,0.4)',
          }}
          onMouseEnter={e => {
            if (!isActive('/admin')) {
              e.currentTarget.style.background = 'rgba(186,26,26,0.10)';
              e.currentTarget.style.color = '#ba1a1a';
            }
          }}
          onMouseLeave={e => {
            if (!isActive('/admin')) {
              e.currentTarget.style.background = 'transparent';
              e.currentTarget.style.color = '#ba1a1a';
            }
          }}
        >
          <span
            className="material-symbols-outlined"
            style={{ fontSize: '22px', flexShrink: 0, fontVariationSettings: isActive('/admin') ? "'FILL' 1" : "'FILL' 0" }}
          >
            admin_panel_settings
          </span>
          <span style={{ fontSize: '14px', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>Admin</span>
        </Link>
      )}

      <div style={{ flex: 1 }} /> {/* Spacer to push settings to the bottom */}

      {/* ── Settings button ───────────────────────────────────────────── */}
      <div ref={settingsRef} style={{ position: 'relative' }}>
        <button
          onClick={() => setShowSettings(!showSettings)}
          title="Settings"
          style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: '12px',
            padding: '11px 14px',
            borderRadius: '12px',
            textDecoration: 'none',
            border: 'none',
            background: showSettings ? 'var(--color-surface-container-low, #f5f5f5)' : 'transparent',
            color: 'var(--color-secondary, #777)',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'background 0.15s, color 0.15s',
            textAlign: 'left'
          }}
          onMouseEnter={e => {
            if (!showSettings) e.currentTarget.style.background = 'var(--color-surface-container-low, #f5f5f5)';
          }}
          onMouseLeave={e => {
            if (!showSettings) e.currentTarget.style.background = 'transparent';
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: '22px', flexShrink: 0 }}>settings</span>
          <span style={{ fontSize: '14px', letterSpacing: '0.01em', whiteSpace: 'nowrap' }}>Settings</span>
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
                Settings are saved locally.
              </p>
            </div>
          </Panel>
        )}
      </div>

    </aside>
  );
};

export default SideBar;
