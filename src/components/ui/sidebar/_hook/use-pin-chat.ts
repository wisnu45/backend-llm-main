import { useMutation } from '@tanstack/react-query';
import { pinChat } from '@/api/chat/api';

export const usePinChat = () => {
  return useMutation({
    mutationKey: ['pin-chat'],
    mutationFn: pinChat
  });
};
