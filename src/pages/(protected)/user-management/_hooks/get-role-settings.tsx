import { getRoleSettings } from '@/api/role-management/api';
import { useQuery } from '@tanstack/react-query';

export const settingsQueryKey = 'get-settings-role';

const useGetRoleSettings = (id: string) => {
  return useQuery({
    queryKey: [settingsQueryKey, { id }],
    queryFn: () => getRoleSettings(id),
    enabled: !!id,
    staleTime: 0
  });
};

export default useGetRoleSettings;
