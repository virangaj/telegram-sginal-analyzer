import React, { useEffect, useRef, useState } from 'react';
import { HubConnectionBuilder, HubConnectionState, LogLevel } from '@microsoft/signalr';
import { Plus, Radio, Search, X } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { MarketSymbol, Signal } from '@/lib/types';

type QuoteCategory = 'crypto' | 'cfds';
type ConnectionStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'unavailable';

interface BiquoteTick {
  symbol: string;
  bid: number;
  ask: number;
  mid?: number;
  timestamp?: string | number;
  time?: string | number;
  source?: string;
  digits?: number;
}

interface ReceivedTick {
  tick: BiquoteTick;
  receivedAt: string;
}

const DEFAULT_SYMBOLS: Record<QuoteCategory, string[]> = {
  cfds: ['EURUSD', 'XAUUSD'],
  crypto: ['BTCUSD'],
};
const HUB_URL = process.env.NEXT_PUBLIC_BIQUOTE_HUB_URL || 'https://biquote.io/hubs/tick';
const MAX_WATCHLIST_SYMBOLS = 30;

function watchlistKey(category: QuoteCategory): string {
  return `signal-analyzer.watchlist.${category}`;
}

function processedSignalsKey(category: QuoteCategory): string {
  return `signal-analyzer.watchlist-signals.${category}`;
}

function loadStringArray(key: string): string[] | null {
  try {
    const stored = localStorage.getItem(key);
    if (stored === null) return null;
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed.filter((value): value is string => typeof value === 'string') : [];
  } catch {
    return [];
  }
}

function loadSignalIds(key: string): number[] {
  try {
    const stored = localStorage.getItem(key);
    if (stored === null) return [];
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed.map(Number).filter(Number.isFinite) : [];
  } catch {
    return [];
  }
}

function normalizeTick(payload: unknown, allowedSymbols: Set<string>): BiquoteTick | null {
  if (!payload || typeof payload !== 'object') return null;
  const data = payload as Record<string, unknown>;
  const symbol = String(data.symbol ?? data.Symbol ?? '').toUpperCase();
  const bid = Number(data.bid ?? data.Bid);
  const ask = Number(data.ask ?? data.Ask);
  if (!allowedSymbols.has(symbol) || !Number.isFinite(bid) || !Number.isFinite(ask) || bid <= 0 || ask < bid) return null;
  const midValue = Number(data.mid ?? data.Mid);
  const timestamp = data.timestamp ?? data.Timestamp;
  const time = data.time ?? data.Time;
  const digits = Number(data.digits ?? data.Digits);
  return {
    symbol,
    bid,
    ask,
    mid: Number.isFinite(midValue) && midValue > 0 ? midValue : (bid + ask) / 2,
    timestamp: typeof timestamp === 'string' || typeof timestamp === 'number' ? timestamp : undefined,
    time: typeof time === 'string' || typeof time === 'number' ? time : undefined,
    source: typeof data.source === 'string' ? data.source : typeof data.Source === 'string' ? data.Source : 'Biquote SignalR',
    digits: Number.isInteger(digits) && digits >= 0 && digits <= 10 ? digits : undefined,
  };
}

function formatPrice(value: number, symbol: string, digits?: number): string {
  const fractionDigits = digits ?? (symbol.endsWith('JPY') ? 3 : symbol === 'BTCUSD' ? 2 : symbol.startsWith('XAU') ? 2 : 5);
  return new Intl.NumberFormat(undefined, { minimumFractionDigits: fractionDigits, maximumFractionDigits: fractionDigits }).format(value);
}

function tickTime(tick: BiquoteTick, receivedAt: string): string {
  const providerTime = tick.timestamp ?? tick.time;
  const date = providerTime === undefined ? null : new Date(providerTime);
  const time = date && Number.isFinite(date.getTime()) ? date : new Date(receivedAt);
  return time.toLocaleString(undefined, { timeZoneName: 'short' });
}

const connectionLabels: Record<ConnectionStatus, string> = {
  idle: 'No symbols selected',
  connecting: 'Connecting to Biquote',
  connected: 'SignalR connected',
  reconnecting: 'Reconnecting',
  unavailable: 'Live feed unavailable',
};

