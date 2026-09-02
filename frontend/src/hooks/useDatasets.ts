import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/services/api";

export function useDatasets() {
  return useQuery({ queryKey: ["datasets"], queryFn: api.listDatasets });
}

export function useDataset(id: string | undefined) {
  return useQuery({
    queryKey: ["dataset", id],
    queryFn: () => api.getDataset(id as string),
    enabled: !!id,
  });
}

export function useDatasetPreview(
  id: string | undefined,
  opts: { page?: number; page_size?: number; sort?: string; sort_dir?: "asc" | "desc"; search?: string }
) {
  return useQuery({
    queryKey: ["dataset-preview", id, opts],
    queryFn: () => api.previewDataset(id as string, opts),
    enabled: !!id,
    placeholderData: (prev) => prev,
  });
}

export function useDatasetProfile(id: string | undefined) {
  return useQuery({
    queryKey: ["dataset-profile", id],
    queryFn: () => api.getDatasetProfile(id as string),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useDatasetColumns(id: string | undefined) {
  return useQuery({
    queryKey: ["dataset-columns", id],
    queryFn: () => api.getDatasetColumns(id as string),
    enabled: !!id,
  });
}

export function useEdaSuggestions(id: string | undefined) {
  return useQuery({
    queryKey: ["eda-suggestions", id],
    queryFn: () => api.getEdaSuggestions(id as string),
    enabled: !!id,
    staleTime: 60_000,
  });
}

export function useUploadDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => api.uploadDataset(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDataset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["datasets"] }),
  });
}
