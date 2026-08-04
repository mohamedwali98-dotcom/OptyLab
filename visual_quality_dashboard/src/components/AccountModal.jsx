import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { api, ApiError } from '../api';
import { BACKEND_URL } from '../backend';
import PasswordField from './PasswordField';

/*
 * AccountModal — the account "manager" the user asked for. It is a WINDOW
 * (centered modal), not a page tab. The top-nav account button opens a hub with
 * two choices:
 *   1) Change password  → a focused window with the password form
 *   2) Recent activity  → a window listing recent logins + a Log out action
 * The hub, and each sub-window, share the same dimmed-backdrop / centered-card
 * styling as AuthModal so the whole app reads as one design system.
 */

const MODAL_BG = 'rgba(15, 22, 18, 0.55)';
const CARD = 'var(--color-surface-container-lowest, #fff)';

const Backdrop = ({ onClose, children, cardStyle }) => (
  <div
    onClick={onClose}
    style={{
      position: 'fixed', inset: 0, zIndex: 998,
      background: MODAL_BG,
      backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px',
      animation: 'acctBackdrop 160ms ease',
    }}
  >
    <div
      onClick={(e) => e.stopPropagation()}
      style={{
        width: '100%', maxWidth: '440px', maxHeight: '90vh',
        background: CARD, borderRadius: '20px',
        boxShadow: '0 24px 64px rgba(0,0,0,0.35)',
        display: 'flex', flexDirection: 'column',
        padding: '28px', position: 'relative', overflowY: 'auto',
        animation: 'acctCard 200ms cubic-bezier(0.2, 0.8, 0.2, 1)',
        ...cardStyle,
      }}
    >
      {children}
    </div>
  </div>
);

const CloseBtn = ({ onClick }) => (
  <button
    onClick={onClick} title="Close"
    style={{
      position: 'absolute', top: '16px', right: '16px',
      border: 'none', background: 'transparent', cursor: 'pointer',
      color: 'var(--color-secondary, #777)', padding: '4px', borderRadius: '8px',
    }}
  >
    <span className="material-symbols-outlined">close</span>
  </button>
);

const ChoiceItem = ({ icon, title, subtitle, onClick }) => (
  <button
    onClick={onClick}
    style={{
      width: '100%', textAlign: 'left', cursor: 'pointer',
      display: 'flex', alignItems: 'center', gap: '14px',
      padding: '16px', borderRadius: '14px',
      border: '1px solid var(--color-surface-variant, #e0e3e5)',
      background: 'var(--color-surface-container-lowest, #fff)',
      transition: 'background 0.15s, border-color 0.15s',
    }}
    onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-container-low, #f5f5f5)'; }}
    onMouseLeave={e => { e.currentTarget.style.background = 'var(--color-surface-container-lowest, #fff)'; }}
  >
    <span
      className="material-symbols-outlined"
      style={{ fontSize: '26px', color: 'var(--color-primary, #2a6918)', flexShrink: 0 }}
    >{icon}</span>
    <span style={{ flex: 1 }}>
      <span style={{ display: 'block', fontSize: '15px', fontWeight: 600, color: 'var(--color-on-surface, #191c1e)' }}>{title}</span>
      <span style={{ display: 'block', fontSize: '12px', color: 'var(--color-secondary, #777)' }}>{subtitle}</span>
    </span>
    <span className="material-symbols-outlined" style={{ fontSize: '20px', color: 'var(--color-secondary, #777)' }}>chevron_right</span>
  </button>
);

