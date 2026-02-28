import { ActionType } from '@/types';
import { create } from 'zustand';

export interface TableStore<TData> {
  actionType?: ActionType;
  data: TData;

  set: (state: Partial<TableStore<TData>>) => void;
}

export const createTableState = <TData>(initialData: TData) =>
  create<TableStore<TData>>((set) => ({
    actionType: undefined,
    data: initialData,
    set: (newState) => set((prev) => ({ ...prev, ...newState }))
  }));
