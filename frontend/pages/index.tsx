/**
 * Home page - Signals dashboard
 */

import React, { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/router';
import { Trash2 } from 'lucide-react';
import { Layout } from '@/components/Layout';
import { SignalsList } from '@/components/SignalsList';
import { useAppStore } from '@/lib/store';
import { apiClient } from '@/lib/api';
import { SignalManagementDialog, SignalAction, SignalPrices } from '@/components/SignalManagementDialog';
import { MarketQuoteStrip } from '@/components/MarketQuoteStrip';

export default function Home() {
  const router = useRouter();
  const category = router.query.category === 'crypto' ? 'crypto' : 'cfds';
  const { signals, loading, error, setSignals, setLoading, setError } =
    useAppStore();
  const [action, setAction] = useState<SignalAction | null>(null);
  const [notice, setNotice] = useState('');
  const pollPaused = useRef(false);
  const requestVersion = useRef(0);
  pollPaused.current = action !== null;

  async function saveSignal(id: number, prices: SignalPrices) {
    requestVersion.current += 1;
    const response = await apiClient.updateSignal(id, prices);
    setSignals(useAppStore.getState().signals.map((signal) => signal.id === id ? response.data : signal));
    setNotice(`Signal #${id} updated`);
  }

  async function sendSignal(id: number) {
    await apiClient.publishSignal(id);
    setNotice(`Signal #${id} sent to Telegram`);
  }

  async function deleteSignals(id?: number, deletePublished = false) {
    requestVersion.current += 1;
    const response = id === undefined ? await apiClient.deleteAllSignals(true, deletePublished) : await apiClient.deleteSignal(id, deletePublished);
    setSignals(id === undefined ? [] : useAppStore.getState().signals.filter((signal) => signal.id !== id));
    setNotice(`${response.data.deleted} signal${response.data.deleted === 1 ? '' : 's'} deleted`);
  }

  useEffect(() => {
    let requestInFlight = false;
    const loadSignals = async () => {
      if (pollPaused.current || requestInFlight) return;
      requestInFlight = true;
      const version = requestVersion.current;
      try {
        const response = await apiClient.getSignals(undefined, 10, category);
        if (version !== requestVersion.current) return;
        setSignals(response.data);
        setError(null);
      } catch (err) {
        if (version !== requestVersion.current) return;
        setError('Failed to load signals');
        console.error(err);
      } finally {
        requestInFlight = false;
        setLoading(false);
      }
    };

    setLoading(true);
    loadSignals();

    const interval = setInterval(loadSignals, 1000);
    return () => clearInterval(interval);
  }, [category, setSignals, setLoading, setError]);

  return (
    <Layout title={`${category === 'crypto' ? 'Crypto' : 'CFDs'} - Signal Analyzer`}>
      <div className="space-y-8">
        <MarketQuoteStrip />
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
          <h2 className="text-3xl font-bold text-white mb-2">{category === 'crypto' ? 'Crypto Signals' : 'CFD Signals'}</h2>
          <p className="text-slate-400">
            Recent signals from Telegram channels categorized as {category === 'crypto' ? 'crypto' : 'CFDs'}
          </p>
          </div>
          <button type="button" disabled={loading || signals.length === 0 || action !== null} onClick={() => setAction({ kind: 'deleteAll' })} className="glass-icon-button flex items-center gap-2 px-3 py-2 text-sm !text-red-300 disabled:opacity-40"><Trash2 size={16} />Delete All</button>
        </div>
        <div role="status" aria-live="polite" className="min-h-5 text-sm text-emerald-300">{notice}</div>

        <SignalsList
          signals={signals}
          isLoading={loading}
          error={error}
          onEditSignal={(signal) => setAction({ kind: 'edit', signal })}
          onDeleteSignal={(signal) => setAction({ kind: 'delete', signal })}
          onSendSignal={(signal) => setAction({ kind: 'send', signal })}
        />
      </div>
      {action && <SignalManagementDialog action={action} onClose={() => setAction(null)} onSave={saveSignal} onDelete={deleteSignals} onSend={sendSignal} />}
    </Layout>
  );
}
