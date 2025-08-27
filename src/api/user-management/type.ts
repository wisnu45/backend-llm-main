import { TResponse } from '@/commons/types/response';

export type TPermission = {
  id: string;
  name: string;
  key: string;
};

export type TRole = {
  id: string;
  name: string;
  permissions: TPermission[];
  created_at: string;
  updated_at: string;
};

export type TUser = {
  id: string;
  name: string;
  email: string;
  role_id: string;
  role?: TRole;
  created_at: string;
  updated_at: string;
};

export type TUserParams = {
  search?: string;
  page?: number;
  page_size?: number;
  role_id?: string;
};

export type TRoleParams = {
  search?: string;
  page?: number;
  page_size?: number;
};

export type TRequestCreateUser = {
  name: string;
  email: string;
  role_id: string;
};

export type TRequestUpdateUser = {
  name: string;
  email: string;
  role_id: string;
};

export type TRequestCreateRole = {
  name: string;
  permission_ids: string[];
};

export type TRequestUpdateRole = {
  name: string;
  permission_ids: string[];
};

export type TResponseListUsers = TResponse<TUser[]>;
export type TResponseDetailUser = TResponse<TUser>;
export type TResponseListRoles = TResponse<TRole[]>;
export type TResponseDetailRole = TResponse<TRole>;
export type TResponseListPermissions = TResponse<TPermission[]>;
