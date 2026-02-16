import React, { useState, useEffect, useRef } from 'react';
import ChatMessage from '../components/ChatMessage';
import { useBackgroundExecution } from '../contexts/BackgroundExecutionContext';
import './ChatPage.css';

interface ExecutionMetadata {
  code_executed: boolean;
  execution_code?: string;
  execution_output?: string;
  execution_error?: string;
}

interface ToolMetadata {
  tool_used: boolean;
  tool_name?: string;
  tool_code?: string;
  tool_output?: string;
  tool_error?: string;
  tool_metadata?: Record<string, any>;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  executionMetadata?: ExecutionMetadata;
  toolMetadata?: ToolMetadata;
}

interface ChatPageProps {
  conversationId?: string;
  token: string;
  onConversationCreated?: (id: string) => void;
}

const ChatPage: React.FC<ChatPageProps> = ({ conversationId, token, onConversationCreated }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { startExecution, stopExecution, isExecuting } = useBackgroundExecution();
  const abortControllerRef = useRef<AbortController | null>(null);
  // Store the latest toolMetadata from streaming - key is conversationId
  const latestToolMetadataRef = useRef<{ conversationId: string; metadata: { executionMetadata?: any; toolMetadata?: any } } | null>(null);
  // Ref to track current messages for polling (avoids stale closure)
  const messagesRef = useRef<Message[]>([]);

  // Keep messagesRef in sync with state (for use in intervals/callbacks)
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Clear everything when starting a new chat or switching conversations
  useEffect(() => {
    // Abort any ongoing streaming request when conversation changes
    if (abortControllerRef.current) {
      console.log('Aborting ongoing request due to conversation change');
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    
    if (!conversationId) {
      setMessages([]);
      setInput('');
      setIsLoading(false);
      setCommandHistory([]);
      setHistoryIndex(-1);
      if (textareaRef.current) {
        textareaRef.current.value = '';
      }
    }
    
    // Always focus the textarea when conversation changes (including new chat)
    setTimeout(() => {
      textareaRef.current?.focus();
    }, 100);
  }, [conversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);
  
  // Focus textarea on initial mount and cleanup on unmount
  useEffect(() => {
    textareaRef.current?.focus();
    
    // Cleanup: abort any ongoing request when component unmounts
    return () => {
      if (abortControllerRef.current) {
        console.log('Aborting ongoing request due to component unmount');
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (conversationId) {
      // Delay check to allow React to sync messages state first
      // This prevents loading from API when we just created a conversation via streaming
      const timeoutId = setTimeout(() => {
        const currentMsgCount = messagesRef.current.length;
        if (currentMsgCount === 0) {
          // Only load from API if we truly have no messages after a short delay
          loadConversation(conversationId);
        }
      }, 100); // 100ms delay to let state sync
      
      return () => clearTimeout(timeoutId);
    } else {
      setMessages([]);
    }
  }, [conversationId, token]);

  const loadConversation = async (id: string) => {
    try {
      const response = await fetch(`/api/conversations/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      // Don't process if response failed
      if (!response.ok) {
        console.error('loadConversation failed:', response.status);
        return;
      }
      
      const msgs = await response.json();
      
      // Ensure msgs is an array before processing
      if (!Array.isArray(msgs)) {
        console.error('loadConversation: msgs is not an array', msgs);
        return;
      }
      
      // Preserve toolMetadata from current messages (API doesn't store it)
      // Match messages by role+index position within their role type
      setMessages((prev) => {
        // Build metadata lookup by role + position
        const userMetadata: Array<{ executionMetadata?: any; toolMetadata?: any } | null> = [];
        const assistantMetadata: Array<{ executionMetadata?: any; toolMetadata?: any } | null> = [];
        
        prev.forEach((msg) => {
          const meta = (msg.toolMetadata || msg.executionMetadata) 
            ? { executionMetadata: msg.executionMetadata, toolMetadata: msg.toolMetadata }
            : null;
          if (msg.role === 'user') {
            userMetadata.push(meta);
          } else {
            assistantMetadata.push(meta);
          }
        });
        
        // Track positions while mapping
        let userIdx = 0;
        let assistantIdx = 0;
        
        return msgs.map((msg: Message) => {
          let existing = null;
          if (msg.role === 'user') {
            existing = userMetadata[userIdx++];
          } else {
            existing = assistantMetadata[assistantIdx++];
          }
          if (existing) {
            return { ...msg, ...existing };
          }
          return msg;
        });
      });
      
      // Populate command history with user messages from this conversation
      const userMessages = msgs
        .filter((msg: Message) => msg.role === 'user')
        .map((msg: Message) => msg.content);
      setCommandHistory(userMessages);
      setHistoryIndex(-1);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
    };

    // Save to command history
    setCommandHistory((prev) => [...prev, input.trim()]);
    setHistoryIndex(-1);

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Create abort controller for this request
    abortControllerRef.current = new AbortController();

    try {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Mark this conversation as executing
      if (conversationId) {
        startExecution(conversationId, abortControllerRef.current);
      }

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: userMessage.content,
          conversation_id: conversationId,
          use_rag: useRag
        }),
        signal: abortControllerRef.current.signal
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullResponse = '';
      let executionMetadata: ExecutionMetadata = { code_executed: false };
      let toolMetadata: ToolMetadata = { tool_used: false };
      let buffer = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          
          // Keep the last incomplete line in the buffer
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim()) continue;

            try {
              const data = JSON.parse(line);
              const type = data.type;

              if (type === 'conversation_id') {
                // New conversation created - update parent state
                if (!conversationId && data.conversation_id && onConversationCreated) {
                  onConversationCreated(data.conversation_id);
                }
                continue; // Don't render this message
              } else if (type === 'tool_detection') {
                // Detect if this is a global search query by checking the content
                const isGlobalSearch = data.content && (
                  data.content.includes('search all users') ||
                  data.content.toLowerCase().includes('global search')
                );
                
                // Only show tool detection for non-global-search tools
                if (!isGlobalSearch) {
                  fullResponse += `\n\n${data.content}\n\n`;
                }
                toolMetadata.tool_used = true;
              } else if (type === 'tool_code') {
                // Store code for tool metadata
                executionMetadata.code_executed = true;
                executionMetadata.execution_code = data.content;
                toolMetadata.tool_code = data.content;
              } else if (type === 'tool_execution') {
                // Check if this is related to global search by looking at previous messages
                const isGlobalSearchExecution = fullResponse.toLowerCase().includes('search all users');
                
                // Only show execution status for non-global-search tools
                if (!isGlobalSearchExecution) {
                  fullResponse += `${data.content}\n`;
                }
              } else if (type === 'search_results') {
                // Display search results DIRECTLY without AI processing
                // Wrap in pre tags to preserve formatting (👤/🤖, line breaks, etc.)
                fullResponse += `\n\n${data.content}\n\n`;
                toolMetadata.tool_used = true;
                toolMetadata.tool_name = 'conversation_memory';
              } else if (type === 'tool_result') {
                // Store tool results with full metadata
                executionMetadata.execution_output = data.output;
                executionMetadata.execution_error = data.error;
                toolMetadata.tool_used = true;
                toolMetadata.tool_name = data.tool || 'unknown';
                toolMetadata.tool_output = data.output;
                toolMetadata.tool_error = data.error;
                toolMetadata.tool_metadata = data.metadata;
                if (data.success) {
                  fullResponse += `\n✅ Tool executed successfully\n\n`;
                } else {
                  fullResponse += `\n❌ Tool execution failed\n\n`;
                }
              } else if (type === 'text') {
                // Regular text content
                fullResponse += data.content;
              } else if (type === 'text_start') {
                // Clear any tool status messages for final response
                // Keep them for now
              }

              // Store metadata in ref to persist across API reloads
              if (toolMetadata.tool_used || executionMetadata.code_executed) {
                // We'll get the conversationId from the onConversationCreated callback or existing prop
                const convId = conversationId || 'pending';
                const newRef = {
                  conversationId: convId,
                  metadata: {
                    executionMetadata: executionMetadata.code_executed ? { ...executionMetadata } : undefined,
                    toolMetadata: toolMetadata.tool_used ? { ...toolMetadata } : undefined,
                  }
                };
                latestToolMetadataRef.current = newRef;
              }
              
              setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  ...assistantMessage,
                  content: fullResponse,
                  executionMetadata: executionMetadata.code_executed ? { ...executionMetadata } : undefined,
                  toolMetadata: toolMetadata.tool_used ? { ...toolMetadata } : undefined,
                };
                return newMessages;
              });
            } catch (e) {
              // Not JSON, treat as plain text (backward compatibility)
              fullResponse += line;
              setMessages((prev) => {
                const newMessages = [...prev];
                newMessages[newMessages.length - 1] = {
                  ...assistantMessage,
                  content: fullResponse,
                };
                return newMessages;
              });
            }
          }
        }
      }
    } catch (error) {
      // Only show error if not aborted (user didn't cancel)
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to send message:', error);
        
        // Trigger immediate health check
        window.dispatchEvent(new Event('network-error'));
        
        let errorMessage = 'Unknown error';
        if (error instanceof TypeError && error.message.includes('fetch')) {
          errorMessage = 'Backend is not responding. Please check if the server is running.';
        } else if (error instanceof Error) {
          errorMessage = error.message;
        }
        
        // Update the last assistant message with error
        setMessages((prev) => {
          const newMessages = [...prev];
          if (newMessages[newMessages.length - 1]?.role === 'assistant') {
            newMessages[newMessages.length - 1] = {
              ...newMessages[newMessages.length - 1],
              content: `🔴 Error: Failed to get response from the server.\n\n${errorMessage}\n\nPlease check:\n- Backend is running (http://localhost:8000/health)\n- Network connection\n- Status indicator at the top`,
            };
          } else {
            newMessages.push({
              id: Date.now().toString(),
              role: 'assistant',
              content: `🔴 Error: Failed to get response from the server.\n\n${errorMessage}`,
            });
          }
          return newMessages;
        });
      }
    } finally {
      setIsLoading(false);
      // Mark execution as complete
      if (conversationId) {
        stopExecution(conversationId);
      }
      abortControllerRef.current = null;
      
      // Refocus the textarea for next input
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 100);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === 'ArrowUp') {
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

  return (
    <div className="chat-page">
      <div className="chat-header">
        <div className="chat-controls">
          <label className="rag-toggle">
            <input
              type="checkbox"
              checked={useRag}
              onChange={(e) => setUseRag(e.target.checked)}
            />
            <span className="rag-label">
              📚 Search Files
              <span className="rag-status">
                {useRag ? ' (ON)' : ' (OFF)'}
              </span>
            </span>
          </label>
          <div className="rag-info">
            <span className="info-icon" title={useRag 
              ? "RAG is ON: AI will search your uploaded files in the Files tab to answer questions with context from your files." 
              : "RAG is OFF: AI will answer from its training knowledge only. Upload files in Files tab and turn RAG ON to search them."}>
              ℹ️
            </span>
          </div>
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <img src="/awesomebot-logo.svg" alt="AwesomeBot" />
            </div>
            <h2>Welcome to AwesomeBot</h2>
            <p>Start a conversation by typing a message below</p>
          </div>
        ) : (
          messages.map((msg, index) => {
            // For the last assistant message in current conversation, merge stored metadata
            let finalExecutionMetadata = msg.executionMetadata;
            let finalToolMetadata = msg.toolMetadata;
            
            const isLastAssistant = msg.role === 'assistant' && 
              index === messages.length - 1;
            
            // Use ref fallback if message doesn't have metadata
            if (isLastAssistant && !finalToolMetadata && !finalExecutionMetadata && latestToolMetadataRef.current) {
              const refConvId = latestToolMetadataRef.current.conversationId;
              const match = refConvId === conversationId || refConvId === 'pending';
              if (match) {
                finalExecutionMetadata = latestToolMetadataRef.current.metadata.executionMetadata;
                finalToolMetadata = latestToolMetadataRef.current.metadata.toolMetadata;
              }
            }
            
            return (
              <ChatMessage 
                key={msg.id} 
                role={msg.role} 
                content={msg.content}
                executionMetadata={finalExecutionMetadata}
                toolMetadata={finalToolMetadata}
              />
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message... (Shift+Enter for new line)"
          disabled={isLoading}
          rows={1}
        />
        <button onClick={handleSend} disabled={isLoading || !input.trim()}>
          {isLoading ? <span className="spinner"></span> : '➤'}
        </button>
      </div>
    </div>
  );
};

export default ChatPage;
