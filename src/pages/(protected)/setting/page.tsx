import { PencilIcon } from 'lucide-react';

type TSetting = {
  config: string;
  desc: string;
  type: 'General' | 'Feature';
  value: string;
};

const dummySettings: TSetting[] = [
  {
    config: 'Chat max text',
    desc: 'Maksimum text yang dapat diketik',
    type: 'General',
    value: '1000'
  },
  {
    config: 'Chat Greeting',
    desc: 'Sapaan chat baru',
    type: 'General',
    value: 'Hai, [username] Apa yang bisa Vita...'
  },
  {
    config: 'Prompt Example',
    desc: 'Contoh2 prompt',
    type: 'General',
    value: 'xxxx; xxxxx; xxxxx'
  },
  {
    config: 'Attachment',
    desc: 'Attachment on/off',
    type: 'Feature',
    value: 'on/off'
  },
  {
    config: 'Attachment File Types',
    desc: 'Attachment allowed file types',
    type: 'General',
    value: 'Pdf, docx, pptx, xlsx, jpg, png, txt'
  },
  {
    config: 'Max Chat Topic',
    desc: 'Maksimum Jumlah Chat Topic (sidebar)',
    type: 'Feature',
    value: '50 (0 = unlimited)'
  },
  {
    config: 'Chat Topic Expired Days',
    desc: 'Batas max chat topic auto delete, dilihat dari last date chat per topic',
    type: 'Feature',
    value: '30 (days) (0 = unlimited)'
  },
  {
    config: 'Max Chat',
    desc: 'Batas max chat per topic',
    type: 'Feature',
    value: '100 (chats) (0 = unlimited)'
  }
];

export default function SettingTable() {
  return (
    <div className="mx-auto w-full rounded-lg bg-white p-6 shadow">
      <h1 className="mb-4 text-2xl font-semibold">Pengaturan Aplikasi</h1>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] table-auto border-collapse overflow-hidden rounded-lg">
          <thead>
            <tr className="bg-gradient-to-r from-purple-500 to-indigo-500 text-left text-white">
              <th className="px-4 py-3">Config</th>
              <th className="px-4 py-3">Desc</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {dummySettings.map((row, idx) => (
              <tr
                key={idx}
                className="border-b last:border-0 hover:bg-gray-100"
              >
                <td className="px-4 py-3 font-medium">{row.config}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{row.desc}</td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-1 text-xs font-semibold ${
                      row.type === 'General'
                        ? 'bg-blue-100 text-blue-600'
                        : 'bg-yellow-100 text-yellow-600'
                    }`}
                  >
                    {row.type}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm">{row.value}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      className="rounded-full bg-yellow-100 p-2 hover:bg-yellow-200"
                      onClick={() => alert(`Comming soon: ${row.config}`)}
                    >
                      <PencilIcon className="h-4 w-4 text-yellow-600" />
                    </button>
                    {/* <button className="rounded-full bg-red-100 p-2 hover:bg-red-200">
                      <TrashIcon className="h-4 w-4 text-red-600" />
                    </button> */}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
