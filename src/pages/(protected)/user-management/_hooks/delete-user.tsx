import { deleteUser } from '@/api/user-management/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { usersListQueryKey } from './get-users';

const useDeleteUser = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { id: string }) => deleteUser(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [usersListQueryKey] });
    }
  });
};

export default useDeleteUser;
