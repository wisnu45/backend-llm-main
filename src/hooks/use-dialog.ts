import { create } from 'zustand';

interface Dialog {
  open: boolean;
  setOpen: (state: boolean) => void;
}

export const useDialog = create<Dialog>((set) => ({
  open: false,
  setOpen: (newState) => set({ open: newState })
}));
