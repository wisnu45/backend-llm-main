import { getSettingsFeature } from '@/api/settings/api';
import { useQuery } from '@tanstack/react-query';
import Cookies from 'js-cookie';

export const useFetchSettingFeature = () => {
  const roleId = Cookies.get('roles_id') || '';
  return useQuery({
    queryKey: ['fetch-setting-feature', roleId],
    queryFn: () => getSettingsFeature(roleId)
  });
};
