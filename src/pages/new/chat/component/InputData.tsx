import { ArrowRightIcon, Cross2Icon } from '@radix-ui/react-icons';
import { Paperclip } from 'lucide-react';
import { useState } from 'react';

const InputData = ({
  handleFileDrop,
  handleDragOver,
  files,
  removeFile,
  text,
  handleChange,
  handleFileChange,
  isChecked,
  setText,
  handleCheckboxChange,
  handleClick
}) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [popupFile, setPopupFile] = useState<File | null>(null);

  const openPopup = (file: File) => {
    setPopupFile(file);
    setIsPopupOpen(true);
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setPopupFile(null);
  };
  return (
    <div
      className="mx-auto w-full rounded-xl border border-gray-300 bg-white p-4 "
      onDrop={handleFileDrop}
      onDragOver={handleDragOver}
    >
      {files?.length > 0 && (
        <>
          <h4 className="text-sm text-gray-400">Files:</h4>
          <div className="mb-4 overflow-x-auto hide-scrollbar">
            <div className="mt-2 flex gap-4">
              {files?.map((file, index) => (
                <div
                  key={index}
                  className="relative flex items-center justify-center rounded-lg bg-gray-700 p-2"
                >
                  <div
                    className="flex flex-col items-center hover:cursor-pointer"
                    onClick={() => openPopup(file)}
                  >
                    {file?.type?.startsWith('image') ? (
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file?.name}
                        className="h-24 w-24 rounded-lg object-cover"
                        onClick={() => openPopup(file)}
                      />
                    ) : (
                      <iframe
                        src={file ? URL.createObjectURL(file) : ''}
                        title={file?.name}
                        className="h-24 w-24 rounded-lg object-cover"
                        onClick={() => openPopup(file)}
                      />
                    )}
                    <span className="w-16 truncate text-center text-xs text-white">
                      {file?.name}
                    </span>
                  </div>
                  <button
                    className="absolute right-0 top-0 z-50 rounded-full bg-red-600 p-1 text-white"
                    onClick={() => removeFile(index)}
                  >
                    <Cross2Icon className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
      <textarea
        className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
        rows={4}
        placeholder="Ask Vita"
        maxLength={1000}
        value={text}
        onChange={handleChange}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            setText('');
            handleClick();
          }
        }}
      />

      <div className="mt-4 flex items-center justify-between text-sm text-gray-800">
        <div className="flex flex-col items-start gap-2 sm:flex-row sm:gap-2">
          <button className="flex items-center gap-1 transition hover:text-purple-600">
            <Paperclip size={18} />
            <label htmlFor="file-upload" className="cursor-pointer">
              Add attachment
            </label>
            <input
              id="file-upload"
              type="file"
              multiple
              className="hidden"
              onChange={(e) => handleFileChange(e)}
            />
          </button>
          {/* <button className="flex items-center gap-1 transition hover:text-purple-600">
            <ImageIcon />
            <label htmlFor="image-upload" className="cursor-pointer">
              Use image
            </label>
            <input
              id="image-upload"
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => handleFileChange(e)}
            />
          </button> */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              className="h-4 w-4"
              checked={isChecked}
              onChange={handleCheckboxChange}
            />
            <span className="text-sm">Cari di internet</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-900">{text.length}/1000</span>
          <button
            onClick={() => handleClick()}
            className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4]"
          >
            <ArrowRightIcon />
          </button>
        </div>
      </div>
      {isPopupOpen && popupFile && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50"
          onClick={closePopup}
        >
          <div
            className="relative h-full max-h-[90%] w-full max-w-4xl overflow-hidden rounded-lg bg-white p-4"
            onClick={(e) => e.stopPropagation()}
          >
            {popupFile?.type?.startsWith('image') ? (
              <img
                src={URL.createObjectURL(popupFile)}
                alt={popupFile?.name}
                className="h-full w-full rounded-lg object-contain"
              />
            ) : (
              <iframe
                src={URL.createObjectURL(popupFile) || ''}
                title={popupFile?.name}
                className="h-full w-full rounded-lg"
              />
            )}
            <button
              onClick={closePopup}
              className="absolute right-4 top-4 rounded-full bg-red-600 p-2 text-white"
            >
              <Cross2Icon className="h-6 w-6" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default InputData;
