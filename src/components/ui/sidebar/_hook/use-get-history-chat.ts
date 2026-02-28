import { useQuery } from '@tanstack/react-query';
import { getHistory } from '@/api/chat/api';
import { TGetHistoryRequest } from '@/api/chat/type';

export const useGetFiles = () => {
  return useQuery<TGetHistoryRequest>({
    queryKey: ['history-chat'],
    queryFn: async () => getHistory()
  });
};
