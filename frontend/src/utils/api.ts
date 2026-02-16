import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
export const setAuthToken = (token: string) => {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common['Authorization'];
  }
};

// Chat API
export const sendMessage = async (
  message: string,
  conversationId?: string,
  useRag: boolean = true
) => {
  const response = await api.post('/api/chat/message', {
    message,
    conversation_id: conversationId,
    use_rag: useRag,
  });
  return response.data;
};

export const streamMessage = async (
  message: string,
  onChunk: (chunk: string) => void,
  conversationId?: string,
  useRag: boolean = true
) => {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      conversation_id: conversationId,
      use_rag: useRag,
    }),
  });

  if (!response.ok) {
    throw new Error('Failed to stream message');
  }

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  if (!reader) {
    throw new Error('No reader available');
  }

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    onChunk(chunk);
  }
};

// Conversations API
export const getConversations = async () => {
  const response = await api.get('/api/conversations/');
  return response.data;
};

export const getConversationMessages = async (conversationId: string) => {
  const response = await api.get(`/api/conversations/${conversationId}`);
  return response.data;
};

export const deleteConversation = async (conversationId: string) => {
  const response = await api.delete(`/api/conversations/${conversationId}`);
  return response.data;
};

// Files API
export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/files/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getDocuments = async () => {
  const response = await api.get('/api/files/');
  return response.data;
};

export const deleteDocument = async (documentId: string) => {
  const response = await api.delete(`/api/files/${documentId}`);
  return response.data;
};

// Code API
export const executeCode = async (code: string, language: string = 'python') => {
  const response = await api.post('/api/code/execute', {
    code,
    language,
  });
  return response.data;
};

// Health check
export const checkHealth = async () => {
  const response = await api.get('/health');
  return response.data;
};

// MCP Server APIs
export const getMCPServers = async (token: string) => {
  const response = await fetch(`${API_BASE_URL}/api/mcp/servers`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

export const createMCPServer = async (token: string, data: {
  name: string;
  command: string;
  args: string[];
  env: Record<string, string>;
}) => {
  const response = await fetch(`${API_BASE_URL}/api/mcp/servers`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  });
  if (!response.ok) throw new Error('Failed to create MCP server');
  return response.json();
};

export const deleteMCPServer = async (token: string, serverId: string) => {
  const response = await fetch(`${API_BASE_URL}/api/mcp/servers/${serverId}`, {
    method: 'DELETE',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to delete MCP server');
  return response.json();
};

export const toggleMCPServer = async (token: string, serverId: string) => {
  const response = await fetch(`${API_BASE_URL}/api/mcp/servers/${serverId}/toggle`, {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Failed to toggle MCP server');
  return response.json();
};

export const getMCPTools = async (token: string) => {
  const response = await fetch(`${API_BASE_URL}/api/mcp/tools`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

