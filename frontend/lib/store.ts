/**
 * State management store for the application
 */

import { create } from 'zustand';
import { Signal } from './types';

interface AppState {
  signals: Signal[];
  loading: boolean;
  error: string | null;

  // Actions
  setSignals: (signals: Signal[]) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  signals: [],
  loading: false,
  error: null,

  setSignals: (signals) => set({ signals }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
}));
