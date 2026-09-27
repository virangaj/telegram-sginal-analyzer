/**
 * Signal card component
 */

import React from 'react';
import { Signal } from '@/lib/types';

interface SignalCardProps {
  signal: Signal;
  onClick?: (signal: Signal) => void;
}

export const SignalCard: React.FC<SignalCardProps> = ({ signal, onClick }) => {
  const avgEntry = signal.entries.reduce((a, b) => a + b) / signal.entries.length;
  const avgTp = signal.take_profits.reduce((a, b) => a + b) / signal.take_profits.length;
  const riskReward = Math.abs(avgTp - avgEntry) / Math.abs(avgEntry - signal.stop_loss);

  return (
    <div
      className="p-4 bg-slate-800 border border-slate-700 rounded-lg hover:bg-slate-700 cursor-pointer transition"
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

      <div className="grid grid-cols-2 gap-2 text-sm mb-3">
        <div>
          <p className="text-slate-400">Entry</p>
          <p className="text-white font-mono">
            {signal.entries.map((e) => e.toFixed(2)).join(', ')}
          </p>
        </div>
        <div>
          <p className="text-slate-400">Stop Loss</p>
          <p className="text-white font-mono">{signal.stop_loss.toFixed(2)}</p>
        </div>
        <div>
          <p className="text-slate-400">Take Profits</p>
          <p className="text-white font-mono">
            {signal.take_profits.map((tp) => tp.toFixed(2)).join(', ')}
          </p>
        </div>
        <div>
          <p className="text-slate-400">R/R Ratio</p>
          <p className="text-white font-mono">{riskReward.toFixed(2)}</p>
        </div>
      </div>
    </div>
  );
};
