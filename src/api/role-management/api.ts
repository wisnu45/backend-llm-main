import { TDefaultResponse } from '@/commons/types/response';
import api from '@/lib/api';
import { TResponseListSettings } from '../settings/type';
import { TRequestSaveRoleSettings } from './type';

export const saveRoleSettings = async (
  req: TRequestSaveRoleSettings
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>(`/role/settings/bulk`, req);
  return res.data;
};

export const getRoleSettings = async (
  id: string
): Promise<TResponseListSettings> => {
  const res = await api.get<TResponseListSettings>(
    `/role/settings/${id}/feature`
  );
  return res.data;
};
