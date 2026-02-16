import React, { useState } from 'react';
import './AuthPage.css';

interface LoginPageProps {
  onLogin: (token: string, username: string, isAdmin: boolean) => void;
  onSwitchToSignup: () => void;
}

const LoginPage: React.FC<LoginPageProps> = ({ onLogin, onSwitchToSignup }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Invalid credentials');
      }

      const data = await response.json();
      onLogin(data.access_token, data.username, data.is_admin);
    } catch (err: any) {
      setError(err.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-container">
        <div className="auth-header">
          <div className="auth-logo-container">
            <img src="/awesomebot-logo.svg" alt="AwesomeBot" className="auth-logo" />
            <h1>AwesomeBot</h1>
          </div>
          <p>AI Chat Platform</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Login</h2>

          {error && <div className="error-message">{error}</div>}

          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
            />
          </div>

          <button type="submit" className="submit-button" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </button>

          <div className="auth-switch">
            Don't have an account?{' '}
            <button type="button" onClick={onSwitchToSignup} className="link-button">
              Sign up
            </button>
          </div>

          <div className="demo-credentials">
            <p>Demo Admin Account:</p>
            <code>Username: admin</code>
            <code>Password: Password1</code>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;


