import api from '@/lib/api';
import { TCreateRequest, TDeleteRequest, TUpdateRequest } from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const getIntro = async (): Promise<TDefaultResponse> => {
  const res = await api.get<TDefaultResponse>('/intro');
  return res.data;
};

export const createIntro = async (
  req: TCreateRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/intro-create', req);
  return res.data;
};

export const deleteIntro = async (
  req: TDeleteRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/intro-delete', req);
  return res.data;
};

export const updateIntro = async (
  req: TUpdateRequest
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/intro-update', req);
  return res.data;
};
