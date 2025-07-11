import { useEffect, useRef, useState } from 'react';
import {
  FileTextIcon,
  HamburgerMenuIcon,
  PlusIcon,
  TimerIcon,
  ExitIcon
} from '@radix-ui/react-icons';
import { Link, useLocation } from 'react-router-dom';
import { useGetFiles } from './_hook/use-get-history-chat';
import UserCard from '../user-card';
import { ScrollArea } from '../scroll-area';
import Cookies from 'js-cookie';

type TRecentChats = {
  session_id: string;
  title: string;
};

const Sidebar = ({ setShowModal }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const query = useGetFiles();
  const dataResult = query.data?.data as TRecentChats[] | undefined;
  const location = useLocation();
  const documentSideBar = Cookies.get('username') === 'admin';
  const topRef = useRef<HTMLDivElement | null>(null);
  const topHeight = topRef.current?.clientHeight;

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth > 760) {
        setIsSidebarOpen(true);
      } else {
        setIsSidebarOpen(false);
      }
    };
    window.addEventListener('resize', handleResize);
    handleResize();
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, []);

  return (
    <ScrollArea className={` h-screen max-h-screen bg-[#D2D2D2]`}>
      <aside
        className={`ease-[cubic-bezier(0.25, 0.8, 0.25, 1)] transition-all duration-300 ${isSidebarOpen ? 'w-[272px]' : 'w-[50px]'} `}
      >
        <div
          ref={topRef}
          className={`absolute left-0 right-0 top-0 w-full ${isSidebarOpen ? 'p-4' : 'p-2'} bg-[#D2D2D2]`}
        >
          <button
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-gray-400/20"
            onClick={toggleSidebar}
          >
            <HamburgerMenuIcon className="h-4 text-gray-800" />
          </button>
          {isSidebarOpen && (
            <div className="mt-2 transition-transform duration-300">
              <UserCard name="Pengguna" id="#12392832" />
            </div>
          )}
          <Link
            to="/new/chat"
            className="mt-2 flex w-full items-center gap-2 rounded-lg p-2 text-left hover:bg-gray-400/20"
          >
            {isSidebarOpen ? (
              <>
                <PlusIcon className="text-gray-800" />
                <span className="text-gradient-primary font-semibold">
                  New Chat
                </span>
              </>
            ) : (
              <PlusIcon className="text-gray-800" />
            )}
          </Link>
          {documentSideBar && (
            <Link
              to="/new/files"
              className="flex items-center justify-between rounded-lg p-2 text-sm text-gray-700 hover:bg-gray-400/20"
            >
              {isSidebarOpen ? (
                <div className="flex gap-2">
                  <FileTextIcon className="font-bold" />
                  <span className="truncate font-semibold">Document File</span>
                </div>
              ) : (
                <FileTextIcon className="font-bold" />
              )}
            </Link>
          )}
        </div>

        {isSidebarOpen && (
          <div
            className={`mb-[120px] mt-[${topHeight}px] w-full flex-grow px-4 `}
          >
            <h2 className="mb-2 p-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Recent Chat
            </h2>
            <nav>
              <ul>
                {Array.isArray(dataResult) && dataResult.length > 0 ? (
                  dataResult.map((chat: TRecentChats) => (
                    <li key={chat.session_id}>
                      <Link
                        to={`/new/chat/${chat.session_id}`}
                        className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${
                          location.pathname === `/new/chat/${chat.session_id}`
                            ? 'bg-gray-400/40 text-black'
                            : 'text-gray-700'
                        }`}
                        onClick={() => {
                          if (window.innerWidth < 768) {
                            setIsSidebarOpen(false);
                          }
                        }}
                      >
                        <span className="truncate">
                          {chat.title || 'Untitled Chat'}
                        </span>
                      </Link>
                    </li>
                  ))
                ) : (
                  <li className="p-2 text-sm text-gray-500">No recent chats</li>
                )}
              </ul>
            </nav>
          </div>
        )}
        <div
          className={`absolute bottom-0 left-0 right-0 mt-auto w-full  ${isSidebarOpen ? 'p-4' : 'p-2'} bg-[#D2D2D2]`}
        >
          <a
            href="#"
            className="flex items-center rounded-lg p-2 text-sm text-gray-600 hover:bg-neutral-300/60"
          >
            {isSidebarOpen ? (
              <>
                <TimerIcon className="mr-3 text-lg" />
                <span>See Full Chat History</span>
              </>
            ) : (
              <TimerIcon className="h-4 w-4 text-gray-700" />
            )}
          </a>
          <button
            onClick={() => setShowModal(true)}
            className="mt-4 flex w-full items-center gap-3 rounded-lg bg-slate-400 p-3 text-sm text-blue-600 hover:bg-[#E0E0E0]"
          >
            {isSidebarOpen ? (
              <span className="w-full text-center font-semibold">Logout</span>
            ) : (
              <ExitIcon className="h-6 w-6 text-gray-700" />
            )}
          </button>
        </div>
      </aside>
    </ScrollArea>
  );
};

export default Sidebar;
