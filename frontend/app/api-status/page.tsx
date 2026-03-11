'use client';
import { useEffect, useState } from 'react';
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
export default function ApiStatus() {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [healthData, setHealthData] = useState<any>(null);
  const [errorMsg, setErrorMsg] = useState('');
  useEffect(() => {
    fetch(`${API}/health`, { signal: AbortSignal.timeout(5000) })
      .then(r => r.json())
      .then(data => { setHealthData(data); setStatus('ok'); })
      .catch(e => { setErrorMsg(e.message || 'Connection failed'); setStatus('error'); });
  }, []);
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 600, margin: 0 }}><span className="rainbow-text">API Status</span></h1>
        <p style={{ color: 'var(--muted)', marginTop: '4px', fontSize: '0.875rem' }}>Backend connectivity check</p>
      </div>
      <div className="card" style={{ maxWidth: '600px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '1.5rem' }}>
          <div style={{
            width: '12px', height: '12px', borderRadius: '50%',
            background: status === 'loading' ? 'var(--muted)' : status === 'ok' ? '#16a34a' : '#ef4444',
            boxShadow: status === 'ok' ? '0 0 8px rgba(22,163,74,0.4)' : status === 'error' ? '0 0 8px rgba(239,68,68,0.4)' : 'none',
          }} />
          <span className="mono" style={{ fontSize: '1rem', fontWeight: 600 }}>
            {status === 'loading' && 'Checking...'}
            {status === 'ok' && 'Backend connected'}
            {status === 'error' && 'Backend unreachable'}
          </span>
        </div>
        <table style={{ width: '100%', fontSize: '0.85rem', borderCollapse: 'collapse' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <td className="mono" style={{ padding: '8px 0', color: 'var(--muted)', width: '40%' }}>API URL</td>
              <td className="mono" style={{ padding: '8px 0' }}>{API}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <td className="mono" style={{ padding: '8px 0', color: 'var(--muted)' }}>Health</td>
              <td className="mono" style={{ padding: '8px 0', color: status === 'ok' ? '#16a34a' : status === 'error' ? '#ef4444' : 'var(--text)' }}>
                {status === 'loading' && '...'}
                {status === 'ok' && (healthData?.status || 'ok')}
                {status === 'error' && errorMsg}
              </td>
            </tr>
            {healthData?.service && (
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <td className="mono" style={{ padding: '8px 0', color: 'var(--muted)' }}>Service</td>
                <td className="mono" style={{ padding: '8px 0' }}>{healthData.service}</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
