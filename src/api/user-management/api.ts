import { TDefaultResponse } from '@/commons/types/response';
import {
  TUserParams,
  TRoleParams,
  TRequestCreateUser,
  TRequestUpdateUser,
  TRequestCreateRole,
  TRequestUpdateRole,
  TResponseListUsers,
  TResponseDetailUser,
  TResponseListRoles,
  TResponseDetailRole,
  TUser,
  TRole
} from './type';

const MOCK_ROLES: TRole[] = [
  {
    id: '1',
    name: 'Admin',
    chat: true,
    file_management: true,
    history: true,
    chat_attachment: true,
    user_management: true,
    max_chat_topic: 100,
    chat_topic_expired_days: 365,
    max_chat: 1000,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: '2',
    name: 'User',
    chat: true,
    file_management: false,
    history: true,
    chat_attachment: true,
    user_management: false,
    max_chat_topic: 10,
    chat_topic_expired_days: 30,
    max_chat: 100,
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z'
  },
  {
    id: '3',
    name: 'BOD',
    chat: true,
    file_management: true,
    history: true,
    chat_attachment: true,
    user_management: false,
    max_chat_topic: 50,
    chat_topic_expired_days: 90,
    max_chat: 500,
    created_at: '2024-01-03T00:00:00Z',
    updated_at: '2024-01-03T00:00:00Z'
  }
];

const MOCK_USERS: TUser[] = [
  {
    id: '1',
    name: 'John Doe',
    username: 'john.doe',
    isPortalUser: true,
    role_id: '1',
    role: MOCK_ROLES[0],
    created_at: '2024-01-01T10:00:00Z',
    updated_at: '2024-01-01T10:00:00Z'
  },
  {
    id: '2',
    name: 'Jane Smith',
    username: 'jane.smith',
    isPortalUser: false,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-02T10:00:00Z',
    updated_at: '2024-01-02T10:00:00Z'
  },
  {
    id: '3',
    name: 'Alice Johnson',
    username: 'alice.johnson',
    isPortalUser: true,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-03T10:00:00Z',
    updated_at: '2024-01-03T10:00:00Z'
  },
  {
    id: '4',
    name: 'Bob Wilson',
    username: 'bob.wilson',
    isPortalUser: false,
    role_id: '3',
    role: MOCK_ROLES[2],
    created_at: '2024-01-04T10:00:00Z',
    updated_at: '2024-01-04T10:00:00Z'
  },
  {
    id: '5',
    name: 'Carol Brown',
    username: 'carol.brown',
    isPortalUser: true,
    role_id: '3',
    role: MOCK_ROLES[2],
    created_at: '2024-01-05T10:00:00Z',
    updated_at: '2024-01-05T10:00:00Z'
  },
  {
    id: '6',
    name: 'David Lee',
    username: 'david.lee',
    isPortalUser: false,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-06T10:00:00Z',
    updated_at: '2024-01-06T10:00:00Z'
  },
  {
    id: '7',
    name: 'Emma Davis',
    username: 'emma.davis',
    isPortalUser: true,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-07T10:00:00Z',
    updated_at: '2024-01-07T10:00:00Z'
  },
  {
    id: '8',
    name: 'Frank Miller',
    username: 'frank.miller',
    isPortalUser: false,
    role_id: '3',
    role: MOCK_ROLES[2],
    created_at: '2024-01-08T10:00:00Z',
    updated_at: '2024-01-08T10:00:00Z'
  },
  {
    id: '9',
    name: 'Grace Taylor',
    username: 'grace.taylor',
    isPortalUser: true,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-09T10:00:00Z',
    updated_at: '2024-01-09T10:00:00Z'
  },
  {
    id: '10',
    name: 'Henry Anderson',
    username: 'henry.anderson',
    isPortalUser: false,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-10T10:00:00Z',
    updated_at: '2024-01-10T10:00:00Z'
  },
  {
    id: '11',
    name: 'Ivy Martinez',
    username: 'ivy.martinez',
    isPortalUser: false,
    role_id: '3',
    role: MOCK_ROLES[2],
    created_at: '2024-01-11T10:00:00Z',
    updated_at: '2024-01-11T10:00:00Z'
  },
  {
    id: '12',
    name: 'Jack Thompson',
    username: 'jack.thompson',
    isPortalUser: false,
    role_id: '2',
    role: MOCK_ROLES[1],
    created_at: '2024-01-12T10:00:00Z',
    updated_at: '2024-01-12T10:00:00Z'
  }
];

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const getUsers = async (
  params?: TUserParams
): Promise<TResponseListUsers> => {
  await delay(500);

  let filteredUsers = [...MOCK_USERS];

  if (params?.search) {
    filteredUsers = filteredUsers.filter(
      (user) =>
        user.name.toLowerCase().includes(params.search!.toLowerCase()) ||
        user.username.toLowerCase().includes(params.search!.toLowerCase())
    );
  }

  if (params?.role_id) {
    filteredUsers = filteredUsers.filter(
      (user) => user.role_id === params.role_id
    );
  }

  const page = params?.page || 1;
  const pageSize = params?.page_size || 10;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedUsers = filteredUsers.slice(startIndex, endIndex);

  return {
    message: 'Users retrieved successfully',
    data: paginatedUsers,
    pageCount: Math.ceil(filteredUsers.length / pageSize),
    page: page,
    pagination: {
      currentPage: page,
      total: filteredUsers.length,
      totalPage: Math.ceil(filteredUsers.length / pageSize),
      hasPreviousPage: page > 1,
      hasNextPage: endIndex < filteredUsers.length,
      page_size: pageSize,
      page: page,
      total_pages: Math.ceil(filteredUsers.length / pageSize)
    }
  };
};

