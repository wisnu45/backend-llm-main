/* eslint-disable @typescript-eslint/no-explicit-any */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface BreadcrumbStore {
  routes: any[];

  addRoute: (data: any) => void;
  setRoutes: (data: any) => void;
  resetRoute: () => void;
}

export const useBreadcrumbStore = create<BreadcrumbStore>()(
  persist(
    (set) => ({
      routes: [],

      // setRoute: (data) => set(({ routes }) => ({ routes: [...routes, data] })),
      addRoute: (data) => set(({ routes }) => ({ routes: [...routes, data] })),
      setRoutes: (data) => set(() => ({ routes: data })),
      resetRoute: () => set({ routes: [] })
    }),
    {
      name: 'breadcrumb-store'
    }
  )
);
