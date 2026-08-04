import React, { useState } from 'react';

/*
 * PasswordField — a password <input> with a show/hide toggle button.
 * Lets the user reveal what they typed so they can see and correct typos
 * (e.g. delete a wrongly-typed character). Controlled: pass value + onChange
 * exactly like a normal <input>.
 */
const PasswordField = ({
  id,
  value,
  onChange,
  placeholder,
  required = false,
  autoComplete,
  className = '',
}) => {
  const [show, setShow] = useState(false);

  return (
    <div style={{ position: 'relative' }}>
      <input
        id={id}
        type={show ? 'text' : 'password'}
        required={required}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        autoComplete={autoComplete}
        className={className}
        style={{ paddingRight: '44px' }}
      />
      <button
        type="button"
        onClick={() => setShow(v => !v)}
        title={show ? 'Hide password' : 'Show password'}
        aria-label={show ? 'Hide password' : 'Show password'}
        tabIndex={-1}
        style={{
          position: 'absolute',
          top: '50%',
          right: '10px',
          transform: 'translateY(-50%)',
          border: 'none',
          background: 'transparent',
          cursor: 'pointer',
          color: 'var(--color-secondary, #777)',
          padding: '4px',
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
        }}
      >
        <span className="material-symbols-outlined">
          {show ? 'visibility_off' : 'visibility'}
        </span>
      </button>
    </div>
  );
};

export default PasswordField;
