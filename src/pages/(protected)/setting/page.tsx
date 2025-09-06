import { PencilIcon } from 'lucide-react';
import { useState, useEffect } from 'react';

type TSetting = {
  config: string;
  desc: string;
  type: 'General' | 'Feature';
  value: string;
  information?: string;
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
    value:
      'Berikan 10 ide marketing produk obat batuk OBH Combi untuk meningkatkan brand awareness; Saya karyawan baru PT.Combiphar. Jelaskan kepada saya dengan lengkap tentang peraturan perusahaan, hak, kewajiban dan benefit yang saya dapatkan sebagai karyawan.; Buatkan saya kalimat email untuk menawarkan kerjasama dengan apotek baru bernama Apotek Sehat ;Bantu saya membuat formula excel'
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
    value: '50',
    information: '(0 = unlimited)'
  },
  {
    config: 'Chat Topic Expired Days',
    desc: 'Batas max chat topic auto delete, dilihat dari last date chat per topic',
    type: 'Feature',
    value: '30',
    information: '(days) (0 = unlimited)'
  },
  {
    config: 'Max Chat',
    desc: 'Batas max chat per topic',
    type: 'Feature',
    value: '100',
    information: '(chats) (0 = unlimited)'
  }
];

export default function SettingTable() {
  const [selectedSetting, setSelectedSetting] = useState<TSetting | null>(null);
  const [modalType, setModalType] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState<string>('');

  useEffect(() => {
    const debounceTimer = setTimeout(() => {
      if (selectedSetting) {
        selectedSetting.value = inputValue;
      }
    }, 300);

    return () => clearTimeout(debounceTimer);
  }, [inputValue, selectedSetting]);

  const openPopup = (row: TSetting) => {
    setSelectedSetting(row);
    setInputValue(row.value);

    if (
      row.config === 'Chat max text' ||
      row.config === 'Max Chat Topic' ||
      row.config === 'Chat Topic Expired Days' ||
      row.config === 'Max Chat'
    ) {
      setModalType('number');
    } else if (row.config === 'Chat Greeting') {
      setModalType('text');
    } else if (row.config === 'Prompt Example') {
      setModalType('cards');
    } else if (row.config === 'Attachment') {
      setModalType('toggle');
    } else if (row.config === 'Attachment File Types') {
      setModalType('dropdown');
    }
  };

  const closePopup = () => {
    setSelectedSetting(null);
    setModalType(null);
  };

  const fileTypes = [
    { value: 'Pdf', label: 'Pdf' },
    { value: 'docx', label: 'docx' },
    { value: 'pptx', label: 'pptx' },
    { value: 'xlsx', label: 'xlsx' },
    { value: 'jpg', label: 'jpg' },
    { value: 'png', label: 'png' },
    { value: 'txt', label: 'txt' }
  ];

  return (
    <div className="mx-auto w-full rounded-lg bg-white p-6 shadow">
      <h1 className="mb-4 text-2xl font-semibold">Pengaturan Aplikasi</h1>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] table-auto border-collapse overflow-hidden rounded-lg">
          <thead>
            <tr className="bg-[#772f8e] text-left text-white">
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
                <td className="px-4 py-3 text-sm">
                  {row.value.split(';').map((item, idx) => (
                    <span key={idx}>
                      {item}
                      {idx < row.value.split(';').length - 1 && <br />}{' '}
                    </span>
                  ))}
                  {row.information && <span>{row.information}</span>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <button
                      className="rounded-full bg-yellow-100 p-2 hover:bg-yellow-200"
                      onClick={() => openPopup(row)}
                    >
                      <PencilIcon className="h-4 w-4 text-yellow-600" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {selectedSetting && modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-[400px] rounded-lg bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold">
              Edit Setting: {selectedSetting.config}
            </h2>
            {modalType === 'number' && (
              <div>
                <input
                  type="number"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="w-full rounded border p-2"
                />
              </div>
            )}
            {modalType === 'text' && (
              <div className="w-full">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  className="h-16 w-full rounded-lg border-2 border-gray-300 bg-white p-4 text-gray-700 shadow-md transition-all duration-300 ease-in-out placeholder:text-gray-400 hover:shadow-lg focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500"
                  placeholder="Enter your text here"
                  onInput={(e) => {
                    const textarea = e.target as HTMLTextAreaElement;
                    textarea.style.height = 'auto';
                    textarea.style.height = `${textarea.scrollHeight}px`;
                  }}
                  rows={3}
                />
              </div>
            )}

            {modalType === 'cards' && (
              <div>
                {inputValue.split(';').map((item, index) => (
                  <div key={index} className="mb-2">
                    <textarea
                      value={item}
                      onChange={(e) => {
                        const newValue = [...inputValue.split(';')];
                        newValue[index] = e.target.value;
                        setInputValue(newValue.join(';'));
                      }}
                      onInput={(e) => {
                        const textarea = e.target as HTMLTextAreaElement;
                        textarea.style.height = 'auto';
                        textarea.style.height = `${textarea.scrollHeight}px`;
                      }}
                      className="w-full rounded border p-2"
                      rows={3}
                    />
                  </div>
                ))}
              </div>
            )}

            {modalType === 'toggle' && (
              <div className="flex items-center space-x-4">
                <span className="text-sm">Attachment: </span>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={inputValue === 'on'}
                    onChange={() =>
                      setInputValue(inputValue === 'on' ? 'off' : 'on')
                    }
                    className="sr-only"
                  />
                  <div
                    className={`h-6 w-11 rounded-full transition-colors duration-300 ease-in-out ${
                      inputValue === 'on' ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`${
                        inputValue === 'on' ? 'translate-x-5' : 'translate-x-0'
                      } inline-block h-5 w-5 transform rounded-full bg-white shadow-md transition-transform duration-300 ease-in-out`}
                    ></div>
                  </div>
                </label>
              </div>
            )}

            {modalType === 'dropdown' && (
              <div className="w-full">
                <select
                  multiple
                  value={inputValue.split(',')}
                  onChange={(e) => {
                    const selectedOptions = Array.from(
                      e.target.selectedOptions,
                      (option) => option.value
                    );
                    setInputValue(selectedOptions.join(','));
                  }}
                  className="scrollbar-thin scrollbar-thumb-blue-500 scrollbar-track-gray-100 h-32 w-full gap-2 rounded-xl border border-gray-300 bg-white p-3 text-gray-700 transition-all duration-300 ease-in-out hover:border-blue-300 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {fileTypes.map((type, index) => (
                    <option
                      key={index}
                      value={type.value}
                      className="m-[2px] rounded-lg px-2 py-1 transition-colors duration-200 hover:bg-blue-100"
                    >
                      {type.label}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="mt-4 flex justify-end">
              <button
                onClick={closePopup}
                className="rounded-lg bg-gray-300 px-4 py-2"
              >
                Cancel
              </button>
              <button
                onClick={closePopup}
                className="ml-2 rounded-lg bg-blue-500 px-4 py-2 text-white"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
