import { TRequestCreateUser, TRole, TUser } from '@/api/user-management/type';
import { useEffect } from 'react';
import useCreateRole from '../_hooks/create-role';
import useCreateUser from '../_hooks/create-user';
import useDeleteRole from '../_hooks/delete-role';
import useDeleteUser from '../_hooks/delete-user';
import useGetUserDetail from '../_hooks/get-user-detail';
import useSaveRoleSettings from '../_hooks/save-role-settings';
import useUpdateRole from '../_hooks/update-role';
import useUpdateUser from '../_hooks/update-user';
import DeleteModal from './delete-modal';
import RoleDetailModal from './role-detail-modal';
import RoleFormModal from './role-form-modal';
import RoleSettingsModal from './role-settings-modal';
import UserDetailModal from './user-detail-modal';
import UserFormModal from './user-form-modal';

type TModal =
  | 'delete-user'
  | 'delete-role'
  | 'edit-user'
  | 'edit-role'
  | 'create-user'
  | 'create-role'
  | 'detail-user'
  | 'detail-role'
  | 'setting-role'
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
  const updateRoleMutation = useUpdateRole(roleData?.id?.toString());
  const deleteRoleMutation = useDeleteRole();
  const saveRoleSettingsMutation = useSaveRoleSettings();

  const userDetailQuery = useGetUserDetail(userData?.id);

  useEffect(() => {
    if (modal && modal.includes('user') && modal !== 'create-user') {
      userDetailQuery.refetch();
    }
  }, [modal, userDetailQuery]);

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
          is_portal: userDetailQuery.data?.data.is_portal,
          role: userDetailQuery.data?.data.role
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
        key={roleData?.id}
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
          name: roleData?.name,
          description: roleData?.description,
          is_local: roleData?.is_local,
          is_portal: roleData?.is_portal
        }}
      />

      <RoleDetailModal
        open={modal === 'detail-role'}
        onOpenChange={() => setModal(null)}
        data={roleData || null}
        onDelete={() => setModal('delete-role')}
        onEdit={() => setModal('edit-role')}
      />

      <RoleSettingsModal
        open={modal === 'setting-role'}
        onOpenChange={() => setModal(null)}
        roleData={roleData}
        loading={saveRoleSettingsMutation.isPending}
        onSave={(settings) => {
          saveRoleSettingsMutation.mutate(settings, {
            onSuccess: () => setModal(null)
          });
        }}
      />
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
        itemName={roleData?.name}
        loading={deleteRoleMutation.isPending}
        onDelete={() => {
          const id = roleData?.id;
          deleteRoleMutation.mutate(
            { id: id?.toString()! },
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
