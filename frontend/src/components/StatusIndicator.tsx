import React, { useState, useEffect } from 'react';
import './StatusIndicator.css';

interface StatusIndicatorProps {
    token: string;
}

interface SystemStatus {
    status: 'healthy' | 'degraded' | 'down';
    services: {
        api: string;
        ollama: string;
        database: string;
    };
    responseTime?: number;
}

const StatusIndicator: React.FC<StatusIndicatorProps> = ({ token }) => {
    const [status, setStatus] = useState<SystemStatus | null>(null);
    const [lastCheck, setLastCheck] = useState<Date>(new Date());
    const [isExpanded, setIsExpanded] = useState(false);
    const [isChecking, setIsChecking] = useState(false);

    const checkHealth = async () => {
        if (isChecking) return; // Prevent concurrent checks
        setIsChecking(true);
        
        const startTime = Date.now();
        try {
            // Add a 5-second timeout to detect hanging requests
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000);
            
            // Add cache-busting to prevent stale responses
            const response = await fetch(`/health?t=${Date.now()}`, {
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                signal: controller.signal,
                cache: 'no-cache'
            });
            
            clearTimeout(timeoutId);
            const responseTime = Date.now() - startTime;
            
            if (response.ok) {
                const data = await response.json();
                
                // Verify the response is actually from our backend
                if (!data.services || typeof data.services !== 'object') {
                    throw new Error('Invalid health check response');
                }
                
                // Determine overall status
                let overallStatus: 'healthy' | 'degraded' | 'down' = 'healthy';
                if (data.services.ollama === 'disconnected') {
                    overallStatus = 'degraded';
                }
                if (data.services.api !== 'running' || data.services.database !== 'connected') {
                    overallStatus = 'down';
                }
                
                setStatus({
                    status: overallStatus,
                    services: data.services,
                    responseTime
                });
            } else {
                setStatus({
                    status: 'down',
                    services: {
                        api: 'error',
                        ollama: 'unknown',
                        database: 'unknown'
                    }
                });
            }
        } catch (error) {
            // Backend is down or timeout occurred
            setStatus({
                status: 'down',
                services: {
                    api: 'error',
                    ollama: 'unknown',
                    database: 'unknown'
                }
            });
        } finally {
            setIsChecking(false);
            setLastCheck(new Date());
        }
    };

    const restartServices = async () => {
        if (!window.confirm('This will restart all AwesomeBot services. Continue?')) {
            return;
        }
        
        try {
            const response = await fetch('/api/admin/restart', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                alert('Services are restarting. The page will reload in 15 seconds...');
                setStatus({
                    status: 'down',
                    services: {
                        api: 'restarting',
                        ollama: 'restarting',
                        database: 'restarting'
                    }
                });
                
                // Wait for services to restart
                setTimeout(() => {
                    window.location.reload();
                }, 15000);
            } else {
                alert('Failed to restart services. Please check logs.');
            }
        } catch (error) {
            alert('Error restarting services: ' + (error as Error).message);
        }
    };

    useEffect(() => {
        // Check immediately on mount
        checkHealth();

        // Check every 10 seconds for faster detection of issues
        const interval = setInterval(checkHealth, 10000);
        
        // Listen for network errors from other components
        const handleNetworkError = () => {
            checkHealth();
        };
        window.addEventListener('network-error', handleNetworkError);

        return () => {
            clearInterval(interval);
            window.removeEventListener('network-error', handleNetworkError);
        };
    }, [token]);

    if (!status) {
        return <div className="status-indicator checking">⚪ Checking...</div>;
    }

    const getStatusIcon = () => {
        switch (status.status) {
            case 'healthy':
                return '🟢';
            case 'degraded':
                return '🟡';
            case 'down':
                return '🔴';
            default:
                return '⚪';
        }
    };

    const getStatusText = () => {
        switch (status.status) {
            case 'healthy':
                return 'Online';
            case 'degraded':
                return 'Degraded';
            case 'down':
                return 'Down';
            default:
                return 'Unknown';
        }
    };

    return (
        <div className={`status-indicator ${status.status}`}>
            <div 
                className="status-summary"
                onClick={() => setIsExpanded(!isExpanded)}
                title="Click for details"
            >
                <span className="status-icon">{getStatusIcon()}</span>
                <span className="status-text">{getStatusText()}</span>
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
            </div>
            
            {isExpanded && (
                <div className="status-details">
                    <div className="service-status">
                        <span className="service-name">API:</span>
                        <span className={`service-value ${status.services.api === 'running' ? 'ok' : 'error'}`}>
                            {status.services.api === 'running' ? '✓' : '✗'} {status.services.api}
                        </span>
                    </div>
                    <div className="service-status">
                        <span className="service-name">AI Model:</span>
                        <span className={`service-value ${status.services.ollama === 'connected' ? 'ok' : 'error'}`}>
                            {status.services.ollama === 'connected' ? '✓' : '✗'} {status.services.ollama}
                        </span>
                    </div>
                    <div className="service-status">
                        <span className="service-name">Database:</span>
                        <span className={`service-value ${status.services.database === 'connected' ? 'ok' : 'error'}`}>
                            {status.services.database === 'connected' ? '✓' : '✗'} {status.services.database}
                        </span>
                    </div>
                    {status.responseTime && (
                        <div className="service-status">
                            <span className="service-name">Response Time:</span>
                            <span className="service-value ok">{status.responseTime}ms</span>
                        </div>
                    )}
                    <div className="last-check">
                        Last checked: {lastCheck.toLocaleTimeString()}
                    </div>
                    <div className="action-buttons">
                        <button onClick={checkHealth} className="refresh-button">
                            🔄 Check
                        </button>
                        <button onClick={restartServices} className="restart-button">
                            🔄 Restart
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default StatusIndicator;

