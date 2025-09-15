import { PencilIcon } from 'lucide-react';
import { useState } from 'react';
import { useFetchSetting } from './_hook/use-fetch-setting';
import { TSettingDocument } from '@/api/settings/type';
import useEditSetting from './_hook/use-mutate-edit-setting';

export default function SettingTable() {
  const [selectedSetting, setSelectedSetting] =
    useState<TSettingDocument | null>(null);
  const [modalType, setModalType] = useState<string | null>(null);
  const [inputValue, setInputValue] = useState<string>('');

  const query = useFetchSetting();
  const mutate = useEditSetting(selectedSetting?.id || '');

  const dataSetting = query?.data?.data || [];

  const isLoading = query.isLoading || query.isFetching;

  const openPopup = (row: TSettingDocument) => {
    setSelectedSetting(row);
    setInputValue(row.value);

    if (
      row.name === 'chat_max_text' ||
      row.name === 'max_chat_topic' ||
      row.name === 'chat_topic_expired_days' ||
      row.name === 'max_chats'
    ) {
      setModalType('number');
    } else if (row.name === 'chat_greeting') {
      setModalType('text');
    } else if (
      row.name === 'prompt_example' ||
      row.name === 'attachment_file_types'
    ) {
      setModalType('text');
    } else if (row.name === 'attachment') {
      setModalType('toggle');
    }
  };

  const submit = () => {
    if (selectedSetting) {
      let data = inputValue;
      if (selectedSetting.data_type === 'array') {
        data = JSON.parse(inputValue);
      }
      const updatedSetting = {
        ...selectedSetting,
        value: data
      };
      const formData = new FormData();
      Object.entries(updatedSetting).forEach(([key, value]) => {
        if (Array.isArray(value)) {
          value.forEach((item) => {
            formData.append(`${key}[]`, item);
          });
        } else {
          formData.append(key, value);
        }
      });
      mutate.mutate(formData, {
        onSuccess: () => {
          setSelectedSetting(null);
          setModalType(null);
          console.log('Mutation successful!');
        },
        onError: (error) => {
          console.error('Mutation failed:', error);
        }
      });
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
            {!isLoading &&
              dataSetting?.map((row) => (
                <tr
                  key={row.id}
                  className="border-b last:border-0 hover:bg-gray-100"
                >
                  <td className="px-4 py-3 font-medium">{row.name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {row.description}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-semibold ${
                        row.type === 'general'
                          ? 'bg-blue-100 text-blue-600'
                          : 'bg-yellow-100 text-yellow-600'
                      }`}
                    >
                      {row.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm">
                    {row.data_type === 'array' ? (
                      <>
                        {JSON.parse(row.value).map(
                          (item: string, index: number) => (
                            <div key={index}>
                              {item},
                              <br key={index} />
                            </div>
                          )
                        )}
                      </>
                    ) : (
                      <span>{row.value}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        className="rounded-full bg-yellow-100 p-2 hover:bg-yellow-200"
                        onClick={() => {
                          openPopup(row);
                        }}
                      >
                        <PencilIcon className="h-4 w-4 text-yellow-600" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
        {isLoading && (
          <div className="flex items-center justify-center py-4">
            <span>Loading...</span> {/* You can use a spinner here */}
          </div>
        )}
      </div>
      {selectedSetting && modalType && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
          <div className="w-[400px] rounded-lg bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold">
              Edit Setting: {selectedSetting.name}
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
                  className="h-60 w-full rounded-lg border-2 border-gray-300 bg-white p-4 text-gray-700 shadow-md transition-all duration-300 ease-in-out placeholder:text-gray-400 hover:shadow-lg focus:border-blue-500 focus:outline-none focus:ring-4 focus:ring-blue-500"
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

            {modalType === 'toggle' && (
              <div className="flex items-center space-x-4">
                <span className="text-sm">Attachment: </span>
                <label className="relative inline-flex cursor-pointer items-center">
                  <input
                    type="checkbox"
                    checked={inputValue === 'true'}
                    onChange={() =>
                      setInputValue(inputValue === 'true' ? 'false' : 'true')
                    }
                    className="sr-only"
                  />
                  <div
                    className={`h-6 w-11 rounded-full transition-colors duration-300 ease-in-out ${
                      inputValue === 'true' ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`${
                        inputValue === 'true'
                          ? 'translate-x-5'
                          : 'translate-x-0'
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
                  {fileTypes?.map((type, index) => (
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
                onClick={submit}
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
