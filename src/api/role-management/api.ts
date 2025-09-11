import { TDefaultResponse } from '@/commons/types/response';
import api from '@/lib/api';
import { TRequestSaveRoleSettings } from './type';

export const saveRoleSettings = async (
  req: TRequestSaveRoleSettings
): Promise<TDefaultResponse> => {
  // Extract role_id from the first item (assuming all items have the same role_id)
  const roleId = req.length > 0 ? req[0].role_id : null;
  if (!roleId) throw new Error('Role ID is required');

  const res = await api.post<TDefaultResponse>(`/role/settings/${roleId}`, req);
  return res.data;
};