/* ── Change password sub-window ─────────────────────────────────────────── */
const ChangePasswordWindow = ({ onClose }) => {
  const { addNotification } = useApp();
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setError(''); setOk('');
    if (newPw.length < 6) { setError('New password must be at least 6 characters.'); return; }
    if (newPw !== confirmPw) { setError('New passwords do not match.'); return; }
    setLoading(true);
    try {
      await api.changePassword(oldPw, newPw);
      setOk('Password changed successfully.');
      setOldPw(''); setNewPw(''); setConfirmPw('');
      addNotification('success', 'Password updated.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <CloseBtn onClick={onClose} />
      <h2 className="font-headline-md text-headline-md text-on-surface mb-xs flex items-center gap-sm">
        <span className="material-symbols-outlined text-primary">lock_reset</span>
        Change password
      </h2>
      <p className="font-body-sm text-body-sm text-secondary mb-md">Update the password for your OptyLab account.</p>

      {error && (
        <div className="bg-error-container text-on-error-container rounded-lg px-md py-sm mb-md text-body-sm">{error}</div>
      )}
      {ok && (
        <div className="bg-primary-container text-on-primary-container rounded-lg px-md py-sm mb-md text-body-sm">{ok}</div>
      )}

      <form onSubmit={submit} className="flex flex-col gap-md">
        <label className="flex flex-col gap-xs">
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Current password</span>
          <PasswordField id="ac-old" required value={oldPw} onChange={e => setOldPw(e.target.value)}
            placeholder="Current password" autoComplete="current-password"
            className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none" />
        </label>
        <label className="flex flex-col gap-xs">
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">New password</span>
          <PasswordField id="ac-new" required value={newPw} onChange={e => setNewPw(e.target.value)}
            placeholder="New password" autoComplete="new-password"
            className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none" />
        </label>
        <label className="flex flex-col gap-xs">
          <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Confirm new password</span>
          <PasswordField id="ac-conf" required value={confirmPw} onChange={e => setConfirmPw(e.target.value)}
            placeholder="Confirm new password" autoComplete="new-password"
            className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none" />
        </label>
        <button type="submit" disabled={loading}
          className="px-md py-sm rounded bg-primary text-on-primary font-label-md hover:opacity-90 transition-opacity flex items-center justify-center gap-xs cursor-pointer disabled:opacity-60">
          {loading ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </div>
  );
};

/* ── Recent activity (logins) sub-window ────────────────────────────────── */
const RecentActivityWindow = ({ onClose }) => {
  const { user, signOut } = useApp();
  const [logins, setLogins] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.history();
      setLogins(data.history || []);
    } catch {
      setLogins([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const fmt = (ts) => {
    try { return new Date(ts).toLocaleString(); } catch { return ts; }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <CloseBtn onClick={onClose} />
      <h2 className="font-headline-md text-headline-md text-on-surface mb-xs flex items-center gap-sm">
        <span className="material-symbols-outlined text-primary">history</span>
        Recent activity
      </h2>
      <p className="font-body-sm text-body-sm text-secondary mb-md">
        Signed in as <span className="font-semibold">{user?.email}</span>
      </p>

      <div className="bg-surface-container-lowest rounded-lg border border-surface-variant">
        <div className="px-md py-sm font-label-md text-label-md text-secondary uppercase tracking-wider border-b border-surface-variant">
          Recent logins
        </div>
        {loading ? (
          <div className="text-center py-xl text-secondary">
            <span className="material-symbols-outlined text-[28px] block mb-2 animate-spin">progress_activity</span>
            Loading…
          </div>
        ) : logins.length === 0 ? (
          <p className="text-secondary text-body-sm py-md px-md">No recent sign-in activity.</p>
        ) : (
          <ul className="divide-y divide-surface-variant max-h-[320px] overflow-y-auto">
            {logins.map((l, i) => (
              <li key={i} className="flex items-center gap-md px-md py-sm">
                <span
                  className="material-symbols-outlined flex-shrink-0"
                  style={{
                    fontSize: '20px',
                    color: l.action === 'logout' ? 'var(--color-error, #ba1a1a)'
                         : l.action === 'change-password' ? 'var(--color-primary, #2a6918)'
                         : 'var(--color-on-surface, #191c1e)',
                  }}
                >
                  {l.action === 'logout' ? 'logout'
                   : l.action === 'change-password' ? 'lock_reset'
                   : l.action === 'register' ? 'person_add' : 'login'}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="font-label-md text-label-md capitalize text-on-surface">
                    {l.action === 'logout' ? 'Signed out'
                     : l.action === 'change-password' ? 'Password changed'
                     : l.action === 'register' ? 'Registered'
                     : 'Signed in'}
                  </div>
                  <div className="font-body-sm text-body-sm text-secondary truncate">
                    {fmt(l.ts)}{l.ip ? ` · ${l.ip}` : ''}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <button
        onClick={() => { signOut(); onClose(); }}
        className="mt-md px-md py-sm rounded font-label-md flex items-center justify-center gap-xs cursor-pointer"
        style={{
          border: '1px solid var(--color-error, #ba1a1a)',
          color: 'var(--color-error, #ba1a1a)',
          background: 'transparent',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-error-container, #ffdad6)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
      >
        <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>logout</span>
        Log out
      </button>
    </div>
  );
};

/* ── Hub (entry) window ─────────────────────────────────────────────────── */
const HubWindow = ({ onClose, onChoose }) => {
  const { user } = useApp();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <CloseBtn onClick={onClose} />
      <div className="flex items-center gap-md">
        <div
          style={{
            width: '46px', height: '46px', borderRadius: '50%', flexShrink: 0,
            background: 'var(--color-primary-container, #d0e4ff)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
        >
          <span className="material-symbols-outlined" style={{ fontSize: '24px', color: 'var(--color-primary, #2a6918)' }}>
            {user?.picture ? '' : 'person'}
          </span>
        </div>
        <div style={{ minWidth: 0 }}>
          <div className="font-headline-sm text-headline-sm text-on-surface truncate">{user?.name}</div>
          <div className="font-body-sm text-body-sm text-secondary truncate">{user?.email}</div>
        </div>
      </div>

      <div className="flex flex-col gap-sm">
        <ChoiceItem
          icon="lock_reset"
          title="Change password"
          subtitle="Update the password for your account"
          onClick={() => onChoose('password')}
        />
        <ChoiceItem
          icon="history"
          title="Recent activity & log out"
          subtitle="See recent sign-ins and sign out"
          onClick={() => onChoose('activity')}
        />
      </div>
    </div>
  );
};

const AccountModal = () => {
  const { accountOpen, closeAccount, user } = useApp();
  const [view, setView] = useState('hub'); // 'hub' | 'password' | 'activity'

  // Reset to the hub each time the modal opens; close on Escape.
  useEffect(() => {
    if (accountOpen) setView('hub');
  }, [accountOpen]);

  useEffect(() => {
    if (!accountOpen) return;
    const onKey = (e) => { if (e.key === 'Escape') closeAccount(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [accountOpen, closeAccount]);

  if (!accountOpen || !user) return null;

  const card =
    view === 'hub'
      ? <HubWindow onClose={closeAccount} onChoose={setView} />
      : view === 'password'
        ? <ChangePasswordWindow onClose={closeAccount} />
        : <RecentActivityWindow onClose={closeAccount} />;

  return (
    <>
      <style>{`
        @keyframes acctBackdrop { from { opacity: 0; } to { opacity: 1; } }
        @keyframes acctCard { from { opacity: 0; transform: translateY(12px) scale(0.98); } to { opacity: 1; transform: none; } }
      `}</style>
      <Backdrop onClose={closeAccount}>{card}</Backdrop>
    </>
  );
};

export default AccountModal;
