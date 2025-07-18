import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';
import { useState } from 'react';
import { Link } from 'react-router-dom';

type Chat = {
  id: number;
  title: string;
  timestamp: string;
};

type TRecentChats = {
  session_id: string;
  title: string;
};

export default function ChatHistory() {
  const [selected, setSelected] = useState<string[]>([]);

  const query = useGetFiles();
  const dataHistory = query.data?.data as TRecentChats[] | undefined;

  const toggleSelect = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (dataHistory) {
      setSelected(dataHistory.map((chat) => chat.session_id));
    }
  };
  const handleClear = () => setSelected([]);
  const handleDelete = () => {
    alert(`Menghapus ${selected.length} obrolan`);
    setSelected([]);
  };

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
            className="w-full rounded bg-[#b4b3b3] px-4 py-2 text-white"
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
          {Array.isArray(dataHistory) && dataHistory.length > 0
            ? dataHistory.map((chat) => (
                <div
                  key={chat.session_id}
                  className={`group relative flex items-start gap-3 rounded-md border p-4 hover:cursor-pointer ${
                    selected.includes(chat.session_id)
                      ? 'border-blue-400 bg-[#d1d1d1]'
                      : 'border-[#333]'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selected.includes(chat?.session_id)}
                    onChange={() => toggleSelect(chat?.session_id)}
                    className="self-center"
                  />

                  <Link to={`/chat/${chat.session_id}`}>
                    <p className="font-medium">{chat.title}</p>
                    <p className="text-sm text-gray-400">
                      {/* Pesan terakhir {chat.timestamp} */}
                    </p>
                  </Link>
                  {selected.length == 0 && (
                    <button
                      onClick={() =>
                        alert(`Hapus obrolan ID ${chat.session_id}`)
                      }
                      className="absolute right-2 top-2 rounded bg-red-600 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100"
                    >
                      Hapus
                    </button>
                  )}
                </div>
              ))
            : null}
          {!query.isLoading && !dataHistory?.length && (
            <li className="p-2 text-sm text-gray-500">No recent chats</li>
          )}
        </div>
      </div>
    </main>
  );
}
