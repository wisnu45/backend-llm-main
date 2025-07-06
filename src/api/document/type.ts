import { TResponse } from '@/commons/types/response';

export type TRequestCreateDocument = FormData;

export type TDocItem = {
  created_at: string;
  deleted_at: string;
  document_name: string;
  id: string;
  metadata: unknown;
  portal_id: string | null;
  // missing
  updated_at: string;
};

export type TResponseListDocument = TResponse<TDocItem[]>;
export type TResponseDetailDocument = TResponse<TDocItem>;
