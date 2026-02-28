import api from '@/lib/api';
import {
  TRequestEditSetting,
  TResponseListSettings,
  TResponseSettingDocument
} from './type';
import { TDefaultResponse } from '@/commons/types/response';

export const getFeatureSettings = async (): Promise<TResponseListSettings> => {
  const res = await api.get<TResponseListSettings>('/settings/feature');
  return res.data;
};

export const getSettings = async (): Promise<TResponseSettingDocument> => {
  const res = await api.get<TResponseSettingDocument>('/settings');
  return res.data;
};

export const editSetting = async (
  req: TRequestEditSetting,
  params: { id: string }
): Promise<TDefaultResponse> => {
  const res = await api.put<TDefaultResponse>(`/setting/${params.id}`, req, {
    headers: {
      'Content-Type': 'application/json'
    }
  });
  return res.data;
};

export const getMenuSettings = async (
  role_id: string
): Promise<TResponseListSettings> => {
  const res = await api.get<TResponseListSettings>(
    `/role/settings/${role_id}/menu`
  );
  return res.data;
};

export const getSettingsFeature = async (
  role_id: string
): Promise<TResponseListSettings> => {
  const res = await api.get<TResponseListSettings>(`/role/settings/${role_id}`);
  return res.data;
};
