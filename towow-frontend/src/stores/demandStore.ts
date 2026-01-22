import { create } from 'zustand';
import { demandApi } from '../api/demand';
import type { DemandState, DemandSubmitRequest, ParsedDemand, DemandSubmitResponse } from '../types';

interface DemandStore extends DemandState {
  setCurrentDemand: (demand: DemandSubmitRequest | null) => void;
  setParsedDemand: (parsed: ParsedDemand | null) => void;
  setSubmitting: (isSubmitting: boolean) => void;
  setSubmitError: (error: string | null) => void;
  submitDemand: (rawInput: string) => Promise<DemandSubmitResponse>;
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

  /**
   * 提交需求并启动协商
   * @param rawInput 用户输入的原始需求文本
   * @returns 包含 negotiation_id 的响应
   */
  submitDemand: async (rawInput: string) => {
    set({ isSubmitting: true, submitError: null });

    try {
      const request: DemandSubmitRequest = {
        user_input: rawInput,
        context: {},
      };

      const response = await demandApi.submit(request);

      set({
        currentDemand: request,
        parsedDemand: response.parsed_demand,
        isSubmitting: false,
      });

      return response;
    } catch (error) {
      const message = error instanceof Error ? error.message : '提交失败';
      set({ submitError: message, isSubmitting: false });
      throw error;
    }
  },

  reset: () => set(initialState),
}));
