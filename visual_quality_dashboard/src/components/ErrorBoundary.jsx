import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Unhandled Application Error:', error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleResetSession = () => {
    try {
      localStorage.removeItem('optylab-token');
    } catch (e) { /* ignore */ }
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--color-surface, #f8f9fa)',
            color: 'var(--color-on-surface, #191c1e)',
            padding: '24px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          <div
            style={{
              maxWidth: '460px',
              width: '100%',
              background: 'var(--color-surface-container-lowest, #ffffff)',
              borderRadius: '20px',
              padding: '36px',
              boxShadow: '0 16px 48px rgba(0,0,0,0.12)',
              textAlign: 'center',
              border: '1px solid var(--color-surface-variant, #e0e3e5)',
            }}
          >
            <div
              style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'var(--color-error-container, #ffdad6)',
                color: 'var(--color-error, #ba1a1a)',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: '20px',
              }}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '36px' }}>
                warning
              </span>
            </div>

            <h1 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '8px' }}>
              Something went wrong
            </h1>
            <p style={{ fontSize: '14px', color: 'var(--color-secondary, #666)', marginBottom: '24px', lineHeight: 1.5 }}>
              The application encountered an unexpected error. Don't worry, your data is safe.
            </p>

            {this.state.error && (
              <div
                style={{
                  background: 'var(--color-surface-container-low, #f5f5f5)',
                  padding: '12px',
                  borderRadius: '10px',
                  fontSize: '12px',
                  fontFamily: 'monospace',
                  color: 'var(--color-error, #ba1a1a)',
                  marginBottom: '24px',
                  wordBreak: 'break-word',
                  textAlign: 'left',
                  maxHeight: '100px',
                  overflowY: 'auto',
                }}
              >
                {this.state.error.message || String(this.state.error)}
              </div>
            )}

            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={this.handleReload}
                style={{
                  padding: '10px 20px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'var(--color-primary, #2a6918)',
                  color: '#ffffff',
                  fontWeight: 600,
                  fontSize: '14px',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(42, 105, 24, 0.25)',
                }}
              >
                Reload Page
              </button>
              <button
                onClick={this.handleResetSession}
                style={{
                  padding: '10px 20px',
                  borderRadius: '10px',
                  border: '1px solid var(--color-outline-variant, #ccc)',
                  background: 'transparent',
                  color: 'var(--color-on-surface, #191c1e)',
                  fontWeight: 600,
                  fontSize: '14px',
                  cursor: 'pointer',
                }}
              >
                Sign In Again
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
