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
   * @returns 包含 demand_id 的响应（兼容 negotiation_id）
   */
  submitDemand: async (rawInput: string) => {
    set({ isSubmitting: true, submitError: null });

    try {
      const request: DemandSubmitRequest = {
        raw_input: rawInput,  // 使用后端期望的字段名
      };

      const response = await demandApi.submit(request);

      // 将 demand_id 映射到 negotiation_id 以保持前端兼容性
      const mappedResponse = {
        ...response,
        negotiation_id: response.demand_id,
      };

      set({
        currentDemand: request,
        parsedDemand: null,  // 后端目前不返回 parsed_demand
        isSubmitting: false,
      });

      return mappedResponse;
    } catch (error) {
      const message = error instanceof Error ? error.message : '提交失败';
      set({ submitError: message, isSubmitting: false });
      throw error;
    }
  },

  reset: () => set(initialState),
}));
