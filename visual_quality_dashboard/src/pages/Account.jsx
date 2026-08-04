import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { api, ApiError } from '../api';
import PasswordField from '../components/PasswordField';

const Account = () => {
  const { user, addNotification } = useApp();

  // ── Change password ────────────────────────────────────────────────
  const [oldPw, setOldPw]       = useState('');
  const [newPw, setNewPw]       = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [pwLoading, setPwLoading] = useState(false);
  const [pwError, setPwError]     = useState('');
  const [pwOk, setPwOk]           = useState('');

  // ── History (last 20) ─────────────────────────────────────────────
  const [history, setHistory] = useState([]);
  const [histLoading, setHistLoading] = useState(true);

  const loadHistory = useCallback(async () => {
    setHistLoading(true);
    try {
      const data = await api.history();
      setHistory(data.history || []);
    } catch (e) {
      setHistory([]);
    } finally {
      setHistLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const submitPw = async (e) => {
    e.preventDefault();
    setPwError(''); setPwOk('');
    if (newPw.length < 6) { setPwError('New password must be at least 6 characters.'); return; }
    if (newPw !== confirmPw) { setPwError('New passwords do not match.'); return; }
    setPwLoading(true);
    try {
      await api.changePassword(oldPw, newPw);
      setPwOk('Password changed successfully.');
      setOldPw(''); setNewPw(''); setConfirmPw('');
      addNotification('success', 'Password updated.');
      loadHistory();
    } catch (err) {
      setPwError(err instanceof ApiError ? err.message : 'Could not change password.');
    } finally {
      setPwLoading(false);
    }
  };

  return (
    <main className="flex-grow p-gutter md:p-margin max-w-7xl mx-auto w-full flex flex-col gap-margin">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-md">
        <div>
          <h1 className="font-display-lg text-display-lg text-on-background mb-xs">My Account</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Signed in as <span className="font-semibold">{user?.email}</span>
          </p>
        </div>
      </header>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-md">
        {/* Change password */}
        <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
            <span className="material-symbols-outlined text-primary">lock_reset</span>
            Change password
          </h2>

          {pwError && (
            <div className="bg-error-container text-on-error-container rounded-lg px-md py-sm mb-md text-body-sm">{pwError}</div>
          )}
          {pwOk && (
            <div className="bg-primary-container text-on-primary-container rounded-lg px-md py-sm mb-md text-body-sm">{pwOk}</div>
          )}

          <form onSubmit={submitPw} className="flex flex-col gap-md">
            <label className="flex flex-col gap-xs">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Current password</span>
              <PasswordField
                id="old-pw" required value={oldPw} onChange={e => setOldPw(e.target.value)}
                placeholder="Current password" autoComplete="current-password"
                className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
              />
            </label>
            <label className="flex flex-col gap-xs">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">New password</span>
              <PasswordField
                id="new-pw" required value={newPw} onChange={e => setNewPw(e.target.value)}
                placeholder="New password" autoComplete="new-password"
                className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
              />
            </label>
            <label className="flex flex-col gap-xs">
              <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Confirm new password</span>
              <PasswordField
                id="confirm-pw" required value={confirmPw} onChange={e => setConfirmPw(e.target.value)}
                placeholder="Confirm new password" autoComplete="new-password"
                className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
              />
            </label>
            <button type="submit" disabled={pwLoading}
              className="px-md py-sm rounded bg-primary text-on-primary font-label-md hover:opacity-90 transition-opacity flex items-center justify-center gap-xs cursor-pointer disabled:opacity-60">
              {pwLoading ? 'Updating…' : 'Update password'}
            </button>
          </form>
        </div>

        {/* Last 20 history */}
        <div className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant">
          <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
            <span className="material-symbols-outlined text-primary">history</span>
            Recent activity (last 20)
          </h2>

          {histLoading ? (
            <div className="text-center py-xl text-secondary">
              <span className="material-symbols-outlined text-[32px] block mb-2 animate-spin">progress_activity</span>
              Loading…
            </div>
          ) : history.length === 0 ? (
            <p className="text-secondary text-body-sm py-md">No activity recorded yet.</p>
          ) : (
            <ul className="divide-y divide-surface-variant max-h-[420px] overflow-y-auto">
              {history.map((h, i) => (
                <li key={i} className="flex items-center gap-md py-sm">
                  <span className="material-symbols-outlined text-secondary">
                    {h.action === 'login' ? 'login' : h.action === 'register' ? 'person_add' : h.action === 'change-password' ? 'lock_reset' : 'circle'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-label-md text-label-md text-on-surface capitalize">{h.action.replace('-', ' ')}</div>
                    <div className="font-body-sm text-body-sm text-secondary">{new Date(h.ts).toLocaleString()}</div>
                  </div>
                  {h.ip && (
                    <span className="font-body-sm text-body-sm text-secondary">{h.ip}</span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </main>
  );
};

export default Account;
