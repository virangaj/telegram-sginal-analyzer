/**
 * Signal card component
 */

import React from 'react';
import { Pencil, Radio, Trash2 } from 'lucide-react';
import { Signal } from '@/lib/types';

interface SignalCardProps {
  signal: Signal;
  onClick?: (signal: Signal) => void;
  onEdit?: (signal: Signal) => void;
  onDelete?: (signal: Signal) => void;
}

export const SignalCard: React.FC<SignalCardProps> = ({ signal, onClick, onEdit, onDelete }) => {
  const avgEntry = signal.entries.reduce((total, price) => total + price, 0) / signal.entries.length;
  const avgTp = signal.take_profits.reduce((total, price) => total + price, 0) / signal.take_profits.length;
  const riskReward = Math.abs(avgTp - avgEntry) / Math.abs(avgEntry - signal.stop_loss);
  const priceFormat = new Intl.NumberFormat('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8, useGrouping: false });

  return (
    <div
      className="glass-surface p-4 hover:border-blue-300/50 cursor-pointer transition"
      onClick={() => onClick?.(signal)}
    >
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="text-lg font-bold text-white">{signal.symbol}</h3>
          <p className="text-sm text-slate-400">
            {new Date(signal.created_at).toLocaleString()}
          </p>
        </div>
        <span
          className={`px-2 py-1 rounded text-sm font-semibold ${
            signal.direction === 'BUY'
              ? 'bg-green-900 text-green-200'
              : 'bg-red-900 text-red-200'
          }`}
        >
          {signal.direction} {signal.order_type}
        </span>
      </div>

      <div className="mb-4 flex min-w-0 items-start gap-2 text-sm text-slate-400">
        <Radio size={15} aria-hidden="true" className="mt-0.5 shrink-0 text-sky-300" />
        <span className="min-w-0 break-words"><span className="text-slate-500">Channel: </span>{signal.channel_name || `Channel #${signal.channel_id}`}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div>
          <p className="text-slate-400">Entry</p>
          <p className="break-words text-white font-mono">
            {signal.entries.map((price) => priceFormat.format(price)).join(', ') || 'Unavailable'}
          </p>
        </div>
        <div>
          <p className="text-slate-400">Stop Loss</p>
          <p className="break-words text-white font-mono">{priceFormat.format(signal.stop_loss)}</p>
        </div>
        <div>
          <p className="text-slate-400">Take Profits</p>
          <p className="break-words text-white font-mono">
            {signal.take_profits.map((price) => priceFormat.format(price)).join(', ') || 'Unavailable'}
          </p>
        </div>
        <div>
          <p className="text-slate-400">R/R Ratio</p>
          <p className="text-white font-mono">{Number.isFinite(riskReward) ? riskReward.toFixed(2) : 'Unavailable'}</p>
        </div>
      </div>
      <div className="flex items-center justify-between gap-3 border-t border-blue-200/15 pt-3" onClick={(event) => event.stopPropagation()}>
        <span className="text-xs text-slate-400">Signal #{signal.id}</span>
        <div className="flex gap-2">
          {onEdit && <button type="button" title="Edit signal prices" aria-label={`Edit signal ${signal.id}`} onClick={() => onEdit(signal)} className="glass-icon-button flex h-9 w-9 items-center justify-center"><Pencil size={16} /></button>}
          {onDelete && <button type="button" title="Delete signal" aria-label={`Delete signal ${signal.id}`} onClick={() => onDelete(signal)} className="glass-icon-button flex h-9 w-9 items-center justify-center !text-red-300"><Trash2 size={16} /></button>}
        </div>
      </div>
    </div>
  );
};
