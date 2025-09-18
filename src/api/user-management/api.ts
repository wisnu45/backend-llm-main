import { TDefaultResponse } from '@/commons/types/response';
import api from '@/lib/api';
import {
  TRequestCreateRole,
  TRequestCreateUser,
  TRequestUpdateRole,
  TRequestUpdateUser,
  TResponseDetailUser,
  TResponseListRoles,
  TResponseListUsers,
  TRoleParams,
  TUserParams
} from './type';

export const getUsers = async (
  params?: TUserParams
): Promise<TResponseListUsers> => {
  const res = await api.get<TResponseListUsers>('/users', {
    params
  });
  return res.data;
};

export const getUserDetail = async (params: {
  id: string;
}): Promise<TResponseDetailUser> => {
  const res = await api.get<TResponseDetailUser>(`/user/${params.id}`);
  return res.data;
};

export const createUser = async (
  req: TRequestCreateUser
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/user', req);
  return res.data;
};

export const updateUser = async (
  req: TRequestUpdateUser,
  params: { id: string }
): Promise<TDefaultResponse> => {
  const res = await api.patch<TDefaultResponse>(`/user/${params.id}`, req);
  return res.data;
};

export const deleteUser = async (params: {
  id: string;
}): Promise<TDefaultResponse> => {
  const res = await api.delete<TDefaultResponse>(`/user/${params.id}`);
  return res.data;
};

export const getRoles = async (
  params?: TRoleParams
): Promise<TResponseListRoles> => {
  const res = await api.get<TResponseListRoles>('/roles', {
    params
  });
  return res.data;
};

export const createRole = async (
  req: TRequestCreateRole
): Promise<TDefaultResponse> => {
  const res = await api.post<TDefaultResponse>('/role', req);
  return res.data;
};

export const updateRole = async (
  req: TRequestUpdateRole,
  params: { id: string }
): Promise<TDefaultResponse> => {
  const res = await api.put<TDefaultResponse>(`/role/${params.id}`, req);
  return res.data;
};

export const deleteRole = async (params: {
  id: string;
}): Promise<TDefaultResponse> => {
  const res = await api.delete<TDefaultResponse>(`/role/${params.id}`);
  return res.data;
};
