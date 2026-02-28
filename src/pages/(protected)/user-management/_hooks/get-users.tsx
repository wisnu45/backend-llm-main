import { getUsers } from '@/api/user-management/api';
import { TUserParams } from '@/api/user-management/type';
import { useQuery } from '@tanstack/react-query';

export const usersListQueryKey = 'get-users-list';

const useGetUsers = (params?: TUserParams) => {
  return useQuery({
    queryKey: [usersListQueryKey, params],
    queryFn: () => getUsers(params)
  });
};

export default useGetUsers;
