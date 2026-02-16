import React, { useState, useRef, useEffect } from 'react';
import './APITestPage.css';

interface APITestPageProps {
  token: string;
}

interface Message {
  role: string;
  content: string;
  timestamp?: string;
}

const APITestPage: React.FC<APITestPageProps> = ({ token }) => {
  const defaultOutput = [
    '// API Console',
    '// Direct API testing without frontend enhancements',
    '// - No search files/RAG context',
    '// - No frontend variables or state',
    '// - Pure prompt → backend → response',
    ''
  ];

  const [input, setInput] = useState('');
  const [output, setOutput] = useState<string[]>(defaultOutput);
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const outputRef = useRef<HTMLDivElement>(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Load saved session state on mount
  useEffect(() => {
    const loadSessionState = () => {
      try {
        const savedInput = localStorage.getItem('api_console_input');
        const savedOutput = localStorage.getItem('api_console_output');
        const savedConversationId = localStorage.getItem('api_console_conversation_id');

        if (savedInput) {
          setInput(savedInput);
        }

        if (savedOutput) {
          const parsedOutput = JSON.parse(savedOutput);
          if (Array.isArray(parsedOutput) && parsedOutput.length > 0) {
            setOutput(parsedOutput);
          }
        }

        if (savedConversationId && savedConversationId !== 'undefined' && savedConversationId !== 'null') {
          setConversationId(savedConversationId);
        }
      } catch (error) {
        console.error('Failed to load API console session state:', error);
      } finally {
        setIsInitialized(true);
      }
    };

    loadSessionState();
  }, []);

  // Save session state whenever it changes
  useEffect(() => {
    if (!isInitialized) return;

    try {
      localStorage.setItem('api_console_input', input);
      localStorage.setItem('api_console_output', JSON.stringify(output));
      if (conversationId) {
        localStorage.setItem('api_console_conversation_id', conversationId);
      }
    } catch (error) {
      console.error('Failed to save API console session state:', error);
    }
  }, [input, output, conversationId, isInitialized]);

  useEffect(() => {
    // Auto-scroll to bottom when output changes
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [output]);

  // Note: Session state (input, output, conversationId) is now loaded in the initial useEffect above
  // No need to fetch from backend since we're saving the complete console state to localStorage

  const addOutput = (text: string, type: 'request' | 'response' | 'error' | 'info' = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    const prefix = type === 'request' ? '→ REQUEST' : 
                   type === 'response' ? '← RESPONSE' : 
                   type === 'error' ? '✖ ERROR' : 
                   'ℹ INFO';
    setOutput(prev => [...prev, `[${timestamp}] ${prefix}: ${text}`, '']);
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const prompt = input.trim();
    setInput('');
    setIsLoading(true);

    // Save to command history
    setCommandHistory((prev) => [...prev, prompt]);
    setHistoryIndex(-1);

    addOutput(`Sending prompt: "${prompt}"`, 'request');

    try {
      const response = await fetch('http://localhost:8000/api/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: prompt,
          conversation_id: conversationId, // Continue existing conversation or create new
          use_rag: false // Explicitly disable search files/RAG for clean API testing
        })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      addOutput('Streaming response...', 'info');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let newConversationId: string | null = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n').filter(line => line.trim());

          for (const line of lines) {
            try {
              const data = JSON.parse(line);
              
              if (data.type === 'text' || data.type === 'text_start') {
                // Main text response content
                if (data.content) {
                  fullResponse += data.content;
                }
              } else if (data.type === 'search_results') {
                // Search results - capture the content (takes priority over tool_result)
                if (data.content) {
                  fullResponse += data.content;
                }
                addOutput('Event: search_results', 'info');
              } else if (data.type === 'tool_result') {
                // Tool execution results - only add if we haven't already captured search_results
                // (search_results already contains the output, so skip to avoid duplication)
                addOutput('Event: tool_result', 'info');
              } else if (data.type === 'done') {
                addOutput('Stream complete', 'info');
              } else if (data.type === 'conversation_id') {
                // Extract conversation_id from the data
                const convId = data.conversation_id;
                if (convId && typeof convId === 'string' && convId.length > 10) {
                  newConversationId = convId;
                  addOutput(`Conversation ID: ${convId.substring(0, 8)}...`, 'info');
                  setConversationId(convId);
                  localStorage.setItem('api_console_conversation_id', convId);
                }
              } else if (data.type === 'tool_detection' || data.type === 'tool_code' || data.type === 'tool_execution') {
                // Tool progress events - just log them
                addOutput(`Event: ${data.type}`, 'info');
              } else {
                // Log other event types for debugging
                addOutput(`Event: ${data.type}`, 'info');
              }
            } catch (e) {
              // Skip invalid JSON
            }
          }
        }
      }

      if (fullResponse) {
        addOutput(fullResponse, 'response');
      }

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unknown error';
      addOutput(errorMsg, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length === 0) return;

      const newIndex = historyIndex === -1 
        ? commandHistory.length - 1 
        : Math.max(0, historyIndex - 1);

      setHistoryIndex(newIndex);
      setInput(commandHistory[newIndex]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex === -1) return;

      const newIndex = historyIndex + 1;
      if (newIndex >= commandHistory.length) {
        setHistoryIndex(-1);
        setInput('');
      } else {
        setHistoryIndex(newIndex);
        setInput(commandHistory[newIndex]);
      }
    }
  };

  const clearConsole = () => {
    const defaultOutput = [
      '// API Console',
      '// Direct API testing without frontend enhancements',
      '// - No search files/RAG context',
      '// - No frontend variables or state',
      '// - Pure prompt → backend → response',
      ''
    ];
    setOutput(defaultOutput);
    setInput('');
    setCommandHistory([]);
    setHistoryIndex(-1);
    
    // Clear saved state from localStorage
    localStorage.setItem('api_console_output', JSON.stringify(defaultOutput));
    localStorage.setItem('api_console_input', '');
  };

  const startNewConversation = () => {
    setConversationId(null);
    localStorage.removeItem('api_console_conversation_id');
    clearConsole();
  };

  return (
    <div className="api-test-page">
      <div className="api-test-header">
        <h2>API Console</h2>
        <div className="header-info">
          <span className="isolation-badge">🔒 Isolated Mode</span>
          {conversationId && (
            <span className="conversation-badge">
              💬 Conversation Active
            </span>
          )}
          <button onClick={startNewConversation} className="new-conversation-btn">
            + New Conversation
          </button>
          <button onClick={clearConsole} className="clear-btn">
            Clear Console
          </button>
        </div>
      </div>

      <div className="api-test-container">
        <div className="input-section">
          <div className="section-label">PROMPT</div>
          <textarea
            className="console-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            onKeyDown={handleKeyDown}
            placeholder="Enter your test prompt here... (Shift+Enter for new line, Enter to send, ↑/↓ for history)"
            disabled={isLoading}
          />
          <div className="input-controls">
            <div className="input-info">
              Endpoint: <code>POST /api/chat/stream</code>
              <span className="config-badge">use_rag: false</span>
            </div>
            <button 
              onClick={handleSend} 
              disabled={!input.trim() || isLoading}
              className="send-btn"
            >
              {isLoading ? 'Sending...' : 'Send Request →'}
            </button>
          </div>
        </div>

        <div className="output-section">
          <div className="section-label">RESPONSE</div>
          <div className={`console-output ${isLoading ? 'loading-fade' : ''}`} ref={outputRef}>
            {output.map((line, index) => (
              <div key={index} className="console-line">
                {line}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default APITestPage;
