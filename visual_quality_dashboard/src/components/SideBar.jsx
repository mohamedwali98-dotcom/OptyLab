import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export const SIDEBAR_W = 200; // px — exported so App.jsx can import it

const NAV_ITEMS = [
  { path: '/upload',  label: 'Upload',  icon: 'cloud_upload'        },
  { path: '/results', label: 'Results', icon: 'analytics'           },
  { path: '/admin',   label: 'Admin',   icon: 'admin_panel_settings' },
];

const SideBar = () => {
  const { pathname } = useLocation();

  const isActive = (p) =>
    pathname === p || (pathname === '/' && p === '/upload');

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
    </aside>
  );
};

export default SideBar;
