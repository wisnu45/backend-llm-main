import api from '@/lib/api';
import { TCreateRequest, TDeleteRequest, TUpdateRequest } from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const getEnhance = async (): Promise<TDefaultResponse> => {
  const res = await api.get<TDefaultResponse>('/enhance');
  return res.data;
};

export const createEnhance = async (
  req: TCreateRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/enhance-create', req);
  return res.data;
};

export const deleteEnhance = async (
  req: TDeleteRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/enhance-delete', req);
  return res.data;
};

export const updateEnhance = async (
  req: TUpdateRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/enhance-update', req);
  return res.data;
};
