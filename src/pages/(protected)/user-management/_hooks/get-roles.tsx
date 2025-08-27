import { getRoles } from '@/api/user-management/api';
import { TRoleParams } from '@/api/user-management/type';
import { useQuery } from '@tanstack/react-query';

export const rolesListQueryKey = 'get-roles-list';

const useGetRoles = (params?: TRoleParams) => {
  return useQuery({
    queryKey: [rolesListQueryKey, params],
    queryFn: () => getRoles(params)
  });
};

export default useGetRoles;
