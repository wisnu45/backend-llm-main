import { useEffect, useRef, useState } from 'react';
import { HamburgerMenuIcon, PlusIcon } from '@radix-ui/react-icons';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useGetFiles } from './_hook/use-get-history-chat';
import UserCard from '../user-card';
import { ScrollArea } from '../scroll-area';
import Cookies from 'js-cookie';
import { Skeleton } from '../skeleton';
import { AlertModal } from '../../shared/alert-modal';
import { MoreVertical, TrashIcon } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuShortcut
} from '../dropdown-menu';
import { DropdownMenuTrigger } from '@radix-ui/react-dropdown-menu';
import { useDeleteChat } from './_hook/use-delete-chat';
import DocumentMenu from './document-menu';

type TRecentChats = {
  session_id: string;
  title: string;
};

const Sidebar = ({ setShowModal }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const query = useGetFiles();
  const dataResult = query.data?.data as TRecentChats[] | undefined;
  const [topHeight, setTopHeight] = useState<number>();
  const location = useLocation();
  const documentSideBar = Cookies.get('role') === 'admin';

  const topRef = useRef<HTMLDivElement | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const navigate = useNavigate();
  const params = useParams();

  const deleteMutation = useDeleteChat();

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
          className={`absolute left-0 right-0 top-0 w-full ${isSidebarOpen ? 'p-4' : 'p-2'} bg-[#D2D2D2] pb-0`}
        >
          <button
            className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-gray-400/20"
            onClick={toggleSidebar}
          >
            <HamburgerMenuIcon className="h-4 text-gray-800" />
          </button>
          {isSidebarOpen && (
            <div className="mt-2 transition-transform duration-300">
              <UserCard
                name={Cookies.get('name') || ''}
                id={Cookies.get('role') || ''}
              />
            </div>
          )}

          <Link
            to="/chat"
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
          {documentSideBar && <DocumentMenu isSidebarOpen={isSidebarOpen} />}

          {isSidebarOpen && (
            <h2 className="mb-2 p-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Recent Chat
            </h2>
          )}
        </div>

        {isSidebarOpen && (
          <div
            className={`mb-[120px]  w-full flex-grow px-4 `}
            style={{
              marginTop: topHeight
            }}
          >
            <nav>
              <ul>
                {query.isLoading && (
                  <li>
                    <Skeleton className="h-8 w-full" />
                  </li>
                )}
                {Array.isArray(dataResult) && dataResult.length > 0
                  ? dataResult.map((chat: TRecentChats) => (
                      <li
                        key={chat.session_id}
                        className="group/outer relative"
                      >
                        <DropdownMenu
                          onOpenChange={(open) => {
                            if (!open) setActive(null);
                          }}
                        >
                          <Link
                            to={`/chat/${chat.session_id}`}
                            className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${active === chat.session_id ? 'bg-gray-400/30' : ''} ${
                              location.pathname === `/chat/${chat.session_id}`
                                ? 'bg-gray-400/40 text-black'
                                : 'text-gray-700'
                            }`}
                            onClick={() => {
                              if (window.innerWidth < 768) {
                                setIsSidebarOpen(false);
                              }
                            }}
                            onMouseEnter={() => setActive(chat.session_id)}
                            onMouseLeave={() => setActive(null)}
                          >
                            <span className="w-11/12 truncate">
                              {chat.title || 'Untitled Chat'}
                            </span>
                          </Link>
                          <DropdownMenuTrigger asChild>
                            <button
                              className={`group/inner absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 cursor-pointer rounded-full hover:bg-slate-700/10 ${active === chat.session_id ? 'bg-slate-700/10' : ''}`}
                              aria-label="More options"
                              onClick={() => setActive(chat.session_id)}
                              onMouseEnter={() => setActive(chat.session_id)}
                            >
                              <MoreVertical
                                style={{
                                  opacity: active === chat.session_id ? 100 : 0
                                }}
                                className="h-4  "
                              />
                            </button>
                          </DropdownMenuTrigger>

                          <DropdownMenuContent side="bottom" align="end">
                            <DropdownMenuItem
                              className="cursor-pointer"
                              onClick={() => {
                                setActiveId(chat.session_id);
                                setShowDeleteModal(true);
                              }}
                            >
                              Delete
                              <DropdownMenuShortcut>
                                <TrashIcon className="h-4 text-red-500" />
                              </DropdownMenuShortcut>
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
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
          <Link
            to="/history"
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
          </Link>
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

      <AlertModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => {
          deleteMutation.mutate(
            { session_id: activeId! },
            {
              onSuccess: () => {
                setShowDeleteModal(false);
                query.refetch();
                if (activeId === params.chatId) {
                  navigate('/chat');
                }
              }
            }
          );
        }}
        loading={deleteMutation.isPending}
        title="Delete Chat"
        description="Are you sure you want to delete this chat? This action cannot be undone."
      />
    </ScrollArea>
  );
};

export default Sidebar;
