import { createRole } from '@/api/user-management/api';
import { TRequestCreateRole } from '@/api/user-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { rolesListQueryKey } from './get-roles';

const useCreateRole = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestCreateRole) => createRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [rolesListQueryKey] });
    }
  });
};

export default useCreateRole;
