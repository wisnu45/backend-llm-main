import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import { MagnifyingGlassIcon } from '@radix-ui/react-icons';
import { TRole } from '@/api/user-management/type';

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

interface IUserManagementHeader {
  activeTab: 'users' | 'roles';
  setModal: (modal: TModal) => void;
  setInput: (event: React.ChangeEvent<HTMLInputElement>) => void;
  userType?: string;
  roleId?: string;
  onUserTypeChange?: (value: string) => void;
  onRoleChange?: (value: string) => void;
  roles?: TRole[];
}

const UserManagementHeader = ({
  activeTab,
  setModal,
  setInput,
  userType,
  roleId,
  onUserTypeChange,
  onRoleChange,
  roles
}: IUserManagementHeader) => {
  const isUsersTab = activeTab === 'users';

  return (
    <>
      <div className="mb-8 flex flex-wrap items-center justify-between">
        <div className="w-full sm:w-auto">
          <h1 className="text-3xl font-bold text-gray-800 sm:text-2xl">
            User Management
          </h1>
          <p className="text-gray-600 sm:text-sm">
            Manage system users and role permissions
          </p>
        </div>
      </div>

      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex w-full flex-wrap items-center gap-4 sm:w-auto">
          <div className="flex w-full items-center overflow-hidden rounded-lg border border-gray-300 bg-white shadow-sm sm:w-auto">
            <input
              type="text"
              placeholder={`Search ${isUsersTab ? 'by username' : 'roles'}...`}
              onChange={setInput}
              className="w-full rounded-l-lg px-4 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-64"
            />
            <button className="rounded-r-lg border-l border-gray-300 bg-gray-50 p-2 hover:bg-gray-100">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-500" />
            </button>
          </div>

          {isUsersTab && (
            <>
              <Select value={userType} onValueChange={onUserTypeChange}>
                <SelectTrigger className="w-full bg-white sm:w-[180px]">
                  <SelectValue placeholder="User Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Users</SelectItem>
                  <SelectItem value="portal">Portal Users</SelectItem>
                  <SelectItem value="local">Local Users</SelectItem>
                </SelectContent>
              </Select>

              <Select value={roleId || 'all'} onValueChange={onRoleChange}>
                <SelectTrigger className="w-full bg-white sm:w-[180px]">
                  <SelectValue placeholder="All Roles" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  {roles?.map((role) => (
                    <SelectItem key={role.id} value={String(role.id)}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </>
          )}
        </div>

        <Button
          className="w-full bg-green-500 hover:bg-green-600 sm:w-auto"
          onClick={() => setModal(isUsersTab ? 'create-user' : 'create-role')}
        >
          {isUsersTab ? 'Add New User' : 'Add New Role'}
        </Button>
      </div>
    </>
  );
};

export default UserManagementHeader;
