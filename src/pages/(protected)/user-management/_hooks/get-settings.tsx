import { getFeatureSettings } from '@/api/settings/api';
import { useQuery } from '@tanstack/react-query';

export const settingsQueryKey = 'get-settings';

const useGetSettings = () => {
  return useQuery({
    queryKey: [settingsQueryKey],
    queryFn: () => getFeatureSettings()
  });
};

export default useGetSettings;
