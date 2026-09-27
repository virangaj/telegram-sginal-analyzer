/**
 * Home page - Signals dashboard
 */

import React, { useEffect } from 'react';
import { Layout } from '@/components/Layout';
import { SignalsList } from '@/components/SignalsList';
import { useAppStore } from '@/lib/store';
import { apiClient } from '@/lib/api';

export default function Home() {
  const { signals, loading, error, setSignals, setLoading, setError } =
    useAppStore();

  useEffect(() => {
    const loadSignals = async () => {
      setLoading(true);
      try {
        const response = await apiClient.getSignals();
        setSignals(response.data);
        setError(null);
      } catch (err) {
        setError('Failed to load signals');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadSignals();

    // Poll for new signals every 30 seconds
    const interval = setInterval(loadSignals, 30000);
    return () => clearInterval(interval);
  }, [setSignals, setLoading, setError]);

  return (
    <Layout title="Signals - Signal Analyzer">
      <div className="space-y-8">
        <div>
          <h2 className="text-3xl font-bold text-white mb-2">Latest Signals</h2>
          <p className="text-slate-400">
            Recent trading signals from configured Telegram channels
          </p>
        </div>

        <SignalsList
          signals={signals}
          isLoading={loading}
          error={error}
        />
      </div>
    </Layout>
  );
}
