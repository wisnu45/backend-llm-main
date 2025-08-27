import { createUser } from '@/api/user-management/api';
import { TRequestCreateUser } from '@/api/user-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { usersListQueryKey } from './get-users';

const useCreateUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestCreateUser) => createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [usersListQueryKey] });
    }
  });
};

export default useCreateUser;
