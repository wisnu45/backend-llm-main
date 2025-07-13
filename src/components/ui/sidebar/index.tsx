import { useEffect, useRef, useState } from 'react';
import {
  FileTextIcon,
  HamburgerMenuIcon,
  PlusIcon
} from '@radix-ui/react-icons';
import { Link, useLocation } from 'react-router-dom';
import { useGetFiles } from './_hook/use-get-history-chat';
import UserCard from '../user-card';
import { ScrollArea } from '../scroll-area';
import Cookies from 'js-cookie';
import { Skeleton } from '../skeleton';
import useGetListDocument from '@/pages/new/files/_hooks/get-list-document';

type TRecentChats = {
  session_id: string;
  title: string;
};

const Sidebar = ({ setShowModal }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const query = useGetFiles();
  const queryDocument = useGetListDocument('', 1, 10);
  const dataResult = query.data?.data as TRecentChats[] | undefined;
  const [topHeight, setTopHeight] = useState<number>();
  const location = useLocation();
  const documentSideBar = Cookies.get('username') === 'admin';
  const topRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    requestAnimationFrame(() => {
      if (topRef.current) {
        setTopHeight(topRef.current.clientHeight);
      }
    });
  }, []);

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
    <ScrollArea
      className={` h-screen max-h-screen bg-[#D2D2D2] hide-scrollbar`}
    >
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
                <div className="flex w-full items-center justify-between">
                  <div className="flex gap-2">
                    <FileTextIcon className="font-bold" />
                    <span className="truncate font-semibold">
                      Document File
                    </span>
                  </div>
                  <div className="w-12 rounded-full bg-[#B9B7C5] p-1 text-center text-xs text-[#5C47DB]">
                    {queryDocument.data?.pagination?.total || 0}
                  </div>
                </div>
              ) : (
                <FileTextIcon className="font-bold" />
              )}
            </Link>
          )}
        </div>

        {isSidebarOpen && (
          <div
            className={`mb-[120px]  w-full flex-grow px-4 `}
            style={{
              marginTop: topHeight
            }}
          >
            <h2 className="mb-2 p-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Recent Chat
            </h2>
            <nav>
              <ul>
                {query.isLoading && (
                  <li>
                    <Skeleton className="h-8 w-full" />
                  </li>
                )}
                {Array.isArray(dataResult) && dataResult.length > 0
                  ? dataResult.map((chat: TRecentChats) => (
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
                  : null}
                {!query.isLoading && !dataResult?.length && (
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
            className="flex items-center justify-between gap-3 rounded-lg p-2 text-sm text-gray-600 transition-colors duration-200 hover:bg-neutral-300/60"
          >
            {isSidebarOpen && (
              <span className="truncate">See Full Chat History</span>
            )}
            <img
              src="/icons/see_more_icon.png"
              alt="See more history"
              className="h-4 w-4"
            />
          </a>
          <button
            onClick={() => setShowModal(true)}
            className={`mt-4 flex w-full items-center gap-3 rounded-lg bg-slate-400 p-2 text-sm text-[#5C47DB] transition-colors duration-200 hover:bg-[#E0E0E0]`}
          >
            <img
              src="/icons/logout_icon.png"
              alt="Logout icon"
              className="h-4 w-4"
            />
            {isSidebarOpen && <span className="font-semibold">Logout</span>}
          </button>
        </div>
      </aside>
    </ScrollArea>
  );
};

export default Sidebar;
