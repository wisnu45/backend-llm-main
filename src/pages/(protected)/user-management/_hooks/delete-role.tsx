import { deleteRole } from '@/api/user-management/api';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { rolesListQueryKey } from './get-roles';

const useDeleteRole = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: { id: string }) => deleteRole(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [rolesListQueryKey] });
    }
  });
};

export default useDeleteRole;
