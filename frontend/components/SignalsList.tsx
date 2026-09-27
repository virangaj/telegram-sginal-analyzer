/**
 * Signals list component
 */

import React from 'react';
import { Signal } from '@/lib/types';
import { SignalCard } from './SignalCard';

interface SignalsListProps {
  signals: Signal[];
  isLoading?: boolean;
  error?: string | null;
  onSignalClick?: (signal: Signal) => void;
}

export const SignalsList: React.FC<SignalsListProps> = ({
  signals,
  isLoading = false,
  error = null,
  onSignalClick,
}) => {
  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-slate-400">Loading signals...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-900 text-red-200 rounded-lg">
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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {signals.map((signal) => (
        <SignalCard
          key={signal.id}
          signal={signal}
          onClick={onSignalClick}
        />
      ))}
    </div>
  );
};
