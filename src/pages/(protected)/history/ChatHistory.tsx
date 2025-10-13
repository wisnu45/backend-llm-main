import { AlertModal } from '@/components/shared/alert-modal';
import { useDeleteChat } from '@/components/ui/sidebar/_hook/use-delete-chat';
import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';
import { TrashIcon } from 'lucide-react';
import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useBulkDeleteChat } from './_hook/use-delete-bulk-chat';

type TRecentChats = {
  chat_id: string;
  title: string;
};

export default function ChatHistory() {
  const [selected, setSelected] = useState<string[]>([]);

  const query = useGetFiles();
  const dataHistory = query.data?.data as TRecentChats[] | undefined;
  const [activeId, setActiveId] = useState<string | null>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const params = useParams();
  const deleteBulkChat = useBulkDeleteChat();

  const toggleSelect = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const handleSelectAll = () => {
    if (dataHistory) {
      setSelected(dataHistory.map((chat) => chat.chat_id));
    }
  };
  const handleClear = () => setSelected([]);
  const handleDelete = () => {
    deleteBulkChat.mutate(
      { chat_ids: selected },
      {
        onSuccess: () => {
          setSelected([]);
          query.refetch();
          alert(`Berhasil menghapus sejumlah ${selected.length} obrolan`);
        },
        onError: (error) => {
          console.error('Error deleting chats:', error);
        }
      }
    );
    setSelected([]);
  };
  const navigate = useNavigate();
  const deleteMutation = useDeleteChat();

  const filteredChats = dataHistory?.filter((chat) =>
    chat.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <main className="min-h-screen px-6 py-10 text-black">
      <div className="mx-auto max-w-3xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Riwayat obrolan Anda</h1>
          <Link
            to={'/chat'}
            className="rounded bg-white px-4 py-2 font-medium text-black"
          >
            + Chat baru
          </Link>
        </div>
        <div className="mb-4">
          <input
            type="text"
            placeholder="Cari obrolan Anda..."
            onChange={handleInput}
            className="w-full rounded bg-white px-4 py-2 text-black"
          />
        </div>
        {selected.length > 0 && (
          <div className="mb-4 flex items-center gap-3 text-sm text-white">
            <span className="text-blue-400">
              {selected.length} obrolan dipilih
            </span>
            <button onClick={handleSelectAll} className="text-blue-400">
              Pilih semua
            </button>
            <button
              onClick={handleClear}
              className="rounded bg-[#333] px-3 py-1"
            >
              Batalkan
            </button>
            <button
              onClick={handleDelete}
              className="rounded bg-red-600 px-3 py-1"
            >
              Hapus Pilihan
            </button>
          </div>
        )}
        <div className="space-y-2">
          {Array.isArray(filteredChats) && filteredChats.length > 0
            ? filteredChats.map((chat) => (
                <div
                  key={chat.chat_id}
                  className={`group relative flex items-start gap-3 rounded-md border p-4 hover:cursor-pointer ${
                    selected.includes(chat.chat_id)
                      ? 'border-blue-400 bg-[#d1d1d1]'
                      : 'border-[#333]'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(chat?.chat_id)}
                    onChange={() => toggleSelect(chat?.chat_id)}
                    className="self-center"
                  />

                  <Link to={`/chat/${chat.chat_id}`}>
                    <p className="font-medium">{chat.title}</p>
                    <p className="text-sm text-gray-400">
                      {/* Pesan terakhir {chat.timestamp} */}
                    </p>
                  </Link>
                  {selected.length == 0 && (
                    <button
                      onClick={() => {
                        setActiveId(chat.chat_id);
                        setShowDeleteModal(true);
                      }}
                      className="absolute right-2 top-2  px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      <TrashIcon className="h-4 text-red-500" />
                    </button>
                  )}
                </div>
              ))
            : null}
          {!query.isLoading && !filteredChats?.length && (
            <li className="p-2 text-sm text-gray-500">No recent chats</li>
          )}
        </div>
      </div>
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
    </main>
  );
}
