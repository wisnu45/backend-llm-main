import { updateRole } from '@/api/user-management/api';
import { TRequestUpdateRole } from '@/api/user-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { rolesListQueryKey } from './get-roles';
import { roleDetailQueryKey } from './get-role-detail';

const useUpdateRole = (id?: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestUpdateRole) => updateRole(data, { id: id! }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [rolesListQueryKey] });
      queryClient.invalidateQueries({ queryKey: [roleDetailQueryKey, id] });
    }
  });
};

export default useUpdateRole;
