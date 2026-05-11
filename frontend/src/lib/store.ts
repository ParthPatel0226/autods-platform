import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

interface AppState {
  currentProjectId: string | null;
  setCurrentProject: (id: string | null) => void;
  sidebarOpen: boolean;
  toggleSidebar: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      currentProjectId: null,
      setCurrentProject: (id) => set({ currentProjectId: id }),
      sidebarOpen: true,
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
    }),
    {
      name: "autods-app-state",
      storage: createJSONStorage(() => localStorage),
      // Only persist the project selection; sidebar state is session-only
      partialize: (state) => ({ currentProjectId: state.currentProjectId }),
    },
  ),
);
