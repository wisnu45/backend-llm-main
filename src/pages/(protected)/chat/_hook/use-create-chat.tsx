import { chat } from '@/api/chat/api';
import { useMutation } from '@tanstack/react-query';
import { AxiosError } from 'axios';

interface NetworkAwareError extends AxiosError {
  isNetworkError?: boolean;
}

const useCreateChat = () => {
  return useMutation({
    mutationKey: ['create-chat'],
    mutationFn: chat,
    meta: {
      // Add meta to identify this as a chat mutation for error handling
      mutationType: 'chat'
    }
  });
};

export { type NetworkAwareError };
export default useCreateChat;
