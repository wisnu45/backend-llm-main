import { getRoleDetail } from '@/api/user-management/api';
import { useQuery } from '@tanstack/react-query';

export const roleDetailQueryKey = 'get-role-detail';

const useGetRoleDetail = (id?: string) => {
  return useQuery({
    queryKey: [roleDetailQueryKey, id],
    queryFn: () => getRoleDetail({ id: id! }),
    enabled: !!id
  });
};

export default useGetRoleDetail;
