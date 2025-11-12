import { clearSyncLogs } from '@/api/sync-log/api';
import { toast } from '@/components/ui/use-toast';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { syncLogsQueryKey } from './get-sync-logs';

const useClearSyncLogs = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationKey: ['clear-sync-logs'],
    mutationFn: clearSyncLogs,
    onSuccess: (data) => {
      queryClient.invalidateQueries({
        queryKey: [syncLogsQueryKey],
        type: 'all'
      });
      toast({
        title: 'Sync logs cleared',
        description: data.message,
        variant: 'default'
      });
    },
    onError: (error: any) => {
      toast({
        title: 'Failed to clear sync logs',
        description:
          error?.response?.data?.error || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  });
};

export default useClearSyncLogs;
