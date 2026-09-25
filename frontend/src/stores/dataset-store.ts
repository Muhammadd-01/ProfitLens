import { create } from 'zustand';
import type { Dataset } from '@/types';

interface DatasetState {
  datasets: Dataset[];
  activeDataset: Dataset | null;

  setDatasets: (datasets: Dataset[]) => void;
  setActiveDataset: (dataset: Dataset | null) => void;
  addDataset: (dataset: Dataset) => void;
  updateDataset: (id: string, updates: Partial<Dataset>) => void;
}

export const useDatasetStore = create<DatasetState>((set) => ({
  datasets: [],
  activeDataset: null,

  setDatasets: (datasets) => set({ datasets }),

  setActiveDataset: (dataset) => set({ activeDataset: dataset }),

  addDataset: (dataset) =>
    set((state) => ({ datasets: [dataset, ...state.datasets] })),

  updateDataset: (id, updates) =>
    set((state) => ({
      datasets: state.datasets.map((d) =>
        d.id === id ? { ...d, ...updates } : d
      ),
      activeDataset:
        state.activeDataset?.id === id
          ? { ...state.activeDataset, ...updates }
          : state.activeDataset,
    })),
}));
