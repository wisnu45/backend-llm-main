import { TResponse } from '@/commons/types/response';

export type TRole = {
  id: string;
  name: string;
  chat: boolean;
  file_management: boolean;
  history: boolean;
  chat_attachment: boolean;
  max_chat_topic: number;
  chat_topic_expired_days: number;
  max_chat: number;
  user_management: boolean;
  permissions?: Array<{ id: string; name: string }>;
  created_at: string;
  updated_at: string;
};

export type TUser = {
  id: string;
  originalName: string;
  username: string;
  isPortalUser: boolean;
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
  originalName: string;
  username: string;
  password: string;
  isPortalUser: boolean;
  role_id: string;
};

export type TRequestUpdateUser = {
  originalName: string;
  username: string;
  isPortalUser: boolean;
  role_id: string;
};

export type TRequestCreateRole = {
  name: string;
  chat: boolean;
  file_management: boolean;
  history: boolean;
  chat_attachment: boolean;
  max_chat_topic: number;
  chat_topic_expired_days: number;
  max_chat: number;
  user_management: boolean;
};

export type TRequestUpdateRole = {
  name: string;
  chat: boolean;
  file_management: boolean;
  history: boolean;
  chat_attachment: boolean;
  max_chat_topic: number;
  chat_topic_expired_days: number;
  max_chat: number;
  user_management: boolean;
};

export type TResponseListUsers = TResponse<TUser[]>;
export type TResponseDetailUser = TResponse<TUser>;
export type TResponseListRoles = TResponse<TRole[]>;
export type TResponseDetailRole = TResponse<TRole>;
