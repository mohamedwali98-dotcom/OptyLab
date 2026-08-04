import React, { useState, useEffect, useCallback } from 'react';
import { useApp } from '../context/AppContext';
import { api, ApiError } from '../api';

const AccessControl = () => {
  const { user, addNotification } = useApp();

  const [emails, setEmails]     = useState([]);
  const [newEmail, setNewEmail] = useState('');
  const [loading, setLoading]   = useState(true);
  const [busy, setBusy]         = useState(false);
  const [error, setError]       = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.adminAccessList();
      setEmails(data.emails || []);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Failed to load access list.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const add = async (e) => {
    e.preventDefault();
    setError(''); setBusy(true);
    const email = newEmail.trim().toLowerCase();
    try {
      await api.grantAccess(email);
      addNotification('success', `${email} can now access the Admin tab.`);
      setNewEmail('');
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to add email.');
    } finally {
      setBusy(false);
    }
  };

  const remove = async (email) => {
    setError('');
    try {
      await api.revokeAccess(email);
      addNotification('info', `${email} removed from admin access.`);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to remove email.');
    }
  };

  const isSelf = (email) => email.toLowerCase() === user?.email?.toLowerCase();

  return (
    <main className="flex-grow p-gutter md:p-margin max-w-7xl mx-auto w-full flex flex-col gap-margin">
      <header className="flex flex-col md:flex-row justify-between items-start md:items-end gap-md">
        <div>
          <h1 className="font-display-lg text-display-lg text-on-background mb-xs">Admin access</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Emails on this list can see and use the red Admin tab. Add or remove access below.
          </p>
        </div>
      </header>

      {error && (
        <div className="bg-error-container text-on-error-container rounded-lg px-md py-sm text-body-sm">{error}</div>
      )}

      {/* Add email */}
      <section className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant">
        <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
          <span className="material-symbols-outlined text-primary">person_add</span>
          Grant access
        </h2>
        <form onSubmit={add} className="flex flex-col sm:flex-row gap-sm items-end">
          <label className="flex-1 flex flex-col gap-xs">
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Email address</span>
            <input
              type="email" required value={newEmail} onChange={e => setNewEmail(e.target.value)}
              placeholder="someone@company.com"
              className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
            />
          </label>
          <button type="submit" disabled={busy}
            className="px-md py-sm rounded bg-primary text-on-primary font-label-md hover:opacity-90 transition-opacity flex items-center justify-center gap-xs cursor-pointer disabled:opacity-60">
            {busy ? 'Adding…' : 'Add email'}
          </button>
        </form>
      </section>

      {/* List */}
      <section className="bg-surface-container-lowest p-md rounded-lg border border-surface-variant">
        <h2 className="font-headline-sm text-headline-sm text-on-surface mb-md flex items-center gap-sm">
          <span className="material-symbols-outlined text-primary">list</span>
          Emails with admin access
        </h2>

        {loading ? (
          <div className="text-center py-xl text-secondary">
            <span className="material-symbols-outlined text-[32px] block mb-2 animate-spin">progress_activity</span>
            Loading…
          </div>
        ) : emails.length === 0 ? (
          <p className="text-secondary text-body-sm py-md">No emails added yet.</p>
        ) : (
          <ul className="divide-y divide-surface-variant">
            {emails.map((row) => (
              <li key={row.email} className="flex items-center gap-sm py-sm">
                <span className="material-symbols-outlined text-secondary">mail</span>
                <div className="flex-1 min-w-0">
                  <div className="font-label-md text-label-md text-on-surface">
                    {row.email}
                    {isSelf(row.email) && (
                      <span className="ml-2 text-[10px] font-semibold bg-primary-container text-on-primary-container px-2 py-0.5 rounded-full align-middle">you</span>
                    )}
                  </div>
                  <div className="font-body-sm text-body-sm text-secondary">
                    Granted by {row.granted_by} · {new Date(row.granted_at).toLocaleString()}
                  </div>
                </div>
                <button
                  onClick={() => remove(row.email)}
                  title="Remove access"
                  className="flex items-center gap-xs px-sm py-xs border border-error text-error hover:bg-error-container rounded font-label-sm text-[12px] cursor-pointer transition-colors"
                >
                  <span className="material-symbols-outlined text-[14px]">delete</span>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
};

export default AccessControl;
