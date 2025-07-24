import api from '@/lib/api';
import { TLoginRequest, TLoginResponse, TLogoutRequest } from './type';

export const login = async (req: TLoginRequest): Promise<TLoginResponse> => {
  const res = await api.post<TLoginResponse>('/auth/login', req);
  return res.data;
};

export const logout = async (req: TLogoutRequest): Promise<TLoginResponse> => {
  const res = await api.post<TLoginResponse>('/logout', { session_id: req });
  return res.data;
};
