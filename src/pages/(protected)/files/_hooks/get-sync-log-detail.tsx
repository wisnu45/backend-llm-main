import { getSyncLogDetail } from '@/api/sync-log/api';
import { useQuery } from '@tanstack/react-query';

const useGetSyncLogDetail = (id?: string) => {
  return useQuery({
    queryKey: ['get-sync-log-detail', id],
    queryFn: () => getSyncLogDetail(id!),
    enabled: !!id
  });
};

export default useGetSyncLogDetail;
