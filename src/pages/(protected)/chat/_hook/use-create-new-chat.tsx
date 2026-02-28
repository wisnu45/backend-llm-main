import { newChat } from '@/api/chat/api';
import { useMutation } from '@tanstack/react-query';

const useCreateNewChat = () => {
  return useMutation({
    mutationKey: ['create-new-chat'],
    mutationFn: newChat
  });
};

export default useCreateNewChat;
