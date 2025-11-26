import { TResponse } from '@/commons/types/response';

export type TSyncStatus = 'success' | 'partial_success' | 'failed';

export type TFailedDocument = {
  title: string;
  file_id: string;
  error_message: string;
};

export type TSyncLogItem = {
  id: string;
  timestamp: string;
  status: TSyncStatus;
  total_documents: number;
  success_count: number;
  failed_count: number;
  global_error?: string;
  title?: string;
  metadata: {
    title?: string;
  };
  original_filename?: string;
};

export type TSyncLogDetail = TSyncLogItem & {
  failed_documents: TFailedDocument[];
};

export type TSyncLogParams = {
  search?: string;
  date_start?: string;
  date_end?: string;
  status?: TSyncStatus | 'all';
  page?: number;
  page_size?: number;
};

export type TResponseSyncLogs = TResponse<TSyncLogItem[]>;
export type TResponseSyncLogDetail = TResponse<TSyncLogDetail>;
