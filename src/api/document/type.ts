import { TResponse } from '@/commons/types/response';

export type TRequestCreateDocument = FormData;

export type TDocItem = {
  created_at: string;
  deleted_at: string;
  url: string | null;
  id: string;
  source_type: string;
  stored_filename: string;
  metadata: Record<string, string>;
  portal_id: string | null;
  original_filename: string;
  // missing
  updated_at: string;
  storage_path: string;
};

export type TDocParams = {
  search: string;
  page: number;
  page_size: number;
  source_type: 'all' | 'portal' | 'admin' | 'user' | 'website';
  doc_type: 'all' | 'portal' | 'admin' | 'user' | 'website';
  // enabled?: boolean;
};

export type TResponseListDocument = TResponse<TDocItem[]>;
export type TResponseDetailDocument = TResponse<TDocItem>;
