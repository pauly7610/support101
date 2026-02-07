import { useState } from 'react';
import { adminGdprDelete } from '../../../api';
import Card from '../../shared/UI/Card';

export default function AdminCompliancePanel() {
  const [userId, setUserId] = useState('');
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(false);

  async function handleDelete() {
    setLoading(true);
    setError('');
    try {
      const res = await adminGdprDelete(userId, undefined);
      setStatus(res.status || 'User data deleted');
      setUserId('');
      setConfirm(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="mb-6">
      <h2 className="text-xl font-semibold mb-2 text-blue-700">Admin: GDPR User Deletion</h2>
      <div className="flex flex-col md:flex-row items-center gap-4">
        <input
          type="text"
          className="border rounded px-2 py-1 text-sm w-64"
          placeholder="User ID (UUID)"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          disabled={loading}
        />
        {!confirm ? (
          <button
            type="button"
            className="bg-red-600 hover:bg-red-700 text-white font-semibold px-4 py-2 rounded disabled:opacity-60"
            onClick={() => setConfirm(true)}
            disabled={loading || !userId}
          >
            Delete User Data
          </button>
        ) : (
          <>
            <span className="text-red-700 font-bold">Confirm deletion?</span>
            <button
              type="button"
              className="bg-red-700 hover:bg-red-800 text-white font-semibold px-4 py-2 rounded disabled:opacity-60"
              onClick={handleDelete}
              disabled={loading}
            >
              {loading ? 'Deleting...' : 'Yes, Delete'}
            </button>
            <button
              type="button"
              className="bg-gray-200 hover:bg-gray-300 text-gray-700 font-semibold px-4 py-2 rounded"
              onClick={() => setConfirm(false)}
              disabled={loading}
            >
              Cancel
            </button>
          </>
        )}
      </div>
      {status && <div className="text-green-600 mt-2">{status}</div>}
      {error && <div className="text-red-600 mt-2">{error}</div>}
    </Card>
  );
}
