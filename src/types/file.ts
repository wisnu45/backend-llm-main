export type FileListResponse = {
  file: string;
  timestamp: string;
};

export type FileUploadResponse = {
  file_path: string;
  message: string;
};

export type FileUploadInput = {
  file: File;
};

export type FileResetResponse = {
  message: string;
};
