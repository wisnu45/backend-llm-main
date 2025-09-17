import { login } from '@/api/auth/api';
import { getRoleById } from '@/api/user-management/api';
import { SessionToken } from '@/lib/cookies';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';

export const useLogin = () => {
  const navigate = useNavigate();

  return useMutation({
    mutationKey: ['post-login-oidc'],
    mutationFn: login,
    onSuccess: async (res) => {
      try {
        const roleDetail = await getRoleById(
          res.data.userdata.roles_id,
          res.data.access_token
        );
        SessionToken.set({
          access_token: res.data.access_token,
          username: res.data.userdata.username,
          name: res.data.userdata.name,
          role: roleDetail?.data?.name || '',
          roles_id: res.data.userdata.roles_id,
          refresh_token: res.data.refresh_token
        });
      } catch (err) {
        console.error('Failed to fetch role detail:', err);
      }
      navigate('/chat', { replace: true });
    },
    onError: () => {}
  });
};
