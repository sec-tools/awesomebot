import React, { useState, useEffect } from 'react';
import './InfoPage.css';

interface InfoPageProps {
  token: string;
  isAdmin: boolean;
}

const InfoPage: React.FC<InfoPageProps> = ({ token, isAdmin }) => {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPlatformInfo();
  }, []);

  const loadPlatformInfo = async () => {
    try {
      const response = await fetch('/api/admin/settings/public', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setSettings(data);
      }
    } catch (error) {
      console.error('Failed to load platform info:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="info-page">
      <div className="info-header">
        <h1>ℹ️ Platform Information</h1>
        <p>Current system configuration and settings</p>
      </div>

      {loading ? (
        <div className="info-loading">Loading platform information...</div>
      ) : (
        <>
          <div className="info-section">
            <h2>🤖 AI Model</h2>
            <div className="info-grid">
              <div className="info-item">
                <div className="info-label">Model Name</div>
                <div className="info-value">Ollama (qwen2.5-coder:7b)</div>
              </div>
              <div className="info-item">
                <div className="info-label">Provider</div>
                <div className="info-value">Ollama</div>
              </div>
              <div className="info-item">
                <div className="info-label">Temperature</div>
                <div className="info-value">{settings?.temperature || 'Loading...'}</div>
              </div>
              <div className="info-item">
                <div className="info-label">Max Tokens</div>
                <div className="info-value">{settings?.max_tokens || 'Loading...'}</div>
              </div>
            </div>
          </div>

          <div className="info-section">
            <h2>⚙️ System Features</h2>
            <div className="info-grid">
              <div className="info-item">
                <div className="info-label">RAG (Document Retrieval)</div>
                <div className="info-value">
                  <span className={`status-badge ${settings?.enable_rag === 'true' ? 'enabled' : 'disabled'}`}>
                    {settings?.enable_rag === 'true' ? '✓ Enabled' : '✗ Disabled'}
                  </span>
                </div>
              </div>
              <div className="info-item">
                <div className="info-label">AwesomeGear Catalog</div>
                <div className="info-value">
                  <span className={`status-badge ${settings?.awesome_gear_enabled === 'true' ? 'enabled' : 'disabled'}`}>
                    {settings?.awesome_gear_enabled === 'true' ? '✓ Enabled' : '✗ Disabled'}
                  </span>
                </div>
              </div>
              <div className="info-item">
                <div className="info-label">Conversation History</div>
                <div className="info-value">
                  <span className="status-badge enabled">✓ Enabled</span>
                </div>
              </div>
              <div className="info-item">
                <div className="info-label">Multi-User Support</div>
                <div className="info-value">
                  <span className="status-badge enabled">✓ Enabled</span>
                </div>
              </div>
            </div>
          </div>

          <div className="info-section">
            <h2>🔧 Available Tools</h2>
            <div className="info-tools">
              <div className="tool-card">
                <div className="tool-icon">🧮</div>
                <div className="tool-name">Math & Code Execution</div>
                <div className="tool-desc">Execute Python code and mathematical calculations</div>
              </div>
              <div className="tool-card">
                <div className="tool-icon">🔍</div>
                <div className="tool-name">Conversation Search</div>
                <div className="tool-desc">Search through your conversation history</div>
              </div>
              <div className="tool-card">
                <div className="tool-icon">📁</div>
                <div className="tool-name">File Operations</div>
                <div className="tool-desc">Read and write files on the system</div>
              </div>
              <div className="tool-card">
                <div className="tool-icon">🌐</div>
                <div className="tool-name">HTTP Requests</div>
                <div className="tool-desc">Make web requests and API calls</div>
              </div>
              <div className="tool-card">
                <div className="tool-icon">🛍️</div>
                <div className="tool-name">Product Search</div>
                <div className="tool-desc">Browse AwesomeGear merchandise catalog</div>
              </div>
              {isAdmin && (
                <>
                  <div className="tool-card admin-only">
                    <div className="tool-icon">🌍</div>
                    <div className="tool-name">Global Search</div>
                    <div className="tool-desc">Search all users' conversations (Admin only)</div>
                  </div>
                  <div className="tool-card admin-only">
                    <div className="tool-icon">🐛</div>
                    <div className="tool-name">Debug Commands</div>
                    <div className="tool-desc">Execute shell commands (Admin only)</div>
                  </div>
                </>
              )}
            </div>
          </div>

          <div className="info-section">
            <h2>📊 Platform Details</h2>
            <div className="info-grid">
              <div className="info-item">
                <div className="info-label">Frontend</div>
                <div className="info-value">React + TypeScript</div>
              </div>
              <div className="info-item">
                <div className="info-label">Backend</div>
                <div className="info-value">Python + FastAPI</div>
              </div>
              <div className="info-item">
                <div className="info-label">Database</div>
                <div className="info-value">SQLite</div>
              </div>
              <div className="info-item">
                <div className="info-label">Authentication</div>
                <div className="info-value">JWT Tokens</div>
              </div>
            </div>
          </div>

          {isAdmin && (
            <div className="info-note">
              <strong>👑 Admin Access:</strong> You have access to all features including user management, 
              system configuration, and admin-only tools. Visit the Admin Panel to manage settings.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default InfoPage;
