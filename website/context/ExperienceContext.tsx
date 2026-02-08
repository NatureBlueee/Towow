'use client';

import { createContext, useContext, useReducer, ReactNode } from 'react';
import { User, Requirement, NegotiationMessage, ExperienceState } from '@/types/experience';

interface ExperienceContextState {
  user: User | null;
  isLoading: boolean;
  state: ExperienceState;
  currentRequirement: Requirement | null;
  messages: NegotiationMessage[];
  error: Error | null;
}

type Action =
  | { type: 'SET_USER'; payload: User | null }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_STATE'; payload: ExperienceState }
  | { type: 'SET_REQUIREMENT'; payload: Requirement | null }
  | { type: 'ADD_MESSAGE'; payload: NegotiationMessage }
  | { type: 'CLEAR_MESSAGES' }
  | { type: 'SET_ERROR'; payload: Error | null };

const initialState: ExperienceContextState = {
  user: null,
  isLoading: true,
  state: 'INIT',
  currentRequirement: null,
  messages: [],
  error: null,
};

function reducer(state: ExperienceContextState, action: Action): ExperienceContextState {
  switch (action.type) {
    case 'SET_USER':
      return { ...state, user: action.payload };
    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };
    case 'SET_STATE':
      return { ...state, state: action.payload };
    case 'SET_REQUIREMENT':
      return { ...state, currentRequirement: action.payload };
    case 'ADD_MESSAGE':
      // Deduplicate: only add if message_id doesn't exist
      if (state.messages.some(m => m.message_id === action.payload.message_id)) {
        return state;
      }
      return { ...state, messages: [...state.messages, action.payload] };
    case 'CLEAR_MESSAGES':
      return { ...state, messages: [] };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    default:
      return state;
  }
}

const ExperienceContext = createContext<{
  state: ExperienceContextState;
  dispatch: React.Dispatch<Action>;
} | null>(null);

export function ExperienceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <ExperienceContext.Provider value={{ state, dispatch }}>
      {children}
    </ExperienceContext.Provider>
  );
}

export function useExperienceContext() {
  const context = useContext(ExperienceContext);
  if (!context) {
    throw new Error('useExperienceContext must be used within ExperienceProvider');
  }
  return context;
}
