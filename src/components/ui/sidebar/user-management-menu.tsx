import useGetUsers from '@/pages/(protected)/user-management/_hooks/get-users';
import { PersonIcon } from '@radix-ui/react-icons';
import { Link } from 'react-router-dom';

interface Props {
  isSidebarOpen: boolean;
}

const UserManagementMenu = ({ isSidebarOpen }: Props) => {
  const queryUsers = useGetUsers();

  return (
    <Link
      to="/user-management"
      className="flex items-center justify-between rounded-lg p-2 text-sm text-gray-700 hover:bg-gray-400/20"
    >
      {isSidebarOpen ? (
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            <PersonIcon className="font-bold" />
            <span className="truncate font-semibold">User Management</span>
          </div>
          <div className="w-12 rounded-full bg-[#B9B7C5] p-1 text-center text-xs text-[#5C47DB]">
            {queryUsers.data?.pagination?.total || 0}
          </div>
        </div>
      ) : (
        <PersonIcon className="font-bold" />
      )}
    </Link>
  );
};

export default UserManagementMenu;
