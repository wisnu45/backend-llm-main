import api from '@/lib/api';
import {
  TDocParams,
  TRequestCreateDocument,
  TResponseDetailDocument,
  TResponseListDocument
} from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const getDocs = async (
  params?: TDocParams
): Promise<TResponseListDocument> => {
  const res = await api.get<TResponseListDocument>('/documents', {
    params
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
