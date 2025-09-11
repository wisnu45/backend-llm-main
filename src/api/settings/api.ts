import api from '@/lib/api';
import { TResponseListSettings } from './type';

export const getFeatureSettings = async (): Promise<TResponseListSettings> => {
  const res = await api.get<TResponseListSettings>('/settings/feature');
  return res.data;
};
