import { getPermissions } from '@/api/user-management/api';
import { useQuery } from '@tanstack/react-query';

export const permissionsListQueryKey = 'get-permissions-list';

const useGetPermissions = () => {
  return useQuery({
    queryKey: [permissionsListQueryKey],
    queryFn: () => getPermissions()
  });
};

export default useGetPermissions;
