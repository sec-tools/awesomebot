import React, { useState, useEffect } from 'react';
import { getMCPServers, createMCPServer, deleteMCPServer, getMCPTools, toggleMCPServer } from '../utils/api';
import './MCPPage.css';

interface MCPServer {
    id: string;
    name: string;
    command: string;
    args: string[];
    env: Record<string, string>;
    enabled: boolean;
    created_at: string;
}

interface MCPTool {
    name: string;
    description: string;
    server_id: string;
    server_name?: string;
    inputSchema?: any;
}

const MCPPage: React.FC<{ token: string }> = ({ token }) => {
    const [servers, setServers] = useState<MCPServer[]>([]);
    const [tools, setTools] = useState<MCPTool[]>([]);
    const [showAddForm, setShowAddForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    
    // Form state
    const [name, setName] = useState('');
    const [command, setCommand] = useState('');
    const [args, setArgs] = useState('');
    const [env, setEnv] = useState('');

    useEffect(() => {
        loadServers();
        loadTools();
    }, []);

    const loadServers = async () => {
        try {
            const data = await getMCPServers(token);
            setServers(data.servers || []);
        } catch (error) {
            console.error('Failed to load MCP servers:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadTools = async () => {
        try {
            const data = await getMCPTools(token);
            setTools(data.tools || []);
        } catch (error) {
            console.error('Failed to load MCP tools:', error);
        }
    };

    const handleAddServer = async (e: React.FormEvent) => {
        e.preventDefault();
        
        try {
            const argsArray = args.split('\n').filter(a => a.trim());
            const envObject = env ? JSON.parse(env) : {};
            
            await createMCPServer(token, {
                name,
                command,
                args: argsArray,
                env: envObject
            });
            
            // Reset form
            setName('');
            setCommand('');
            setArgs('');
            setEnv('');
            setShowAddForm(false);
            
            // Reload servers
            await loadServers();
            await loadTools();
        } catch (error: any) {
            alert(`Failed to add MCP server: ${error.message}`);
        }
    };

    const handleDeleteServer = async (serverId: string) => {
        if (!window.confirm('Are you sure you want to delete this MCP server?')) {
            return;
        }
        
        try {
            await deleteMCPServer(token, serverId);
            await loadServers();
            await loadTools();
        } catch (error) {
            alert('Failed to delete MCP server');
        }
    };

    const handleToggleServer = async (serverId: string) => {
        try {
            await toggleMCPServer(token, serverId);
            await loadServers();
            await loadTools();
        } catch (error) {
            alert('Failed to toggle MCP server');
        }
    };

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setUploading(true);
        
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/mcp/servers/upload', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const result = await response.json();
            
            // Show results
            let message = result.message;
            if (result.failed && result.failed.length > 0) {
                message += '\n\nFailed servers:\n';
                result.failed.forEach((f: any) => {
                    message += `- ${f.name}: ${f.error}\n`;
                });
            }
            
            alert(message);
            
            // Reload servers
            await loadServers();
            await loadTools();
            
            // Clear the file input
            event.target.value = '';
        } catch (error: any) {
            alert(`Upload failed: ${error.message}`);
        } finally {
            setUploading(false);
        }
    };

    if (loading) {
        return <div className="mcp-page"><div className="loading">Loading...</div></div>;
    }

    return (
        <div className="mcp-page">
            <div className="mcp-header">
                <h1>🔌 MCP Servers</h1>
                <p className="subtitle">Model Context Protocol - Connect external tools and data sources</p>
                <div className="header-actions">
                    <label className="upload-button" title="Upload MCP server configuration (JSON)">
                        <input
                            type="file"
                            accept=".json,.txt"
                            onChange={handleFileUpload}
                            disabled={uploading}
                            style={{ display: 'none' }}
                        />
                        📤 {uploading ? 'Uploading...' : 'Upload Config'}
                    </label>
                    <button onClick={() => setShowAddForm(!showAddForm)} className="add-button">
                        {showAddForm ? 'Cancel' : '+ Add MCP Server'}
                    </button>
                </div>
            </div>

            {showAddForm && (
                <div className="add-form-container">
                    <form onSubmit={handleAddServer} className="add-form">
                        <h3>Add New MCP Server</h3>
                        
                        <div className="form-group">
                            <label>Name</label>
                            <input
                                type="text"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Filesystem Server"
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label>Command</label>
                            <input
                                type="text"
                                value={command}
                                onChange={(e) => setCommand(e.target.value)}
                                placeholder="e.g., npx or python"
                                required
                            />
                        </div>

                        <div className="form-group">
                            <label>Arguments (one per line)</label>
                            <textarea
                                value={args}
                                onChange={(e) => setArgs(e.target.value)}
                                placeholder="e.g.,&#10;-y&#10;@modelcontextprotocol/server-filesystem&#10;/path/to/allowed/directory"
                                rows={4}
                            />
                        </div>

                        <div className="form-group">
                            <label>Environment Variables (JSON)</label>
                            <textarea
                                value={env}
                                onChange={(e) => setEnv(e.target.value)}
                                placeholder='{"KEY": "value"}'
                                rows={3}
                            />
                        </div>

                        <div className="form-actions">
                            <button type="submit" className="submit-button">Add Server</button>
                            <button type="button" onClick={() => setShowAddForm(false)} className="cancel-button">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            <div className="servers-section">
                <h2>Configured Servers ({servers.length})</h2>
                {servers.length === 0 ? (
                    <div className="empty-state">
                        <p>No MCP servers configured yet.</p>
                        <p className="hint">Add a server to connect external tools and data sources.</p>
                    </div>
                ) : (
                    <div className="servers-grid">
                        {servers.map((server) => (
                            <div key={server.id} className={`server-card ${server.enabled ? 'enabled' : 'disabled'}`}>
                                <div className="server-header">
                                    <h3>{server.name}</h3>
                                    <div className="server-actions">
                                        <button
                                            onClick={() => handleToggleServer(server.id)}
                                            className={`toggle-button ${server.enabled ? 'on' : 'off'}`}
                                            title={server.enabled ? 'Disable' : 'Enable'}
                                        >
                                            {server.enabled ? '✓' : '○'}
                                        </button>
                                        <button
                                            onClick={() => handleDeleteServer(server.id)}
                                            className="delete-button"
                                            title="Delete"
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                                
                                <div className="server-details">
                                    <div className="detail-row">
                                        <span className="label">Command:</span>
                                        <code>{server.command}</code>
                                    </div>
                                    {server.args.length > 0 && (
                                        <div className="detail-row">
                                            <span className="label">Args:</span>
                                            <code>{server.args.join(' ')}</code>
                                        </div>
                                    )}
                                    <div className="detail-row">
                                        <span className="label">Status:</span>
                                        <span className={`status ${server.enabled ? 'active' : 'inactive'}`}>
                                            {server.enabled ? 'Active' : 'Inactive'}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>

            <div className="tools-section">
                <h2>Available Tools ({tools.length})</h2>
                {tools.length === 0 ? (
                    <div className="empty-state">
                        <p>No tools available from MCP servers.</p>
                    </div>
                ) : (
                    <div className="tools-grid">
                        {tools.map((tool, idx) => (
                            <div key={idx} className="tool-card">
                                <h4>{tool.name}</h4>
                                <p className="tool-description">{tool.description}</p>
                                <div className="tool-meta">
                                    <span className="server-badge">
                                        {tool.server_name || 'Unknown Server'}
                                    </span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default MCPPage;

