import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Loader2, Save, Trash2, X } from 'lucide-react';
import { Signal } from '@/lib/types';

export type SignalPrices = Pick<Signal, 'entries' | 'stop_loss' | 'take_profits'>;
export type SignalAction = { kind: 'edit' | 'delete'; signal: Signal } | { kind: 'deleteAll' };

interface Props {
  action: SignalAction;
  onClose: () => void;
  onSave: (id: number, prices: SignalPrices) => Promise<void>;
  onDelete: (id?: number) => Promise<void>;
}

function parsePrices(value: string, field: string): number[] {
  const parts = value.split(',').map((part) => part.trim());
  const prices = parts.map(Number);
  if (parts.some((part) => part === '') || prices.some((price) => !Number.isFinite(price) || price <= 0)) {
    throw new Error(`${field} must contain positive prices separated by commas.`);
  }
  return prices;
}

export function SignalManagementDialog({ action, onClose, onSave, onDelete }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const signal = action.kind === 'deleteAll' ? null : action.signal;
  const [entries, setEntries] = useState(signal?.entries.join(', ') ?? '');
  const [stopLoss, setStopLoss] = useState(signal?.stop_loss.toString() ?? '');
  const [targets, setTargets] = useState(signal?.take_profits.join(', ') ?? '');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const editing = action.kind === 'edit';

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      if (editing && signal) {
        const prices = {
          entries: parsePrices(entries, 'Entry prices'),
          stop_loss: Number(stopLoss),
          take_profits: parsePrices(targets, 'Take-profit prices'),
        };
        if (!Number.isFinite(prices.stop_loss) || prices.stop_loss <= 0) throw new Error('Stop loss must be a positive price.');
        const valid = signal.direction === 'BUY'
          ? prices.stop_loss < Math.min(...prices.entries) && prices.take_profits.every((target) => target > Math.max(...prices.entries))
          : prices.stop_loss > Math.max(...prices.entries) && prices.take_profits.every((target) => target < Math.min(...prices.entries));
        if (!valid) throw new Error('Stop loss and targets must be on the correct side of every entry.');
        await onSave(signal.id, prices);
      } else {
        await onDelete(signal?.id);
      }
      onClose();
    } catch (failure) {
      const detail = axios.isAxiosError(failure) ? failure.response?.data?.detail : null;
      setError(typeof detail === 'string' ? detail : failure instanceof Error ? failure.message : 'Unable to complete the request.');
      setPending(false);
    }
  }

  return (
    <dialog ref={dialogRef} aria-labelledby="signal-dialog-title" onCancel={(event) => { event.preventDefault(); if (!pending) onClose(); }} className="m-auto w-[calc(100%_-_2rem)] max-w-lg max-h-[90dvh] overflow-y-auto rounded-lg border border-blue-200/30 bg-[#12244b] p-0 text-slate-200 shadow-2xl backdrop:bg-[#050d24]/80 backdrop:backdrop-blur-sm">
      <form onSubmit={submit} className="space-y-5 p-5 sm:p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="signal-dialog-title" className="text-xl font-semibold text-white">{editing ? 'Edit Prices' : action.kind === 'deleteAll' ? 'Delete All Signals?' : 'Delete Signal?'}</h2>
            {signal && <p className="mt-1 text-sm text-slate-400">{signal.symbol} | {signal.direction} | #{signal.id}</p>}
          </div>
          <button type="button" title="Close" aria-label="Close signal dialog" disabled={pending} onClick={onClose} className="glass-icon-button flex h-9 w-9 shrink-0 items-center justify-center disabled:opacity-50"><X size={18} /></button>
        </div>
        {error && <div role="alert" className="rounded-md border border-red-400/30 bg-red-950/30 p-3 text-sm text-red-200">{error}</div>}
        {editing ? <fieldset disabled={pending} className="space-y-4">
          <div><label htmlFor="signal-entries" className="mb-2 block text-sm">Entry Prices</label><input id="signal-entries" type="text" required autoFocus value={entries} onChange={(event) => setEntries(event.target.value)} className="glass-input" /></div>
          <div><label htmlFor="signal-stop-loss" className="mb-2 block text-sm">Stop Loss</label><input id="signal-stop-loss" type="number" step="any" min="0" required value={stopLoss} onChange={(event) => setStopLoss(event.target.value)} className="glass-input" /></div>
          <div><label htmlFor="signal-targets" className="mb-2 block text-sm">Take-Profit Prices</label><input id="signal-targets" type="text" required value={targets} onChange={(event) => setTargets(event.target.value)} className="glass-input" /></div>
        </fieldset> : <p className="text-sm leading-relaxed text-slate-300">{action.kind === 'deleteAll' ? 'All stored signals and their related analysis and trade records will be permanently deleted.' : 'This signal and its related analysis and trade records will be permanently deleted.'} Raw Telegram messages and channels will remain.</p>}
        <div className="flex flex-wrap justify-end gap-3 border-t border-blue-200/15 pt-4">
          <button type="button" disabled={pending} onClick={onClose} className="rounded-md border border-blue-200/25 px-4 py-2 text-sm disabled:opacity-50">Cancel</button>
          <button type="submit" disabled={pending} className={`flex items-center gap-2 rounded-md px-4 py-2 text-sm font-semibold text-white disabled:opacity-50 ${editing ? 'glass-primary-button' : 'border border-red-300/30 bg-red-700 hover:bg-red-600'}`}>
            {pending ? <Loader2 size={16} className="animate-spin" /> : editing ? <Save size={16} /> : <Trash2 size={16} />}
            {pending ? (editing ? 'Saving' : 'Deleting') : editing ? 'Save Changes' : action.kind === 'deleteAll' ? 'Delete All' : 'Delete Signal'}
          </button>
        </div>
      </form>
    </dialog>
  );
}