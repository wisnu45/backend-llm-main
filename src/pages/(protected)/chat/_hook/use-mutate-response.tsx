import { chatFeedback } from '@/api/chat/api';
import { TChatResponseRequest } from '@/api/chat/type';
import { TDefaultResponse } from '@/commons/types/response';
import { useMutation } from '@tanstack/react-query';

const useCreateFeedbackChat = () => {
  return useMutation<TDefaultResponse, Error, TChatResponseRequest>({
    mutationKey: ['feedback-chat'],
    mutationFn: (data: TChatResponseRequest) => chatFeedback(data)
  });
};

export default useCreateFeedbackChat;