export function MarketQuoteStrip({ category, signals }: { category: QuoteCategory; signals: Signal[] }) {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [watchlistReady, setWatchlistReady] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState<MarketSymbol[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState('');
  const [quotes, setQuotes] = useState<Record<string, ReceivedTick>>({});
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const processedSignalIds = useRef<Set<number>>(new Set());

  useEffect(() => {
    const savedSymbols = loadStringArray(watchlistKey(category));
    setSymbols(savedSymbols === null ? DEFAULT_SYMBOLS[category] : [...new Set(savedSymbols.map((symbol) => symbol.toUpperCase()))]);
    processedSignalIds.current = new Set(loadSignalIds(processedSignalsKey(category)));
    setWatchlistReady(true);
  }, [category]);

  useEffect(() => {
    if (!watchlistReady) return;
    const newSignals = signals.filter((signal) => signal.category === category && !processedSignalIds.current.has(signal.id));
    if (!newSignals.length) return;
    for (const signal of newSignals) processedSignalIds.current.add(signal.id);
    try {
      localStorage.setItem(processedSignalsKey(category), JSON.stringify([...processedSignalIds.current]));
    } catch {
      setSearchError('Signal pairs could not be saved to this browser.');
    }
    const signalSymbols = [...new Set(newSignals.map((signal) => signal.symbol.trim().toUpperCase()).filter((symbol) => /^[A-Z0-9._-]{2,24}$/.test(symbol)))];
    if (!signalSymbols.length) return;
    setSymbols((current) => {
      const next = [...current];
      for (const symbol of signalSymbols) {
        if (!next.includes(symbol) && next.length < MAX_WATCHLIST_SYMBOLS) next.push(symbol);
      }
      if (next.length !== current.length) {
        try {
          localStorage.setItem(watchlistKey(category), JSON.stringify(next));
        } catch {
          setSearchError('Signal pairs could not be saved to this browser.');
        }
        return next;
      }
      return current;
    });
  }, [category, signals, watchlistReady]);

  useEffect(() => {
    const query = searchText.trim();
    if (query.length < 2) {
      setSearchResults([]);
      setSearching(false);
      setSearchError('');
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      setSearching(true);
      setSearchError('');
      apiClient.searchMarketSymbols(query, category, 10).then(({ data }) => {
        if (active) setSearchResults(data);
      }).catch(() => {
        if (active) {
          setSearchResults([]);
          setSearchError('Symbol search is temporarily unavailable.');
        }
      }).finally(() => {
        if (active) setSearching(false);
      });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [category, searchText]);

  useEffect(() => {
    if (!watchlistReady) return;
    if (symbols.length === 0) {
      setStatus('idle');
      return;
    }
    let stopped = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;
    let pendingStart: Promise<void> | null = null;
    const allowedSymbols = new Set(symbols);
    const connection = new HubConnectionBuilder()
      .withUrl(HUB_URL, { withCredentials: false })
      .withAutomaticReconnect([0, 2000, 10000, 30000])
      .configureLogging(LogLevel.Warning)
      .build();

    const schedule = (task: () => void) => {
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(task, 5000);
    };

    const subscribe = async () => {
      if (stopped) return;
      try {
        await connection.invoke('Subscribe', symbols);
        if (!stopped) setStatus('connected');
      } catch {
        if (!stopped) {
          setStatus('unavailable');
          schedule(() => { void subscribe(); });
        }
      }
    };

    const start = async () => {
      if (stopped || connection.state !== HubConnectionState.Disconnected) return;
      setStatus('connecting');
      try {
        pendingStart = connection.start();
        await pendingStart;
        pendingStart = null;
        if (stopped) {
          await connection.stop();
          return;
        }
        await subscribe();
      } catch {
        pendingStart = null;
        if (!stopped) {
          setStatus('unavailable');
          schedule(() => { void start(); });
        }
      }
    };

    connection.on('ReceiveTick', (payload: unknown) => {
      const tick = normalizeTick(payload, allowedSymbols);
      if (!tick || stopped) return;
      setQuotes((current) => ({ ...current, [tick.symbol]: { tick, receivedAt: new Date().toISOString() } }));
    });
    connection.on('ReceiveSubscriptionState', () => {
      if (!stopped && connection.state === HubConnectionState.Connected) setStatus('connected');
    });
    connection.onreconnecting(() => {
      if (!stopped) setStatus('reconnecting');
    });
    connection.onreconnected(() => {
      if (!stopped) void subscribe();
    });
    connection.onclose(() => {
      if (stopped) return;
      setStatus('unavailable');
      schedule(() => { void start(); });
    });

    void start();
    return () => {
      stopped = true;
      if (retryTimer) clearTimeout(retryTimer);
      connection.off('ReceiveTick');
      connection.off('ReceiveSubscriptionState');
      void (async () => {
        if (pendingStart) await pendingStart.catch(() => undefined);
        await connection.stop();
      })();
    };
  }, [symbols, watchlistReady]);

  function saveSymbols(next: string[]) {
    setSymbols(next);
    try {
      localStorage.setItem(watchlistKey(category), JSON.stringify(next));
    } catch {
      setSearchError('Watchlist could not be saved to this browser.');
    }
  }

  function addSymbol(symbol: string) {
    const normalized = symbol.trim().toUpperCase();
    if (!normalized || symbols.includes(normalized)) return;
    if (symbols.length >= MAX_WATCHLIST_SYMBOLS) {
      setSearchError(`Watchlist limit reached (${MAX_WATCHLIST_SYMBOLS} symbols).`);
      return;
    }
    saveSymbols([...symbols, normalized]);
    setSearchText('');
    setSearchResults([]);
    setSearchError('');
  }

  function removeSymbol(symbol: string) {
    saveSymbols(symbols.filter((item) => item !== symbol));
    setQuotes((current) => {
      const next = { ...current };
      delete next[symbol];
      return next;
    });
  }

  const title = category === 'crypto' ? 'Crypto Watchlist' : 'CFD Watchlist';
  const statusColor = status === 'connected' ? 'text-emerald-300' : status === 'idle' ? 'text-slate-400' : 'text-amber-300';

  return (
    <section aria-label={title} className="theme-band border-y py-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-white">{title}<span className="ml-2 text-xs font-normal text-slate-400">Biquote SignalR</span></h2>
          <p className="mt-1 text-xs text-slate-400">Pairs from signals are added automatically; your choices are saved in this browser.</p>
        </div>
        <div className={`flex items-center gap-2 text-sm ${statusColor}`} role="status" aria-live="polite">
          <Radio size={16} aria-hidden="true" />{connectionLabels[status]}
        </div>
      </div>

      <div className="grid gap-4">
        <div className="min-w-0 divide-y divide-[var(--glass-border)] border-y border-[var(--glass-border)]">
          {symbols.map((symbol) => {
            const quote = quotes[symbol];
            return (
              <article key={symbol} className="grid gap-3 py-4 sm:grid-cols-[minmax(105px,0.8fr)_minmax(0,1fr)_36px] sm:items-center">
                <div className="min-w-0">
                  <h3 className="truncate font-semibold text-white">{symbol}</h3>
                  <p className="mt-1 text-xs text-slate-400">{quote ? 'Live tick' : status === 'connected' ? 'Waiting for first tick' : 'No tick received'}</p>
                </div>
                <div><dt className="text-xs text-slate-400">Midpoint</dt><dd className="mt-1 break-words font-mono text-sm text-white">{quote ? formatPrice(quote.tick.mid ?? (quote.tick.bid + quote.tick.ask) / 2, symbol, quote.tick.digits) : '—'}</dd></div>
                <button type="button" onClick={() => removeSymbol(symbol)} className="glass-icon-button flex h-9 w-9 items-center justify-center justify-self-end" title={`Remove ${symbol}`} aria-label={`Remove ${symbol} from watchlist`}><X size={15} /></button>
                {quote && <p className="text-xs text-slate-400 sm:col-span-3">Tick time: {tickTime(quote.tick, quote.receivedAt)} · Source: {quote.tick.source}</p>}
              </article>
            );
          })}
          {symbols.length === 0 && <p className="py-8 text-center text-sm text-slate-400">Search for a pair to start your watchlist.</p>}
        </div>

        <div className="relative min-w-0">
          <label htmlFor={`symbol-search-${category}`} className="mb-2 block text-xs text-slate-400">Add a {category === 'crypto' ? 'crypto' : 'forex or CFD'} pair</label>
          <div className="relative">
            <Search size={16} className="pointer-events-none absolute left-3 top-3 text-slate-400" aria-hidden="true" />
            <input
              id={`symbol-search-${category}`}
              className="glass-input !pl-10"
              type="text"
              role="searchbox"
              autoComplete="off"
              value={searchText}
              onChange={(event) => setSearchText(event.target.value)}
              placeholder={category === 'crypto' ? 'Search BTCUSD, BTCUSDT…' : 'Search EURUSD, XAUUSD…'}
            />
          </div>
          {searching && <p role="status" className="mt-2 text-xs text-slate-400">Searching provider symbols…</p>}
          {searchError && <p role="alert" className="mt-2 text-xs text-amber-200">{searchError}</p>}
          {!searching && searchText.trim().length >= 2 && !searchError && searchResults.length === 0 && <p className="mt-2 text-xs text-slate-400">No matching provider symbols.</p>}
          {searchResults.length > 0 && (
            <ul aria-label="Symbol search results" className="mt-2 max-h-64 divide-y divide-[var(--glass-border)] overflow-y-auto border border-[var(--glass-border)] bg-[var(--glass-surface)]">
              {searchResults.map((result) => {
                const selected = symbols.includes(result.name.toUpperCase());
                return (
                  <li key={`${result.name}-${result.exchange ?? ''}`}>
                    <button type="button" disabled={selected} onClick={() => addSymbol(result.name)} className="flex w-full items-center justify-between gap-3 px-3 py-3 text-left hover:bg-white/5 disabled:opacity-50">
                      <span className="min-w-0"><span className="mr-2 font-semibold text-[var(--glass-accent)]">{result.name}</span><span className="block truncate text-xs text-slate-400 sm:inline">{result.description}</span></span>
                      <span className="flex shrink-0 items-center gap-2 text-[10px] uppercase text-slate-500">{selected ? 'Added' : result.type}<Plus size={14} /></span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <p className="mt-3 text-xs text-slate-500">{symbols.length}/{MAX_WATCHLIST_SYMBOLS} symbols · Source: Biquote</p>
        </div>
      </div>
      {status === 'unavailable' && <p className="mt-3 text-xs text-amber-200">Waiting for the live connection. No REST quote fallback is used.</p>}
    </section>
  );
}