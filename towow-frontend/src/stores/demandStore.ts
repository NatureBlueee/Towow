import { create } from 'zustand';
import type { DemandState, DemandSubmitRequest, ParsedDemand } from '../types';

interface DemandStore extends DemandState {
  setCurrentDemand: (demand: DemandSubmitRequest | null) => void;
  setParsedDemand: (parsed: ParsedDemand | null) => void;
  setSubmitting: (isSubmitting: boolean) => void;
  setSubmitError: (error: string | null) => void;
  reset: () => void;
}

const initialState: DemandState = {
  currentDemand: null,
  parsedDemand: null,
  isSubmitting: false,
  submitError: null,
};

export const useDemandStore = create<DemandStore>((set) => ({
  ...initialState,

  setCurrentDemand: (demand) => set({ currentDemand: demand }),

  setParsedDemand: (parsed) => set({ parsedDemand: parsed }),

  setSubmitting: (isSubmitting) => set({ isSubmitting }),

  setSubmitError: (error) => set({ submitError: error }),

  reset: () => set(initialState),
}));
