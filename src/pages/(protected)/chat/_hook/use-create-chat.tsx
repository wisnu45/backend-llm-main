import { chat } from '@/api/chat/api';
import { useMutation } from '@tanstack/react-query';

const useCreateChat = () => {
  return useMutation({
    mutationKey: ['create-chat'],
    mutationFn: chat
  });
};

export default useCreateChat;
