import { useMutation } from '@tanstack/react-query';
import { clearChat } from '@/api/chat/api';

export const useDeleteChat = () => {
  return useMutation({
    mutationKey: ['delete-chat'],
    mutationFn: clearChat
  });
};
