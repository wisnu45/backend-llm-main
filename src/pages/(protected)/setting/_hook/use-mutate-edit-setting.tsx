import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from '@/components/ui/use-toast';
import { editSetting } from '@/api/settings/api';
import { TRequestEditSetting } from '@/api/settings/type';

const useEditSetting = (id: string) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationKey: ['use-mutate-edit-setting'],
    mutationFn: (req: TRequestEditSetting) => editSetting(req, { id }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ['fetch-setting'],
        type: 'all'
      });
      toast({
        title: 'Setting edited successfully!',
        variant: 'default'
      });
    },
    onError: (error) => {
      toast({
        title: 'Failed to edi Setting',
        description: error?.message || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  });
};

export default useEditSetting;
