import { TResponse } from '@/commons/types/response';

export type TRequestCreateDocument = FormData;

export type TDocItem = {
  created_at: string;
  deleted_at: string;
  document_url: string | null;
  id: string;
  source_type: string;
  metadata: Record<string, string>;
  portal_id: string | null;
  // missing
  updated_at: string;
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
