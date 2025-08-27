import { updateUser } from '@/api/user-management/api';
import { TRequestUpdateUser } from '@/api/user-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { usersListQueryKey } from './get-users';
import { userDetailQueryKey } from './get-user-detail';

const useUpdateUser = (id?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestUpdateUser) => updateUser(data, { id: id! }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [usersListQueryKey] });
      queryClient.invalidateQueries({ queryKey: [userDetailQueryKey, id] });
    }
  });
};

export default useUpdateUser;
