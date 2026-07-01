import React, { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';

export default function StatusBar() {
  const [status, setStatus] = useState('checking'); // 'online' | 'offline' | 'checking'

  const checkHealth = async () => {
    setStatus('checking');
    try {
      const res = await fetch('/health');
      if (res.ok) {
        setStatus('online');
      } else {
        setStatus('offline');
      }
    } catch {
      setStatus('offline');
    }
  };

  useEffect(() => {
    checkHealth();
    // Poll every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="status-bar">
      <div className="status-left">
        <span style={{ fontWeight: '600' }}>Backend Link:</span>
        <span className={`status-indicator ${status}`} />
        <span className="status-text">
          {status === 'online' ? 'CONNECTED' : status === 'offline' ? 'DISCONNECTED (API OFFLINE)' : 'CHECKING...'}
        </span>
      </div>
      <button onClick={checkHealth} className="status-btn">
        <RefreshCw size={10} className={status === 'checking' ? 'animate-spin' : ''} />
        <span>Check Link</span>
      </button>
    </div>
  );
}
