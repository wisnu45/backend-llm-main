import { Link, useLocation } from 'react-router-dom';

interface Props {
  isSidebarOpen: boolean;
}

const SettingMenu = ({ isSidebarOpen }: Props) => {
  const location = useLocation();
  const isActive = location.pathname === '/setting';

  return (
    <Link
      to="/setting"
      className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${
        isActive ? 'bg-gray-400/40 text-black' : 'text-gray-700'
      }`}
    >
      {isSidebarOpen ? (
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            <img
              src="/icons/setting.png"
              alt="See more history"
              className="h-4 w-4"
            />
            <span className="truncate font-semibold">Setting</span>
          </div>
        </div>
      ) : (
        <img
          src="/icons/setting.png"
          alt="See more history"
          className="h-4 w-4"
        />
      )}
    </Link>
  );
};

export default SettingMenu;
