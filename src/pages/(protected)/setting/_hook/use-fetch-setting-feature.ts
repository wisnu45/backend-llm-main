import { useQuery } from '@tanstack/react-query';
import { getSettingsFeature } from '@/api/settings/api';
import Cookies from 'js-cookie';

export const useFetchSettingFeature = () => {
  return useQuery({
    queryKey: ['fetch-setting-feature'],
    queryFn: () => getSettingsFeature(Cookies.get('roles_id') || '')
  });
};
