import { useQuery } from '@tanstack/react-query';
import { getSettings } from '@/api/settings/api';

export const useFetchSetting = () => {
  return useQuery({
    queryKey: ['fetch-setting'],
    queryFn: () => getSettings()
  });
};
