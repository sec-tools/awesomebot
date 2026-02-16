import React, { useState, useEffect, useCallback } from 'react';
import Sidebar from './components/Sidebar';
import ChatPage from './pages/ChatPage';
import FilesPage from './pages/FilesPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import AdminPage from './pages/AdminPage';
import MCPPage from './pages/MCPPage';
import APITestPage from './pages/APITestPage';
import InfoPage from './pages/InfoPage';
import StatusIndicator from './components/StatusIndicator';
import { BackgroundExecutionProvider } from './contexts/BackgroundExecutionContext';
import './App.css';

type Page = 'chat' | 'files' | 'admin' | 'mcp' | 'apitest' | 'info';
type AuthPage = 'login' | 'signup';

const AppContent: React.FC = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authPage, setAuthPage] = useState<AuthPage>('login');
  const [token, setToken] = useState<string>('');
  const [username, setUsername] = useState<string>('');
  const [isAdmin, setIsAdmin] = useState(false);
  const [currentPage, setCurrentPage] = useState<Page>('chat');
  const [conversationId, setConversationId] = useState<string | undefined>();

  // Token refresh function
  const refreshToken = useCallback(async () => {
    const currentToken = localStorage.getItem('token');
    if (!currentToken) return false;

    try {
      const response = await fetch('http://localhost:8000/api/auth/refresh', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${currentToken}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const data = await response.json();
        setToken(data.access_token);
        setUsername(data.username);
        setIsAdmin(data.is_admin);
        
        // Update localStorage
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('username', data.username);
        localStorage.setItem('isAdmin', String(data.is_admin));
        
        console.log('✅ Token refreshed successfully');
        return true;
      } else {
        // Token refresh failed - force logout
        console.warn('⚠️ Token refresh failed, logging out');
        handleLogout();
        return false;
      }
    } catch (error) {
      console.error('❌ Token refresh error:', error);
      return false;
    }
  }, []);

  // Check for existing token on load
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUsername = localStorage.getItem('username');
    const savedIsAdmin = localStorage.getItem('isAdmin') === 'true';

    if (savedToken && savedUsername) {
      setToken(savedToken);
      setUsername(savedUsername);
      setIsAdmin(savedIsAdmin);
      setIsAuthenticated(true);
      
      // Immediately refresh token on app load to ensure it's valid
      refreshToken();
    }
  }, [refreshToken]);

  // Auto-refresh token every 24 hours (before 30-day expiration)
  useEffect(() => {
    if (!isAuthenticated) return;

    // Refresh token every 24 hours
    const refreshInterval = setInterval(() => {
      console.log('🔄 Auto-refreshing token...');
      refreshToken();
    }, 24 * 60 * 60 * 1000); // 24 hours

    return () => clearInterval(refreshInterval);
  }, [isAuthenticated, refreshToken]);

  // Global 401 error handler
  useEffect(() => {
    const handleUnauthorized = (event: CustomEvent) => {
      console.warn('⚠️ 401 Unauthorized detected, attempting token refresh...');
      refreshToken().then(success => {
        if (!success) {
          alert('Your session has expired. Please log in again.');
        }
      });
    };

    window.addEventListener('unauthorized' as any, handleUnauthorized);
    return () => window.removeEventListener('unauthorized' as any, handleUnauthorized);
  }, [refreshToken]);

  const handleAuth = (newToken: string, newUsername: string, newIsAdmin: boolean) => {
    setToken(newToken);
    setUsername(newUsername);
    setIsAdmin(newIsAdmin);
    setIsAuthenticated(true);

    // Save to localStorage
    localStorage.setItem('token', newToken);
    localStorage.setItem('username', newUsername);
    localStorage.setItem('isAdmin', String(newIsAdmin));
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setToken('');
    setUsername('');
    setIsAdmin(false);

    // Clear localStorage
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('isAdmin');
  };

  const handleNewChat = () => {
    setConversationId(undefined);
    setCurrentPage('chat');
  };

  const handleSelectConversation = (id: string) => {
    setConversationId(id);
    setCurrentPage('chat');
  };

  // If not authenticated, show auth pages
  if (!isAuthenticated) {
    if (authPage === 'login') {
      return (
        <LoginPage
          onLogin={handleAuth}
          onSwitchToSignup={() => setAuthPage('signup')}
        />
      );
    } else {
      return (
        <SignupPage
          onSignup={handleAuth}
          onSwitchToLogin={() => setAuthPage('login')}
        />
      );
    }
  }

  // Main app UI
  return (
    <div className="app">
      <Sidebar
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        currentConversationId={conversationId}
        token={token}
      />
      
      <div className="main-content">
        <nav className="top-nav">
          <div className="nav-left">
            <button
              className={currentPage === 'chat' ? 'active' : ''}
              onClick={() => setCurrentPage('chat')}
            >
              💬 Chat
            </button>
            <button
              className={currentPage === 'apitest' ? 'active' : ''}
              onClick={() => setCurrentPage('apitest')}
            >
              API
            </button>
            <button
              className={currentPage === 'files' ? 'active' : ''}
              onClick={() => setCurrentPage('files')}
            >
              📁 Files
            </button>
            <button
              className={currentPage === 'mcp' ? 'active' : ''}
              onClick={() => setCurrentPage('mcp')}
            >
              🔌 MCP
            </button>
            <button
              className={currentPage === 'info' ? 'active' : ''}
              onClick={() => setCurrentPage('info')}
            >
              ℹ️ Info
            </button>
            {isAdmin && (
              <button
                className={currentPage === 'admin' ? 'active' : ''}
                onClick={() => setCurrentPage('admin')}
              >
                ⚙️ Admin
              </button>
            )}
          </div>
          
          <div className="nav-center">
            <StatusIndicator token={token} />
          </div>
          
          <div className="user-info">
            <span>{username}</span>
            <button onClick={handleLogout} className="logout-button">
              Logout
            </button>
          </div>
        </nav>

        {currentPage === 'chat' && (
          <ChatPage 
            key={conversationId || 'new'} 
            conversationId={conversationId} 
            token={token}
            onConversationCreated={setConversationId}
          />
        )}
        {currentPage === 'files' && <FilesPage token={token} />}
        {currentPage === 'mcp' && <MCPPage token={token} />}
        {currentPage === 'info' && <InfoPage token={token} isAdmin={isAdmin} />}
        {currentPage === 'apitest' && <APITestPage token={token} />}
        {currentPage === 'admin' && isAdmin && <AdminPage token={token} />}
      </div>
    </div>
  );
};

const App: React.FC = () => {
  return (
    <BackgroundExecutionProvider>
      <AppContent />
    </BackgroundExecutionProvider>
  );
};

export default App;
