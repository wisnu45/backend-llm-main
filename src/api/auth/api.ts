import api, { baseAxios } from '@/lib/api';
import {
  TLoginRequest,
  TLoginResponse,
  TLoginSSORequest,
  TLogoutRequest
} from './type';

export const login = async (req: TLoginRequest): Promise<TLoginResponse> => {
  const res = await baseAxios.post<TLoginResponse>('/auth/login', req);
  return res.data;
};

export const logout = async (req: TLogoutRequest): Promise<TLoginResponse> => {
  const res = await api.post<TLoginResponse>('/auth/logout', req);
  return res.data;
};

export const loginBySSO = async (
  req: TLoginSSORequest
): Promise<TLoginResponse> => {
  const res = await api.post<TLoginResponse>('/auth/sso-login', req);
  return res.data;
};
