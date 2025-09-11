import { useMutation } from '@tanstack/react-query';
import { renameChat } from '@/api/chat/api';

export const useRenameChat = () => {
  return useMutation({
    mutationKey: ['rename-chat'],
    mutationFn: renameChat
  });
};
