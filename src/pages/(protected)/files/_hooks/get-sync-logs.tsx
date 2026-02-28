import { getSyncLogs } from '@/api/sync-log/api';
import { TSyncLogParams } from '@/api/sync-log/type';
import { useQuery } from '@tanstack/react-query';

export const syncLogsQueryKey = 'get-sync-logs';

const useGetSyncLogs = (params?: TSyncLogParams) => {
  return useQuery({
    queryKey: [syncLogsQueryKey, params],
    queryFn: () => getSyncLogs(params)
  });
};

export default useGetSyncLogs;
