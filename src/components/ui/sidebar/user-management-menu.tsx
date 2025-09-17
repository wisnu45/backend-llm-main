import { PersonIcon } from '@radix-ui/react-icons';
import { Link, useLocation } from 'react-router-dom';

interface Props {
  isSidebarOpen: boolean;
}

const UserManagementMenu = ({ isSidebarOpen }: Props) => {
  const location = useLocation();
  const isActive = location.pathname === '/user-management';

  return (
    <Link
      to="/user-management"
      className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${
        isActive ? 'bg-gray-400/40 text-black' : 'text-gray-700'
      }`}
    >
      {isSidebarOpen ? (
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            <PersonIcon className="font-bold" />
            <span className="truncate font-semibold">User Management</span>
          </div>
        </div>
      ) : (
        <PersonIcon className="font-bold" />
      )}
    </Link>
  );
};

export default UserManagementMenu;
