import { updateRole } from '@/api/user-management/api';
import { TRequestUpdateRole } from '@/api/user-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { rolesListQueryKey } from './get-roles';

const useUpdateRole = (id?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestUpdateRole) => updateRole(data, { id: id! }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [rolesListQueryKey] });
    }
  });
};

export default useUpdateRole;
