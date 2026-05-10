import { useState } from 'react';

function LoginModal({ login, register, closeLogin }) {
  const [mode, setMode] = useState('signin');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const demoAccounts = [
    {
      label: 'Admin',
      email: 'admin@asystqa.com',
      password: 'admin123',
    },
    {
      label: 'Developer',
      email: 'dev@asystqa.com',
      password: 'dev123',
    },
  ];

  function handleSubmit(event) {
    event.preventDefault();

    if (mode === 'signup') {
      register(email, password, name);
      return;
    }

    login(email, password);
  }

  function fillDemoAccount(account) {
    setEmail(account.email);
    setPassword(account.password);
  }

  return (
    <div className="loginOverlay">
      <form className="loginModal" onSubmit={handleSubmit}>
        <button type="button" className="closeLoginBtn" onClick={closeLogin}>
          ×
        </button>

        <img src="/logo.png" alt="AsystQA Logo" />

        <h2>{mode === 'signin' ? 'Sign in to AsystQA' : 'Create your AsystQA account'}</h2>
        <p>
          {mode === 'signin'
            ? 'Try a demo account or sign up for quick access.'
            : 'Register with your email and start using the command center.'}
        </p>

        {mode === 'signup' && (
          <label>
            Name
            <input
              type="text"
              value={name}
              placeholder="Your name"
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            value={email}
            placeholder="you@example.com"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            placeholder="Enter your password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button type="submit" className="loginSubmitBtn">
          {mode === 'signin' ? 'Sign In →' : 'Sign Up →'}
        </button>

        <div className="authToggle">
          {mode === 'signin' ? (
            <p>
              Don’t have an account?{' '}
              <button type="button" onClick={() => setMode('signup')}>
                Sign up
              </button>
            </p>
          ) : (
            <p>
              Already have an account?{' '}
              <button type="button" onClick={() => setMode('signin')}>
                Sign in
              </button>
            </p>
          )}
        </div>

        {mode === 'signin' && (
          <div className="demoAccounts">
            <strong>Demo accounts</strong>
            <p>Select one to autofill credentials.</p>
            {demoAccounts.map((account) => (
              <button
                type="button"
                key={account.label}
                onClick={() => fillDemoAccount(account)}
              >
                {account.label}: {account.email}
              </button>
            ))}
          </div>
        )}
      </form>
    </div>
  );
}

export default LoginModal;
