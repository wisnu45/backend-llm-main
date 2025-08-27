import { useMutation } from '@tanstack/react-query';
import { bulkDeleteChat } from '@/api/chat/api';

export const useBulkDeleteChat = () => {
  return useMutation({
    mutationKey: ['delete-bulk-chat'],
    mutationFn: bulkDeleteChat
  });
};
