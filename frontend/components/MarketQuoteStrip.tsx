import React, { useEffect, useState } from 'react';
import { Radio } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { MarketQuote } from '@/lib/types';

const labels = {
  live: 'Live Quote', stale: 'Stale Quote', closed: 'Market Closed - Last Quote',
  unknown: 'Freshness Unconfirmed', unavailable: 'Quote Unavailable',
};

export function MarketQuoteStrip() {
  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let inFlight = false;
    let active = true;
    const refresh = async () => {
      if (inFlight) return;
      inFlight = true;
      try {
        const response = await apiClient.getMarketSnapshot('XAUUSD');
        if (active) {
          setQuote(response.data);
          setError(false);
        }
      } catch {
        if (active) setError(true);
      } finally {
        inFlight = false;
      }
    };
    refresh();
    const timer = setInterval(refresh, 1000);
    return () => { active = false; clearInterval(timer); };
  }, []);

  const state = error ? (quote?.price != null ? 'stale' : 'unavailable') : quote?.status;
  const price = (value: number | null | undefined) => value == null ? 'Unavailable' : new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 5 }).format(value);

  return (
    <section aria-label="XAU/USD market quote" className="theme-band border-y py-5">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">XAU/USD <span className="ml-2 text-xs font-normal text-slate-400">{quote?.provider ?? 'Biquote'}</span></h2>
          <div className="mt-2 flex flex-wrap items-baseline gap-3"><span className="font-mono text-2xl font-semibold text-white">{quote ? price(quote.price) : error ? 'Unavailable' : 'Loading'}</span><span className="text-xs text-slate-400">Midpoint</span></div>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-300"><Radio size={16} className={state === 'live' ? 'text-emerald-300' : 'text-amber-300'} /><span>{state ? labels[state] : 'Loading Quote'}</span></div>
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3 text-sm sm:grid-cols-4">
        <div><dt className="text-slate-400">Bid</dt><dd className="mt-1 break-words font-mono text-white">{price(quote?.bid)}</dd></div>
        <div><dt className="text-slate-400">Ask</dt><dd className="mt-1 break-words font-mono text-white">{price(quote?.ask)}</dd></div>
        <div className="col-span-2"><dt className="text-slate-400">Quote Time</dt><dd className="mt-1 text-white">{quote?.timestamp ? new Date(quote.timestamp).toLocaleString(undefined, { timeZoneName: 'short' }) : 'Unavailable'}</dd></div>
      </dl>
      {quote?.source && <p className="mt-3 break-words text-xs text-slate-400">Source: {quote.source}</p>}
      {quote?.quote_age_seconds != null && <p className="mt-1 text-xs text-slate-400">Quote age: {Math.floor(quote.quote_age_seconds).toLocaleString()} seconds</p>}
      {(error || quote?.error) && <p role="status" className="mt-3 text-xs text-amber-200">Quote feed temporarily unavailable. Retrying automatically.</p>}
    </section>
  );
}