import { login } from '@/api/auth/api';
import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

export const useLogin = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationKey: ['post-login-oidc'],
    mutationFn: login,
    onSuccess: async (res) => {
      SessionToken.set({
        access_token: res.data.access_token,
        username: res.data.userdata.username,
        name: res.data.userdata.name,
        role: res.data.userdata.role.name,
        roles_id: res.data.userdata.role.id,
        is_company: 'true',
        // refresh_token: res.data.refresh_token
        error_connection:
          'Sambungan terputus. Coba periksa jaringan Anda dan muat ulang halaman'
      });
      navigate('/chat', { replace: true });
    },
    onError: () => {}
  });
};
