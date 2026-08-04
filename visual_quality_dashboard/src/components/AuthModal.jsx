import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { ApiError } from '../api';
import PasswordField from './PasswordField';

/*
 * AuthModal — full-screen, centered sign-in / register modal.
 * Rendered once at the app root (see App.jsx). Opened via openAuth() from
 * anywhere (TopNavBar "Sign in", or a route guard blocking protected content).
 * It overlays whatever is behind it; the page stays mounted underneath.
 */
const AuthModal = () => {
  const { authModal, closeAuth, signIn, signUp, addNotification } = useApp();
  const { open, mode } = authModal;

  const [isLogin, setIsLogin] = useState(mode === 'login');
  const [name, setName]         = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm]    = useState('');
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState('');

  // Reset transient state each time the modal opens; sync toggle to requested mode.
  useEffect(() => {
    if (open) {
      setIsLogin(mode !== 'register');
      setError('');
      setLoading(false);
    }
  }, [open, mode]);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => { if (e.key === 'Escape') closeAuth(); };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [open, closeAuth]);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (!isLogin) {
      if (password.length < 6) { setError('Password must be at least 6 characters.'); return; }
      if (password !== confirm) { setError('Passwords do not match.'); return; }
    }
    setLoading(true);
    try {
      if (isLogin) {
        const data = await signIn(email, password);
        addNotification('success', `Welcome back, ${data.user.name}!`);
      } else {
        const data = await signUp(email, name, password);
        addNotification('success',
          data.admin_access ? 'Account created — admin access granted.' : 'Account created successfully.');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong.');
    } finally {
      setLoading(false);
    }
  };

  return (
    // Full-screen dimmed backdrop, content centered.
    <div
      onClick={closeAuth}
      style={{
        position: 'fixed', inset: 0, zIndex: 999,
        background: 'rgba(15, 22, 18, 0.55)',
        backdropFilter: 'blur(4px)',
        WebkitBackdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: '24px',
      }}
    >
      {/* Centered card */}
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%', maxWidth: '420px',
          maxHeight: '90vh',
          background: 'var(--color-surface-container-lowest, #fff)',
          borderRadius: '20px',
          boxShadow: '0 24px 64px rgba(0,0,0,0.35)',
          display: 'flex', flexDirection: 'column',
          padding: '32px',
          position: 'relative',
          overflowY: 'auto',
        }}
      >
        <button
          onClick={closeAuth}
          title="Close"
          style={{
            position: 'absolute', top: '16px', right: '16px',
            border: 'none', background: 'transparent', cursor: 'pointer',
            color: 'var(--color-secondary, #777)', padding: '4px', borderRadius: '8px',
          }}
        >
          <span className="material-symbols-outlined">close</span>
        </button>

        <div className="flex flex-col justify-center flex-1">
          <div className="flex flex-col items-center text-center mb-md">
            <img
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuA5Oy1uZrGc-3lrWxiE00vAqLq0ioa1XoTpI_93qwdgFYxIhu5Z46MqAezeZIy7B6MmiomQQZ03BojhqprfCRp9U36M4UAvt_PVxbRY9_vLwaak7cDRMpJDkhrkCwmpN807UXFehfWZYi925fF0gfo_9JgP3CsyfhfFy3WYScGHrKiBJreEqaUlwbfBo0ClGS3z7v5iNI4UGKO6NFyO6w5152kRLwv8UUD9f9JL5jGoSIREPZZg4Bw8zujVKWCML188ODlW6I2XIfIj"
              alt="Optylab Logo"
              style={{ height: '36px', width: 'auto', marginBottom: '12px' }}
            />
            <h1 className="font-display-lg text-display-lg text-on-background">
              {isLogin ? 'Sign in' : 'Create account'}
            </h1>
            <p className="font-body-md text-body-md text-on-surface-variant mt-xs">
              {isLogin ? 'Access your OptyLab dashboard.' : 'Register to use OptyLab.'}
            </p>
          </div>

          {error && (
            <div className="bg-error-container text-on-error-container rounded-lg px-md py-sm mb-md text-body-sm">
              {error}
            </div>
          )}

          <form onSubmit={submit} className="flex flex-col gap-md">
            {!isLogin && (
              <input
                type="text" required value={name} onChange={e => setName(e.target.value)}
                placeholder="Your name"
                className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
              />
            )}
            <input
              type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
            />
            <PasswordField
              id="auth-password"
              required value={password} onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
            />
            {!isLogin && (
              <PasswordField
                id="auth-confirm"
                required value={confirm} onChange={e => setConfirm(e.target.value)}
                placeholder="Confirm password"
                autoComplete="new-password"
                className="w-full px-md py-sm rounded border border-outline-variant bg-surface-container-lowest text-body-md focus:border-primary outline-none"
              />
            )}
            <button
              type="submit" disabled={loading}
              className="px-md py-sm rounded bg-primary text-on-primary font-label-md hover:opacity-90 transition-opacity flex items-center justify-center gap-xs cursor-pointer disabled:opacity-60"
            >
              {loading ? 'Please wait…' : (isLogin ? 'Sign in' : 'Create account')}
            </button>
          </form>

          <p className="font-body-sm text-body-sm text-secondary mt-lg text-center">
            {isLogin ? "Don't have an account? " : 'Already have an account? '}
            <button
              type="button"
              onClick={() => { setIsLogin(v => !v); setError(''); }}
              className="text-primary font-semibold hover:underline bg-transparent border-none cursor-pointer"
            >
              {isLogin ? 'Create one' : 'Sign in'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
};

export default AuthModal;
