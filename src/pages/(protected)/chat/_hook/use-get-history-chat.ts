import { useQuery } from '@tanstack/react-query';
import { getDetailHistory } from '@/api/chat/api';
import { TClearChatRequest, TGetDetailHistoryData } from '@/api/chat/type';

interface UseGetDetailHistoryParams {
  request: TClearChatRequest;
}

interface UseGetDetailHistoryResult {
  data: TGetDetailHistoryData | undefined;
  isLoading: boolean;
  isFetching: boolean;
  error: unknown;
  refetch: () => void;
}

export const useGetDetailHistory = (
  request: UseGetDetailHistoryParams['request']
): UseGetDetailHistoryResult => {
  const query = useQuery<TGetDetailHistoryData>({
    queryKey: ['history-detail-chat', request],
    queryFn: async () => getDetailHistory(request)
  });
  return query;
};
