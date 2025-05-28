import React, { useState } from 'react';
import { requestGdprDelete, requestCcpaOptout } from '../../api';

export default function ComplianceSettings({ userId }: { userId?: string }) {
  const [gdprStatus, setGdprStatus] = useState('');
  const [ccpaStatus, setCcpaStatus] = useState('');
  const [loading, setLoading] = useState(null);
  const [error, setError] = useState('');

  async function handleGdprDelete() {
    if (!userId) {
      setError('User ID is required.');
      return;
    }
    setLoading('gdpr');
    setError('');
    setGdprStatus('');
    try {
      const res = await requestGdprDelete(userId);
      setGdprStatus(res.status || 'Request submitted');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  }
  async function handleCcpaOptout() {
    if (!userId) {
      setError('User ID is required.');
      return;
    }
    setLoading('ccpa');
    setError('');
    setCcpaStatus('');
    try {
      const res = await requestCcpaOptout(userId);
      setCcpaStatus(res.status || 'Opt-out submitted');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="p-4 bg-white rounded-lg shadow border max-w-lg mx-auto mt-6">
      <h2 className="text-xl font-bold mb-4 text-blue-700">Privacy & Compliance</h2>
      {!userId && (
        <div className="text-red-600 mb-4">User ID is required to perform compliance actions.</div>
      )}
      <div className="mb-4">
        <button
          className="bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded mr-4 disabled:opacity-60"
          onClick={handleGdprDelete}
          disabled={loading === 'gdpr' || !userId}
        >
          {loading === 'gdpr' ? 'Processing...' : 'Delete My Data (GDPR)'}
        </button>
        {gdprStatus && <span className="text-green-600 ml-2">{gdprStatus}</span>}
      </div>
      <div className="mb-4">
        <button
          className="bg-yellow-500 hover:bg-yellow-600 text-white font-semibold px-4 py-2 rounded disabled:opacity-60"
          onClick={handleCcpaOptout}
          disabled={loading === 'ccpa' || !userId}
        >
          {loading === 'ccpa' ? 'Processing...' : 'Opt Out of Data Sale (CCPA)'}
        </button>
        {ccpaStatus && <span className="text-green-600 ml-2">{ccpaStatus}</span>}
      </div>
      {error && <div className="text-red-600 mt-2">{error}</div>}
    </div>
  );
}
