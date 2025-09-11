import { saveRoleSettings } from '@/api/role-management/api';
import { TRequestSaveRoleSettings } from '@/api/role-management/type';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { settingsQueryKey } from './get-settings';

const useSaveRoleSettings = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: TRequestSaveRoleSettings) => saveRoleSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [settingsQueryKey] });
    }
  });
};

export default useSaveRoleSettings;
