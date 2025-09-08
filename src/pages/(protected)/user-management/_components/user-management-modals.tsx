import { useEffect } from 'react';
import UserFormModal from './user-form-modal';
import RoleFormModal from './role-form-modal';
import UserDetailModal from './user-detail-modal';
import RoleDetailModal from './role-detail-modal';
import DeleteModal from './delete-modal';
import useCreateUser from '../_hooks/create-user';
import useUpdateUser from '../_hooks/update-user';
import useDeleteUser from '../_hooks/delete-user';
import useCreateRole from '../_hooks/create-role';
import useUpdateRole from '../_hooks/update-role';
import useDeleteRole from '../_hooks/delete-role';
import useGetUserDetail from '../_hooks/get-user-detail';
import useGetRoleDetail from '../_hooks/get-role-detail';
import { TUser, TRole, TRequestCreateUser } from '@/api/user-management/type';

type TModal =
  | 'delete-user'
  | 'delete-role'
  | 'edit-user'
  | 'edit-role'
  | 'create-user'
  | 'create-role'
  | 'detail-user'
  | 'detail-role'
  | null;

interface IUserManagementModals {
  modal: TModal;
  setModal: (modal: TModal) => void;
  userData: TUser | null;
  roleData: TRole | null;
}

const UserManagementModals = ({
  modal,
  setModal,
  userData,
  roleData
}: IUserManagementModals) => {
  const createUserMutation = useCreateUser();
  const updateUserMutation = useUpdateUser(userData?.id);
  const deleteUserMutation = useDeleteUser();

  const createRoleMutation = useCreateRole();
  const updateRoleMutation = useUpdateRole(roleData?.id);
  const deleteRoleMutation = useDeleteRole();

  const userDetailQuery = useGetUserDetail(userData?.id);
  const roleDetailQuery = useGetRoleDetail(roleData?.id);

  useEffect(() => {
    if (modal && modal.includes('user') && modal !== 'create-user') {
      userDetailQuery.refetch();
    }
    if (modal && modal.includes('role') && modal !== 'create-role') {
      roleDetailQuery.refetch();
    }
  }, [modal, userDetailQuery, roleDetailQuery]);

  return (
    <>
      {/* User Modals */}
      <UserFormModal
        open={modal === 'create-user'}
        mode="create"
        loading={createUserMutation.isPending}
        onOpenChange={() => setModal(null)}
        onSubmit={(data) => {
          createUserMutation.mutate(data as TRequestCreateUser, {
            onSuccess: () => setModal(null)
          });
        }}
      />

      <UserFormModal
        key={userDetailQuery.data?.data.id}
        open={modal === 'edit-user'}
        mode="edit"
        loading={updateUserMutation.isPending}
        onOpenChange={() => setModal(null)}
        onSubmit={(data) => {
          updateUserMutation.mutate(data, {
            onSuccess: () => setModal(null)
          });
        }}
        defaultValues={{
          name: userDetailQuery.data?.data.name,
          username: userDetailQuery.data?.data.username,
          isPortalUser: userDetailQuery.data?.data.isPortalUser,
          role_id: userDetailQuery.data?.data.role_id
        }}
      />

      <UserDetailModal
        open={modal === 'detail-user'}
        onOpenChange={() => setModal(null)}
        data={userDetailQuery.data?.data}
        onDelete={() => setModal('delete-user')}
        onEdit={() => setModal('edit-user')}
      />

      {/* Role Modals */}
      <RoleFormModal
        open={modal === 'create-role'}
        mode="create"
        loading={createRoleMutation.isPending}
        onOpenChange={() => setModal(null)}
        onSubmit={(data) => {
          createRoleMutation.mutate(data, {
            onSuccess: () => setModal(null)
          });
        }}
      />

      <RoleFormModal
        key={roleDetailQuery.data?.data.id}
        open={modal === 'edit-role'}
        mode="edit"
        loading={updateRoleMutation.isPending}
        onOpenChange={() => setModal(null)}
        onSubmit={(data) => {
          updateRoleMutation.mutate(data, {
            onSuccess: () => setModal(null)
          });
        }}
        defaultValues={{
          name: roleDetailQuery.data?.data.name,
          chat: roleDetailQuery.data?.data.chat,
          file_management: roleDetailQuery.data?.data.file_management,
          history: roleDetailQuery.data?.data.history,
          chat_attachment: roleDetailQuery.data?.data.chat_attachment,
          user_management: roleDetailQuery.data?.data.user_management,
          max_chat_topic: roleDetailQuery.data?.data.max_chat_topic,
          chat_topic_expired_days:
            roleDetailQuery.data?.data.chat_topic_expired_days,
          max_chat: roleDetailQuery.data?.data.max_chat
        }}
      />

      <RoleDetailModal
        open={modal === 'detail-role'}
        onOpenChange={() => setModal(null)}
        data={roleDetailQuery.data?.data}
        onDelete={() => setModal('delete-role')}
        onEdit={() => setModal('edit-role')}
      />

      {/* Delete Modals */}
      <DeleteModal
        open={modal === 'delete-user'}
        title="Delete User"
        itemName={userDetailQuery.data?.data.name || userData?.name}
        loading={deleteUserMutation.isPending}
        onDelete={() => {
          const id = userDetailQuery.data?.data.id || userData?.id;
          deleteUserMutation.mutate(
            { id: id! },
            {
              onSuccess: () => setModal(null)
            }
          );
        }}
        onOpenChange={() => setModal(null)}
      />

      <DeleteModal
        open={modal === 'delete-role'}
        title="Delete Role"
        itemName={roleDetailQuery.data?.data.name || roleData?.name}
        loading={deleteRoleMutation.isPending}
        onDelete={() => {
          const id = roleDetailQuery.data?.data.id || roleData?.id;
          deleteRoleMutation.mutate(
            { id: id! },
            {
              onSuccess: () => setModal(null)
            }
          );
        }}
        onOpenChange={() => setModal(null)}
      />
    </>
  );
};

export default UserManagementModals;
