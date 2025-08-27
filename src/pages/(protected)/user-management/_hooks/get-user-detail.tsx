import { getUserDetail } from '@/api/user-management/api';
import { useQuery } from '@tanstack/react-query';

export const userDetailQueryKey = 'get-user-detail';

const useGetUserDetail = (id?: string) => {
  return useQuery({
    queryKey: [userDetailQueryKey, id],
    queryFn: () => getUserDetail({ id: id! }),
    enabled: !!id
  });
};

export default useGetUserDetail;
