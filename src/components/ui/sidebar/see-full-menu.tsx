import { Link, useLocation } from 'react-router-dom';

interface Props {
  isSidebarOpen: boolean;
}

const SeeFullHistory = ({ isSidebarOpen }: Props) => {
  const location = useLocation();
  const isActive = location.pathname === '/history';

  return (
    <Link
      to="/history"
      className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${
        isActive ? 'bg-gray-400/40 text-black' : 'text-gray-700'
      }`}
    >
      {isSidebarOpen ? (
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            <img
              src="/icons/see_more_icon.png"
              alt="See more history"
              className="h-4 w-4"
            />
            <span className="truncate font-semibold">
              See Full Chat History
            </span>
          </div>
        </div>
      ) : (
        <img
          src="/icons/see_more_icon.png"
          alt="See more history"
          className="h-4 w-4"
        />
      )}
    </Link>
  );
};

export default SeeFullHistory;
