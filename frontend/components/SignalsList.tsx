/**
 * Signals list component
 */

import React from 'react';
import { Pencil, Send, Trash2 } from 'lucide-react';
import { Signal } from '@/lib/types';

const priceFormat = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8, useGrouping: false });

function formatPrice(price: number): string {
  return Number.isFinite(price) && price > 0 ? priceFormat.format(price) : 'Unavailable';
}

function plannedRatio(signal: Signal, target: number): string {
  if (!signal.entries.length || signal.entries.some((price) => !Number.isFinite(price) || price <= 0)) return 'Unavailable';
  const entry = signal.entries.reduce((total, price) => total + price, 0) / signal.entries.length;
  const direction = signal.direction === 'BUY' ? 1 : signal.direction === 'SELL' ? -1 : 0;
  const risk = direction * (entry - signal.stop_loss);
  const reward = direction * (target - entry);
  if (!direction || !Number.isFinite(risk) || !Number.isFinite(reward) || risk <= 0 || reward <= 0) return 'Unavailable';
  return `1:${(reward / risk).toFixed(2)}`;
}

function statusStyle(status: string): string {
  switch (status.toLowerCase()) {
    case 'success': return 'border-emerald-300/30 bg-emerald-400/10 text-emerald-200';
    case 'failed': return 'border-red-300/30 bg-red-400/10 text-red-200';
    case 'active': return 'border-sky-300/30 bg-sky-400/10 text-sky-200';
    case 'pending': return 'border-amber-300/30 bg-amber-400/10 text-amber-200';
    default: return 'border-slate-300/20 bg-slate-400/10 text-slate-300';
  }
}

interface SignalsListProps {
  signals: Signal[];
  isLoading?: boolean;
  error?: string | null;
  onSignalClick?: (signal: Signal) => void;
  onEditSignal?: (signal: Signal) => void;
  onDeleteSignal?: (signal: Signal) => void;
  onSendSignal?: (signal: Signal) => void;
}

export const SignalsList: React.FC<SignalsListProps> = ({
  signals,
  isLoading = false,
  error = null,
  onSignalClick,
  onEditSignal,
  onDeleteSignal,
  onSendSignal,
}) => {
  if (isLoading) {
    return (
      <div role="status" className="flex justify-center items-center h-64">
        <div className="text-slate-400">Loading signals...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div role="alert" className="p-4 bg-red-900 text-red-200 rounded-lg">
        <p className="font-semibold">Error loading signals</p>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (signals.length === 0) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-slate-400">No signals yet</div>
      </div>
    );
  }

  return (
    <div role="region" aria-label="Signals table" tabIndex={0} className="theme-band max-w-full overflow-x-auto border-y focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--glass-accent)]">
      <table className="w-full min-w-[1050px] border-collapse text-left text-sm">
        <caption className="sr-only">Trading signals with entry prices, stop loss, take profits, planned reward-to-risk, stored status, and source channel</caption>
        <thead className="theme-table-head text-xs text-slate-300">
          <tr>
            <th scope="col" className="px-4 py-3 font-medium">Signal No.</th>
            <th scope="col" className="px-4 py-3 font-medium">Signal</th>
            <th scope="col" className="px-4 py-3 font-medium">Direction</th>
            <th scope="col" className="px-4 py-3 font-medium">Entry</th>
            <th scope="col" className="px-4 py-3 font-medium">SL</th>
            <th scope="col" className="px-4 py-3 font-medium">TP</th>
            <th scope="col" title="Per-target planned reward-to-risk using the average listed entry; not realized execution results" className="px-4 py-3 font-medium">Planned R:R</th>
            <th scope="col" className="px-4 py-3 font-medium">Status</th>
            <th scope="col" className="px-4 py-3 font-medium">Source</th>
            <th scope="col" className="px-4 py-3 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          {signals.map((signal) => (
            <tr key={signal.id} className="theme-table-row border-t align-top transition-colors">
              <td className="px-4 py-4 font-mono text-slate-300">#{signal.id}</td>
              <th scope="row" className="px-4 py-4 font-normal">
                {onSignalClick ? <button type="button" onClick={() => onSignalClick(signal)} className="font-semibold text-sky-200 hover:underline">{signal.symbol}</button> : <span className="font-semibold text-white">{signal.symbol}</span>}
                <time dateTime={signal.created_at} className="mt-1 block whitespace-nowrap text-xs text-slate-400">{new Date(signal.created_at).toLocaleString()}</time>
              </th>
              <td className="px-4 py-4"><span className={signal.direction === 'BUY' ? 'font-semibold text-emerald-300' : 'font-semibold text-red-300'}>{signal.direction}</span><div className="mt-1 text-xs text-slate-400">{signal.order_type}</div></td>
              <td className="px-4 py-4 font-mono text-white"><div className="space-y-1">{signal.entries.length ? signal.entries.map((price, index) => <div key={index}>{formatPrice(price)}</div>) : 'Unavailable'}</div></td>
              <td className="px-4 py-4 font-mono text-white">{formatPrice(signal.stop_loss)}</td>
              <td className="px-4 py-4"><div className="space-y-1">{signal.take_profits.length ? signal.take_profits.map((price, index) => <div key={index} className="whitespace-nowrap"><span className="mr-2 text-xs text-slate-400">TP{index + 1}</span><span className="font-mono text-white">{formatPrice(price)}</span></div>) : 'Unavailable'}</div></td>
              <td className="px-4 py-4"><div className="space-y-1">{signal.take_profits.length ? signal.take_profits.map((price, index) => <div key={index} className="whitespace-nowrap"><span className="mr-2 text-xs text-slate-400">TP{index + 1}</span><span className="font-mono text-white">{plannedRatio(signal, price)}</span></div>) : 'Unavailable'}</div></td>
              <td className="px-4 py-4"><span className={`inline-block whitespace-nowrap rounded border px-2 py-1 text-xs font-medium ${statusStyle(signal.status)}`}>{signal.status ? signal.status.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) : 'Unknown'}</span></td>
              <td className="max-w-[220px] px-4 py-4"><span className="break-words text-slate-200">{signal.channel_name || `Channel #${signal.channel_id}`}</span></td>
              <td className="px-4 py-4"><div className="flex justify-end gap-2">
                {onSendSignal && <button type="button" title="Send to Telegram" aria-label={`Send signal ${signal.id} to Telegram`} onClick={() => onSendSignal(signal)} className="glass-icon-button flex h-9 w-9 shrink-0 items-center justify-center"><Send size={16} /></button>}
                {onEditSignal && <button type="button" title="Edit signal prices" aria-label={`Edit signal ${signal.id}`} onClick={() => onEditSignal(signal)} className="glass-icon-button flex h-9 w-9 shrink-0 items-center justify-center"><Pencil size={16} /></button>}
                {onDeleteSignal && <button type="button" title="Delete signal" aria-label={`Delete signal ${signal.id}`} onClick={() => onDeleteSignal(signal)} className="glass-icon-button flex h-9 w-9 shrink-0 items-center justify-center !text-red-300"><Trash2 size={16} /></button>}
              </div></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
