import React, { useState, useEffect } from 'react';
import './AdminPage.css';

interface GuardRail {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

interface User {
  id: string;
  username: string;
  is_admin: boolean;
  created_at: string;
  last_login: string | null;
}

interface AdminPageProps {
  token: string;
}

const AdminPage: React.FC<AdminPageProps> = ({ token }) => {
  const [systemPrompt, setSystemPrompt] = useState('');
  const [temperature, setTemperature] = useState(0.5);
  const [maxTokens, setMaxTokens] = useState(2048);
  const [enableRag, setEnableRag] = useState(true);
  const [guardrails, setGuardrails] = useState<GuardRail[]>([]);
  const [awesomeGearEnabled, setAwesomeGearEnabled] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadSettings();
    loadGuardRails();
    loadAwesomeGearStatus();
    loadUsers();
  }, []);

  const loadSettings = async () => {
    try {
      // Load all settings at once
      const response = await fetch('/api/admin/settings', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSystemPrompt(data.system_prompt || '');
        setTemperature(parseFloat(data.temperature) || 0.5);
        setMaxTokens(parseInt(data.max_tokens) || 2048);
        setEnableRag(data.enable_rag === 'true');
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  };

  const loadGuardRails = async () => {
    try {
      const response = await fetch('/api/guardrails/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setGuardrails(data.guardrails || []);
      }
    } catch (error) {
      console.error('Failed to load guard rails:', error);
    }
  };

  const loadAwesomeGearStatus = async () => {
    try {
      const response = await fetch('/api/awesomegear/status');
      if (response.ok) {
        const data = await response.json();
        setAwesomeGearEnabled(data.enabled);
      }
    } catch (error) {
      console.error('Failed to load AwesomeGear status:', error);
    }
  };

  const toggleGuardRail = async (railId: string, currentlyEnabled: boolean) => {
    try {
      const response = await fetch(`/api/guardrails/${railId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enabled: !currentlyEnabled })
      });

      if (response.ok) {
        setGuardrails(prev =>
          prev.map(rail =>
            rail.id === railId ? { ...rail, enabled: !currentlyEnabled } : rail
          )
        );
        setMessage('✅ Guard rail updated');
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (error) {
      console.error('Failed to toggle guard rail:', error);
    }
  };

  const toggleAwesomeGear = async () => {
    try {
      const response = await fetch('/api/awesomegear/toggle', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ enabled: !awesomeGearEnabled })
      });

      if (response.ok) {
        setAwesomeGearEnabled(!awesomeGearEnabled);
        setMessage('✅ AwesomeGear updated');
        setTimeout(() => setMessage(''), 3000);
      }
    } catch (error) {
      console.error('Failed to toggle AwesomeGear:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await fetch('/api/admin/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setUsers(data || []);
      }
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const deleteUser = async (userId: string, username: string) => {
    if (!window.confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }

    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (response.ok) {
        setMessage(`✅ User ${username} deleted successfully`);
        setTimeout(() => setMessage(''), 3000);
        loadUsers(); // Reload users list
      } else {
        const error = await response.json();
        setMessage(`❌ ${error.detail || 'Failed to delete user'}`);
        setTimeout(() => setMessage(''), 5000);
      }
    } catch (error) {
      console.error('Failed to delete user:', error);
      setMessage('❌ Failed to delete user');
      setTimeout(() => setMessage(''), 5000);
    }
  };

  const handleSaveSystemPrompt = async () => {
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('/api/admin/system-prompt', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ system_prompt: systemPrompt })
      });

      if (response.ok) {
        setMessage('✅ System prompt updated successfully');
      } else {
        throw new Error('Failed to update');
      }
    } catch (error) {
      setMessage('❌ Failed to update system prompt');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAISettings = async () => {
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('/api/admin/ai-settings', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          temperature,
          max_tokens: maxTokens,
          enable_rag: enableRag
        })
      });

      if (response.ok) {
        setMessage('✅ AI settings updated successfully');
      } else {
        throw new Error('Failed to update');
      }
    } catch (error) {
      setMessage('❌ Failed to update AI settings');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-header">
        <h1>⚙️ Admin Panel</h1>
        <p>Configure system settings and AI behavior</p>
      </div>

      {message && (
        <div className={`admin-message ${message.includes('✅') ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      <div className="admin-section">
        <h2>System Prompt</h2>
        <p className="section-description">
          Define the AI's personality and behavior for all users
        </p>
        <textarea
          className="system-prompt-input"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          placeholder="You are a helpful AI assistant..."
          rows={6}
        />
        <button
          className="admin-button"
          onClick={handleSaveSystemPrompt}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save'}
        </button>
      </div>

      <div className="admin-section">
        <h2>AI Settings</h2>
        <p className="section-description">
          Configure AI model parameters
        </p>

        <div className="setting-group">
          <label>
            Temperature: {temperature}
            <span className="setting-hint">Controls creativity (0.0 = focused, 1.0 = creative)</span>
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
          />
        </div>

        <div className="setting-group">
          <label>
            Max Tokens: {maxTokens}
            <span className="setting-hint">Maximum response length</span>
          </label>
          <input
            type="range"
            min="512"
            max="4096"
            step="512"
            value={maxTokens}
            onChange={(e) => setMaxTokens(parseInt(e.target.value))}
          />
        </div>

        <div className="setting-group">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={enableRag}
              onChange={(e) => setEnableRag(e.target.checked)}
            />
            Enable RAG (Document Retrieval)
          </label>
        </div>

        <button
          className="admin-button"
          onClick={handleSaveAISettings}
          disabled={loading}
        >
          {loading ? 'Saving...' : 'Save'}
        </button>
      </div>

      <div className="admin-section">
        <h2>🛡️ Guard Rails</h2>
        <p className="section-description">
          Enable security techniques to protect against prompt injection and other attacks
        </p>
        
        {guardrails.length === 0 ? (
          <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Loading guard rails...</p>
        ) : (
          <div className="guardrails-list">
            {guardrails.map((rail) => (
              <div key={rail.id} className="guardrail-item">
                <div className="guardrail-info">
                  <div className="guardrail-name">{rail.name}</div>
                  <div className="guardrail-description">{rail.description}</div>
                </div>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={rail.enabled}
                    onChange={() => toggleGuardRail(rail.id, rail.enabled)}
                  />
                  <span className="slider"></span>
                </label>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="admin-section">
        <h2>🛍️ AwesomeGear</h2>
        <p className="section-description">
          Allow users to query product catalog using natural language
        </p>
        
        <div className="feature-toggle">
          <div>
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>Enable AwesomeGear</div>
            <div style={{ color: '#6b7280', fontSize: '14px' }}>
              When enabled, users can ask about merchandise like "show me t-shirts" or "what mugs do you have?"
            </div>
          </div>
          <label className="switch">
            <input
              type="checkbox"
              checked={awesomeGearEnabled}
              onChange={toggleAwesomeGear}
            />
            <span className="slider"></span>
          </label>
        </div>
      </div>

      <div className="admin-section">
        <h2>👥 User Management</h2>
        <p className="section-description">
          Manage user accounts and permissions
        </p>
        
        {users.length === 0 ? (
          <p style={{ color: '#6b7280', fontStyle: 'italic' }}>Loading users...</p>
        ) : (
          <div className="users-list">
            <table className="users-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Created</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td className="username-cell">{user.username}</td>
                    <td>
                      <span className={user.is_admin ? 'badge-admin' : 'badge-user'}>
                        {user.is_admin ? '👑 Admin' : '👤 User'}
                      </span>
                    </td>
                    <td className="date-cell">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="date-cell">
                      {user.last_login 
                        ? new Date(user.last_login).toLocaleDateString()
                        : 'Never'}
                    </td>
                    <td>
                      <button
                        className="delete-button"
                        onClick={() => deleteUser(user.id, user.username)}
                        title={`Delete ${user.username}`}
                      >
                        🗑️ Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPage;

