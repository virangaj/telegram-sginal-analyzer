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
import { ReviewMessage } from '@/lib/types';

export default function Home() {
  const router = useRouter();
  const category = router.query.category === 'crypto' ? 'crypto' : 'cfds';
  const { signals, loading, error, setSignals, setLoading, setError } =
    useAppStore();
  const [action, setAction] = useState<SignalAction | null>(null);
  const [notice, setNotice] = useState('');
  const [reviewMessages, setReviewMessages] = useState<ReviewMessage[]>([]);
  const [reviewError, setReviewError] = useState<string | null>(null);
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
        const [signalResult, reviewResult] = await Promise.allSettled([
          apiClient.getSignals(undefined, 10, category),
          apiClient.getReviewMessages(category),
        ]);
        if (version !== requestVersion.current) return;
        if (signalResult.status === 'fulfilled') {
          setSignals(signalResult.value.data);
          setError(null);
        } else {
          setError('Failed to load signals');
          console.error(signalResult.reason);
        }
        if (reviewResult.status === 'fulfilled') {
          setReviewMessages(reviewResult.value.data);
          setReviewError(null);
        } else {
          setReviewError('Failed to load messages for review');
          console.error(reviewResult.reason);
        }
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
    return () => {
      requestVersion.current += 1;
      clearInterval(interval);
    };
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

        {(reviewMessages.length > 0 || reviewError) && (
          <section aria-labelledby="review-messages-title" className="theme-band border-y py-5">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h3 id="review-messages-title" className="text-lg font-semibold text-white">Messages needing review</h3>
              <span className="rounded border border-amber-300/30 bg-amber-400/10 px-2 py-1 text-xs text-amber-200">{reviewMessages.length}</span>
            </div>
            {reviewError && <p role="alert" className="mb-3 text-sm text-red-300">{reviewError}</p>}
            <ul className="divide-y divide-[var(--glass-border)]">
              {reviewMessages.map((message) => (
                <li key={message.id} className="grid gap-3 py-4 md:grid-cols-[minmax(0,1fr)_220px]">
                  <div className="min-w-0">
                    <pre className="max-h-56 overflow-auto whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-100">{message.raw_text}</pre>
                    <p className="mt-2 text-sm text-amber-200">{message.parse_error || 'Signal needs review'}</p>
                  </div>
                  <div className="text-xs text-slate-400 md:text-right">
                    <span className="block break-words text-slate-200">{message.channel_name}</span>
                    <time className="mt-1 block" dateTime={message.received_at}>{new Date(message.received_at).toLocaleString()}</time>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        )}
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
