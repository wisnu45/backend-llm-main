import { TDefaultResponse } from '@/commons/types/response';
import api from '@/lib/api';
import { TRequestSaveRoleSettings } from './type';

export const saveRoleSettings = async (
  req: TRequestSaveRoleSettings
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>(`/role/settings`, req);
  return res.data;
};
