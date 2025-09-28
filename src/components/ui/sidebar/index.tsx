import { DropdownMenuTrigger } from '@radix-ui/react-dropdown-menu';
import {
  HamburgerMenuIcon,
  MagnifyingGlassIcon,
  PlusIcon
} from '@radix-ui/react-icons';
import Cookies from 'js-cookie';
import { Edit, MoreVertical, Pin, PinOff, TrashIcon } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { AlertModal } from '../../shared/alert-modal';
import RenameModal from '../alert-edit';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuShortcut
} from '../dropdown-menu';
import { ScrollArea } from '../scroll-area';
import { Skeleton } from '../skeleton';
import UserCard from '../user-card';
import { useDeleteChat } from './_hook/use-delete-chat';
import { useGetFiles } from './_hook/use-get-history-chat';
import { useGetMenuBar } from './_hook/use-get-menubar';
import { usePinChat } from './_hook/use-pin-chat';
import { useRenameChat } from './_hook/use-rename-chat';
import DocumentMenu from './document-menu';
import UserManagementMenu from './user-management-menu';
import SeeFullHistory from './see-full-menu';

const Sidebar = ({ setShowModal }) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const query = useGetFiles();
  const dataResult = query.data?.data || [];
  const [topHeight, setTopHeight] = useState<number>();
  const location = useLocation();
  const topRef = useRef<HTMLDivElement | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showEditName, setShowEditName] = useState(false);
  const [active, setActive] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [chatId, setChatId] = useState<string | null>(null);
  const [activeChat, setActiveChat] = useState<string | null>(null);
  const navigate = useNavigate();
  const params = useParams();

  const deleteMutation = useDeleteChat();
  const renameMutation = useRenameChat();
  const pinMutation = usePinChat();
  const getMenuBar = useGetMenuBar();
  const queryClient = useQueryClient();

  const menuSidebar = getMenuBar?.data?.data;

  const getMenuValue = (name) =>
    menuSidebar?.find((menu) => menu.name === name)?.value || false;

  const documentSideBarMenu = getMenuValue('Menu document');
  const settingSideBarMenu = getMenuValue('Menu setting');
  const userSideBarMenu = getMenuValue('Menu user');

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

  const [textSearch, setTextSearch] = useState<string>('');

  const filteredData = dataResult?.filter((item) =>
    item.title.toLowerCase().includes(textSearch.toLowerCase())
  );

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
          <div className="flex items-center justify-between">
            {isSidebarOpen && (
              <Link to="/">
                <img src="/combiphar.png" className="h-auto max-w-24" />
              </Link>
            )}
            <button
              className="flex h-8 w-8 items-center justify-center rounded-lg hover:bg-gray-400/20"
              onClick={toggleSidebar}
            >
              <HamburgerMenuIcon className="h-4 text-gray-800" />
            </button>
          </div>
          {isSidebarOpen && (
            <>
              <div className="mt-2 transition-transform duration-300">
                <UserCard
                  name={Cookies.get('name') || ''}
                  id={Cookies.get('role') || ''}
                />
              </div>
            </>
          )}

          <Link
            to="/chat"
            onClick={() => {
              Cookies.remove('chat_id');
            }}
            className={`mt-2 flex w-full items-center gap-2 rounded-lg p-2 text-left hover:bg-gray-400/20 ${
              location.pathname === '/chat'
                ? 'bg-gray-400/40 text-black'
                : 'text-gray-700'
            }`}
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
          {isSidebarOpen ? (
            <div className="mb-2 mt-2 pl-2">
              <input
                type="text"
                placeholder="Search Chat"
                className="w-full rounded-lg border border-gray-300 bg-gray-400/20 p-2 text-sm focus:border-blue-500 focus:outline-none"
                onChange={(e) => setTextSearch(e.target.value)}
              />
            </div>
          ) : (
            <Link
              to=""
              onClick={toggleSidebar}
              className={`mt-2 flex w-full items-center gap-2 rounded-lg bg-gray-400/40 p-2 text-left text-black hover:bg-gray-400/20`}
            >
              <MagnifyingGlassIcon className="text-gray-800" />
            </Link>
          )}
          {isSidebarOpen && (
            <h2 className="mb-2 p-2 text-xs font-semibold uppercase tracking-wider text-gray-500">
              Recent Chat
            </h2>
          )}
        </div>
        {isSidebarOpen && (
          <div
            className="mb-[120px]  w-full overflow-auto px-4"
            style={{
              marginTop: topHeight,
              maxHeight: `calc(100vh - ${topHeight}px - 120px)`
            }}
          >
            <nav>
              <ul className="overflow-hidde">
                {query.isLoading && (
                  <li>
                    <Skeleton className="h-8 w-full" />
                  </li>
                )}
                {dataResult.length > 0
                  ? (filteredData ?? []).map((chat) => (
                      <div key={chat.chat_id}>
                        <li key={chat.chat_id} className="group/outer relative">
                          <DropdownMenu
                            onOpenChange={(open) => {
                              if (!open) setActive(null);
                            }}
                          >
                            <Link
                              to={`/chat/${chat.chat_id}`}
                              className={`flex items-center justify-between rounded-lg p-2 text-sm hover:bg-gray-400/20 ${active === chat.chat_id ? 'bg-gray-400/30' : ''} ${
                                location.pathname === `/chat/${chat.chat_id}`
                                  ? 'bg-gray-400/40 text-black'
                                  : 'text-gray-700'
                              }`}
                              onClick={() => {
                                if (window.innerWidth < 768) {
                                  setIsSidebarOpen(false);
                                }
                              }}
                              onMouseEnter={() => setActive(chat.chat_id)}
                              onMouseLeave={() => setActive(null)}
                            >
                              <span className="flex w-11/12 items-center gap-1">
                                {chat.pinned && (
                                  <Pin className="h-3 w-3 flex-shrink-0 text-blue-500" />
                                )}
                                <span className="truncate">
                                  {chat.title || 'Untitled Chat'}
                                </span>
                              </span>
                            </Link>
                            <DropdownMenuTrigger asChild>
                              <button
                                className={`group/inner absolute right-1 top-1/2 h-6 w-6 -translate-y-1/2 cursor-pointer rounded-full hover:bg-slate-700/10 ${active === chat.chat_id ? 'bg-slate-700/10' : ''}`}
                                aria-label="More options"
                                onClick={() => setActive(chat.chat_id)}
                                onMouseEnter={() => setActive(chat.chat_id)}
                              >
                                <MoreVertical
                                  style={{
                                    opacity: active === chat.chat_id ? 100 : 0
                                  }}
                                  className="h-4  "
                                />
                              </button>
                            </DropdownMenuTrigger>

                            <DropdownMenuContent side="bottom" align="end">
                              <DropdownMenuItem
                                className="cursor-pointer"
                                onClick={() => {
                                  setActiveId(chat.chat_id);
                                  setShowDeleteModal(true);
                                }}
                              >
                                Delete
                                <DropdownMenuShortcut>
                                  <TrashIcon className="h-4 text-red-500" />
                                </DropdownMenuShortcut>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="cursor-pointer"
                                onClick={() => {
                                  setActiveId(chat.chat_id);
                                  setChatId(chat.id);
                                  setActiveChat(chat.title);
                                  setShowEditName(true);
                                }}
                              >
                                Rename{' '}
                                <DropdownMenuShortcut>
                                  <Edit className="h-4 text-blue-500" />
                                </DropdownMenuShortcut>
                              </DropdownMenuItem>
                              <DropdownMenuItem
                                className="cursor-pointer"
                                onClick={() => {
                                  pinMutation.mutate(
                                    {
                                      chat_id: chat.id,
                                      pinned: !chat.pinned
                                    },
                                    {
                                      onSuccess: () => {
                                        query.refetch();
                                      }
                                    }
                                  );
                                }}
                              >
                                {chat.pinned ? 'Unpin' : 'Pin'}
                                <DropdownMenuShortcut>
                                  {chat.pinned ? (
                                    <PinOff className="h-4 text-blue-500" />
                                  ) : (
                                    <Pin className="h-4 text-blue-500" />
                                  )}
                                </DropdownMenuShortcut>
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </li>
                      </div>
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
          <SeeFullHistory isSidebarOpen={isSidebarOpen} />
          {documentSideBarMenu && (
            <DocumentMenu isSidebarOpen={isSidebarOpen} />
          )}
          {userSideBarMenu && (
            <UserManagementMenu isSidebarOpen={isSidebarOpen} />
          )}

          {settingSideBarMenu && (
            <Link
              to="/setting"
              className="flex items-center gap-3 rounded-lg p-2 text-sm text-gray-600 transition-colors duration-200 hover:bg-neutral-300/60"
            >
              <img
                src="/icons/setting.png"
                alt="See more history"
                className="h-4 w-4"
              />
              {isSidebarOpen && <span className="truncate">Setting</span>}
            </Link>
          )}
          <button
            onClick={() => setShowModal(true)}
            className={`mt-4 flex w-full items-center gap-3 rounded-lg bg-slate-400 p-2 text-sm text-[#5C47DB] transition-colors duration-200 hover:bg-[#E0E0E0]`}
          >
            <img
              src="/icons/logout_icon.png"
              alt="Logout icon"
              className="h-4 w-4"
            />
            {isSidebarOpen && <span className="font-semibold">Log out</span>}
          </button>
        </div>
      </aside>

      <AlertModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => {
          deleteMutation.mutate(
            { chat_id: activeId! },
            {
              onSuccess: () => {
                setShowDeleteModal(false);
                query.refetch();
                queryClient.invalidateQueries({
                  queryKey: ['fetch-setting-feature'],
                  type: 'all'
                });
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
      <RenameModal
        isOpen={showEditName}
        onClose={() => setShowEditName(false)}
        initialValue={activeChat || ''}
        onConfirm={(newName) => {
          renameMutation.mutate(
            { chat_id: chatId!, title: newName },
            {
              onSuccess: () => {
                setShowEditName(false);
                query.refetch();
              }
            }
          );
        }}
        loading={renameMutation.isPending}
        title="Rename Chat"
        description="Enter a new name for this chat."
      />
    </ScrollArea>
  );
};

export default Sidebar;
