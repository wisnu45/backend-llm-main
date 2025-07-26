import { login } from '@/api/auth/api';
import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

export const useLogin = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationKey: ['post-login-oidc'],
    mutationFn: login,
    onSuccess: (res) => {
      SessionToken.set({
        access_token: res.authorization,
        username: res.data.userdata.username,
        name: res.data.userdata.name,
        role: res.data.userdata.role
      });
      navigate('/chat', { replace: true });
    },
    onError: () => {}
  });
};
