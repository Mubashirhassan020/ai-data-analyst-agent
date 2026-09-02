import { useMutation } from "@tanstack/react-query";
import { api } from "@/services/api";
import type { AnalysisRequest, ChartRequest } from "@/types/api";

export function useExecuteAnalysis() {
  return useMutation({ mutationFn: (payload: AnalysisRequest) => api.executeAnalysis(payload) });
}

export function useBuildChart() {
  return useMutation({ mutationFn: (payload: ChartRequest) => api.buildChart(payload) });
}
