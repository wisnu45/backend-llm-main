import { logout } from '@/api/auth/api';
import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';
import Cookies from 'js-cookie';
import { useNavigate } from 'react-router-dom';

export const useLogout = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationKey: ['post-logout-oidc'],
    mutationFn: async () => {
      const refreshToken = Cookies.get('refresh_token');
      await logout({ refresh_token: refreshToken || '' });
    },
    onSuccess: () => {
      SessionToken.remove();
      navigate('/auth/signin', { replace: true });
    },
    onError: () => {}
  });
};
