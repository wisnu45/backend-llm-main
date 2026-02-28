import { create } from 'zustand';

type fileStatus = 'pending' | 'success' | 'failed' | 'processing';

export interface FileUploadStatus {
  id: string;
  file: File;
  status: fileStatus;
  errorMessage?: string;
}

interface FileStore {
  files: FileUploadStatus[];
  isSubmitting: boolean;

  setIsSubmitting: (value: boolean) => void;
  setFiles: (files: File[]) => void;
  setFileStatus: (
    id: string,
    status: fileStatus,
    errorMessage?: string
  ) => void;
  addFile: (file: File) => void;
}

export const useFiles = create<FileStore>((set) => ({
  files: [],
  isSubmitting: false,

  setIsSubmitting: (value) => set({ isSubmitting: value }),
  setFiles: (files: File[]) => {
    const fileStatuses: FileUploadStatus[] = files.map((file) => ({
      id: file.name + Date.now(),
      file,
      status: 'pending'
    }));
    set(() => ({ files: fileStatuses }));
  },

  setFileStatus: (id, status, errorMessage) =>
    set((state) => ({
      files: state.files.map((fileStatus) =>
        fileStatus.id === id
          ? { ...fileStatus, status, errorMessage }
          : fileStatus
      )
    })),

  addFile: (file) =>
    set((state) => ({
      files: [
        ...state.files,
        { id: file.name + Date.now(), file, status: 'pending' }
      ]
    }))
}));
