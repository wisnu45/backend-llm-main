import api from '@/lib/api';
import {
  TRequestCreateDocument,
  TResponseDetailDocument,
  TResponseListDocument
} from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const getDocs = async (
  search: string = '',
  page: number = 1,
  limit: number = 10
): Promise<TResponseListDocument> => {
  const res = await api.get<TResponseListDocument>('/documents', {
    params: {
      search,
      page,
      limit
    }
  });
  return res.data;
};

export const getDetailDoc = async (params: {
  id?: string;
}): Promise<TResponseDetailDocument> => {
  const res = await api.get<TResponseDetailDocument>(`/documents/${params.id}`);
  return res.data;
};

export const createDoc = async (
  req: TRequestCreateDocument
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/documents', req, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
  return res.data;
};

export const deleteDoc = async (params: {
  id: string;
}): Promise<TDefaultResponse> => {
  const res = await api.delete<TDefaultResponse>(`/documents/${params.id}`);
  return res.data;
};

export const editDoc = async (
  req: TRequestCreateDocument,
  params: { id: string }
): Promise<TDefaultResponse> => {
  const res = await api.patch<TDefaultResponse>(
    `/documents/${params.id}`,
    req,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );
  return res.data;
};
