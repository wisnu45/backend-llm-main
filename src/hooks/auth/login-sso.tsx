import { loginBySSO } from '@/api/auth/api';
import { useMutation } from '@tanstack/react-query';

export const useLoginSSO = () => {
  return useMutation({
    mutationKey: ['login-sso'],
    mutationFn: loginBySSO
  });
};
