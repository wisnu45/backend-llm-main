import { TResponse } from '@/commons/types/response';

export type TRole = {
  id?: number;
  name: string;
  description: string;
  is_local: boolean;
  is_portal: boolean;
};

export type TUser = {
  id: string;
  is_portal: boolean;
  name: string;
  username: string;
  role: string;
  created_at: string;
  updated_at: string;
};

export type TUserParams = {
  search?: string;
  page?: number;
  page_size?: number;
};

export type TRoleParams = {
  search?: string;
  page?: number;
  page_size?: number;
};

export type TRequestCreateUser = {
  is_portal: boolean;
  name: string;
  password: string;
  username: string;
};

export type TRequestUpdateUser = {
  is_portal: boolean;
  name: string;
  username: string;
};

export type TRequestCreateRole = {
  name: string;
  description: string;
  is_local: boolean;
  is_portal: boolean;
};

export type TRequestUpdateRole = {
  name: string;
  description: string;
  is_local: boolean;
  is_portal: boolean;
};

export type TResponseListUsers = TResponse<TUser[]>;
export type TResponseDetailUser = TResponse<TUser>;
export type TResponseListRoles = TResponse<TRole[]>;
export type TResponseDetailRole = TResponse<TRole>;
