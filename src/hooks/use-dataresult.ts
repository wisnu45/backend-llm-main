/* eslint-disable @typescript-eslint/no-explicit-any */
import { create } from 'zustand';

interface DataResultStore {
  messages: any;

  set: (newState: any) => void;
}

export const useDataResult = create<DataResultStore>()((set) => ({
  messages: undefined,

  set: (newState) => set(() => ({ messages: newState }))
}));
