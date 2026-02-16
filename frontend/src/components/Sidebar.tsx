import React, { useState, useEffect } from 'react';
import { getConversations, deleteConversation } from '../utils/api';
import { useBackgroundExecution } from '../contexts/BackgroundExecutionContext';
import './Sidebar.css';

interface Conversation {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

interface SidebarProps {
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  currentConversationId?: string;
  token: string;
}

const Sidebar: React.FC<SidebarProps> = ({
  onSelectConversation,
  onNewChat,
  currentConversationId,
  token,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const { isExecuting } = useBackgroundExecution();

  const loadConversations = async () => {
    try {
      const response = await fetch('/api/conversations/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 401) {
        // Token expired - trigger refresh
        console.warn('⚠️ 401 in Sidebar, triggering token refresh');
        window.dispatchEvent(new CustomEvent('unauthorized'));
        return;
      }
      
      if (!response.ok) {
        console.error('Failed to load conversations:', response.status);
        return;
      }
      
      const data = await response.json();
      if (Array.isArray(data)) {
        setConversations(data);
      }
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  useEffect(() => {
    loadConversations();
    
    // Refresh conversations every 5 seconds to catch new ones
    const interval = setInterval(loadConversations, 5000);
    
    return () => clearInterval(interval);
  }, [token]);
  
  // Reload when conversation changes (catches newly created conversations)
  useEffect(() => {
    if (currentConversationId) {
      loadConversations();
    }
  }, [currentConversationId]);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.status === 401) {
        console.warn('⚠️ 401 in handleDelete, triggering token refresh');
        window.dispatchEvent(new CustomEvent('unauthorized'));
        return;
      }
      
      await loadConversations();
      if (currentConversationId === id) {
        onNewChat();
      }
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  return (
    <>
      <button className="sidebar-toggle" onClick={() => setIsOpen(!isOpen)}>
        ☰
      </button>
      
      <div className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-title-group">
            <h2>AwesomeBot</h2>
            <img src="/awesomebot-logo.svg" alt="AwesomeBot Logo" className="sidebar-logo" />
          </div>
          <button className="close-btn" onClick={() => setIsOpen(false)}>
            ×
          </button>
        </div>

        <button className="new-chat-btn" onClick={() => { onNewChat(); setIsOpen(false); }}>
          + New Chat
        </button>

        <div className="conversations-list">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                currentConversationId === conv.id ? 'active' : ''
              }`}
              onClick={() => {
                onSelectConversation(conv.id);
                setIsOpen(false);
              }}
            >
              <div className="conversation-info">
                <div className="conversation-title">
                  {isExecuting(conv.id) && <span className="executing-indicator">⚡</span>}
                  {conv.title}
                </div>
                <div className="conversation-meta">
                  {conv.message_count} messages
                  {isExecuting(conv.id) && <span className="executing-text"> • Processing...</span>}
                </div>
              </div>
              <button
                className="delete-btn"
                onClick={(e) => handleDelete(conv.id, e)}
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      </div>

      {isOpen && <div className="sidebar-overlay" onClick={() => setIsOpen(false)} />}
    </>
  );
};

export default Sidebar;