export const getUserDetail = async (params: {
  id: string;
}): Promise<TResponseDetailUser> => {
  await delay(300);

  const user = MOCK_USERS.find((u) => u.id === params.id);

  if (!user) {
    throw new Error('User not found');
  }

  return {
    message: 'User detail retrieved successfully',
    data: user,
    pageCount: 1,
    page: 1
  };
};

export const createUser = async (
  req: TRequestCreateUser
): Promise<TDefaultResponse> => {
  await delay(800);

  const newUser: TUser = {
    id: (MOCK_USERS.length + 1).toString(),
    name: req.name,
    username: req.username,
    isPortalUser: req.isPortalUser,
    role_id: req.role_id,
    role: MOCK_ROLES.find((r) => r.id === req.role_id),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  MOCK_USERS.push(newUser);

  return {
    message: 'User created successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};

export const updateUser = async (
  req: TRequestUpdateUser,
  params: { id: string }
): Promise<TDefaultResponse> => {
  await delay(800);

  const userIndex = MOCK_USERS.findIndex((u) => u.id === params.id);

  if (userIndex === -1) {
    throw new Error('User not found');
  }

  MOCK_USERS[userIndex] = {
    ...MOCK_USERS[userIndex],
    name: req.name,
    username: req.username,
    isPortalUser: req.isPortalUser,
    role_id: req.role_id,
    role: MOCK_ROLES.find((r) => r.id === req.role_id),
    updated_at: new Date().toISOString()
  };

  return {
    message: 'User updated successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};

export const deleteUser = async (params: {
  id: string;
}): Promise<TDefaultResponse> => {
  await delay(500);

  const userIndex = MOCK_USERS.findIndex((u) => u.id === params.id);

  if (userIndex === -1) {
    throw new Error('User not found');
  }

  MOCK_USERS.splice(userIndex, 1);

  return {
    message: 'User deleted successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};

export const getRoles = async (
  params?: TRoleParams
): Promise<TResponseListRoles> => {
  await delay(400);

  let filteredRoles = [...MOCK_ROLES];

  if (params?.search) {
    filteredRoles = filteredRoles.filter((role) =>
      role.name.toLowerCase().includes(params.search!.toLowerCase())
    );
  }

  const page = params?.page || 1;
  const pageSize = params?.page_size || 10;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedRoles = filteredRoles.slice(startIndex, endIndex);

  return {
    message: 'Roles retrieved successfully',
    data: paginatedRoles,
    pageCount: Math.ceil(filteredRoles.length / pageSize),
    page: page,
    pagination: {
      currentPage: page,
      total: filteredRoles.length,
      totalPage: Math.ceil(filteredRoles.length / pageSize),
      hasPreviousPage: page > 1,
      hasNextPage: endIndex < filteredRoles.length,
      page_size: pageSize,
      page: page,
      total_pages: Math.ceil(filteredRoles.length / pageSize)
    }
  };
};

export const getRoleDetail = async (params: {
  id: string;
}): Promise<TResponseDetailRole> => {
  await delay(300);

  const role = MOCK_ROLES.find((r) => r.id === params.id);

  if (!role) {
    throw new Error('Role not found');
  }

  return {
    message: 'Role detail retrieved successfully',
    data: role,
    pageCount: 1,
    page: 1
  };
};

export const createRole = async (
  req: TRequestCreateRole
): Promise<TDefaultResponse> => {
  await delay(800);

  const newRole: TRole = {
    id: (MOCK_ROLES.length + 1).toString(),
    name: req.name,
    chat: req.chat,
    file_management: req.file_management,
    history: req.history,
    chat_attachment: req.chat_attachment,
    user_management: req.user_management,
    max_chat_topic: req.max_chat_topic,
    chat_topic_expired_days: req.chat_topic_expired_days,
    max_chat: req.max_chat,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };

  MOCK_ROLES.push(newRole);

  return {
    message: 'Role created successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};

export const updateRole = async (
  req: TRequestUpdateRole,
  params: { id: string }
): Promise<TDefaultResponse> => {
  await delay(800);

  const roleIndex = MOCK_ROLES.findIndex((r) => r.id === params.id);

  if (roleIndex === -1) {
    throw new Error('Role not found');
  }

  MOCK_ROLES[roleIndex] = {
    ...MOCK_ROLES[roleIndex],
    name: req.name,
    chat: req.chat,
    file_management: req.file_management,
    history: req.history,
    chat_attachment: req.chat_attachment,
    user_management: req.user_management,
    max_chat_topic: req.max_chat_topic,
    chat_topic_expired_days: req.chat_topic_expired_days,
    max_chat: req.max_chat,
    updated_at: new Date().toISOString()
  };

  return {
    message: 'Role updated successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};

export const deleteRole = async (params: {
  id: string;
}): Promise<TDefaultResponse> => {
  await delay(500);

  const roleIndex = MOCK_ROLES.findIndex((r) => r.id === params.id);

  if (roleIndex === -1) {
    throw new Error('Role not found');
  }

  const usersWithRole = MOCK_USERS.filter((u) => u.role_id === params.id);
  if (usersWithRole.length > 0) {
    throw new Error('Cannot delete role that is assigned to users');
  }

  MOCK_ROLES.splice(roleIndex, 1);

  return {
    message: 'Role deleted successfully',
    data: null,
    pageCount: 1,
    page: 1
  };
};
