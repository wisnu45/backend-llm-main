import { ArrowRightIcon, Cross2Icon } from '@radix-ui/react-icons';

import { Globe } from 'lucide-react';

import { useState, useImperativeHandle, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { ChatFormSchema, TChatFormData } from '../schema';
import { TSetPromptType } from '../page';
import Cookies from 'js-cookie';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { useMobileScroll } from '@/hooks/use-mobile-scroll';
import clsx from 'clsx';

interface InputDataWithFormProps {
  onSubmit: (data: TChatFormData) => void;
  isLoading?: boolean;
  initialPrompt?: string;
  setPrompRef?: React.MutableRefObject<TSetPromptType | null | undefined>;
  scrollContainerRef?: React.RefObject<HTMLElement>;
  isFloating?: boolean;
}

const InputDataWithForm = ({
  isFloating,
  onSubmit,
  isLoading = false,
  initialPrompt = '',
  setPrompRef,
  scrollContainerRef
}: InputDataWithFormProps) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [popupFile, setPopupFile] = useState<File | null>(null);
  const defaultIsBrowse = Cookies.get('search_internet') === 'true';

  // Combined mobile detection and scroll state
  const { shouldHideOnScroll } = useMobileScroll(50, scrollContainerRef);

  // Determine if form should be hidden
  const shouldHide = shouldHideOnScroll && isFloating;

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { isValid },
    reset,
    trigger
  } = useForm<TChatFormData>({
    resolver: zodResolver(ChatFormSchema),

    defaultValues: {
      prompt: initialPrompt,
      attachments: [],
      is_browse: defaultIsBrowse
    },
    mode: 'onChange'
  });

  const watchedAttachments = watch('attachments');
  const watchedPrompt = watch('prompt');

  const openPopup = (file: File) => {
    setPopupFile(file);
    setIsPopupOpen(true);
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setPopupFile(null);
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const currentAttachments = watchedAttachments || [];
      setValue('attachments', [...currentAttachments, ...droppedFiles]);
    }
  };

  // const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  //   const selectedFiles = e.target.files;
  //   if (selectedFiles) {
  //     const newFiles = Array.from(selectedFiles);
  //     const currentAttachments = watchedAttachments || [];
  //     setValue('attachments', [...currentAttachments, ...newFiles]);
  //   }
  // };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    const currentAttachments = watchedAttachments || [];
    const updatedAttachments = currentAttachments.filter((_, i) => i !== index);
    setValue('attachments', updatedAttachments);
  };

  const onFormSubmit = (data: TChatFormData) => {
    onSubmit(data);
    reset();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(onFormSubmit)();
    }
  };

  useImperativeHandle(
    setPrompRef,
    () => ({
      onSetPrompt: (prompt: string) => {
        setValue('prompt', prompt);
        trigger('prompt');
      }
    }),
    [setValue, trigger]
  );
  const watchedSearch = watch('is_browse');

  useEffect(() => {
    setValue('is_browse', watchedSearch === true);
    Cookies.set('search_internet', watchedSearch === true ? 'true' : 'false');
  }, [watchedSearch, setValue]);

  return (
    <div
      className={clsx(' bottom-0 left-0 right-0', isFloating ? 'absolute' : '')}
    >
      <form
        onSubmit={handleSubmit(onFormSubmit)}
        className={`relative transition-transform duration-300 ease-in-out ${
          shouldHide
            ? 'translate-y-full transform opacity-0'
            : 'translate-y-0 transform opacity-100'
        }`}
        style={{
          transform: shouldHide ? 'translateY(100%)' : 'translateY(0)',
          opacity: shouldHide ? 0 : 1,
          visibility: shouldHide ? 'hidden' : 'visible'
        }}
      >
        <div
          className="mx-auto w-full rounded-xl border border-gray-300 bg-white p-4 shadow-lg"
          onDrop={handleFileDrop}
          onDragOver={handleDragOver}
        >
          {watchedAttachments && watchedAttachments.length > 0 && (
            <>
              <h4 className="text-sm text-gray-400">Files:</h4>
              <div className="mb-4 overflow-x-auto hide-scrollbar">
                <div className="mt-2 flex gap-4">
                  {watchedAttachments.map((file, index) => (
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
                        type="button"
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

          <Controller
            name="prompt"
            control={control}
            render={({ field }) => (
              <div>
                <textarea
                  {...field}
                  className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
                  rows={4}
                  placeholder="Ask Vita"
                  maxLength={1000}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                />
              </div>
            )}
          />

          <div className="mt-4 flex items-center justify-between text-sm text-gray-800">
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:gap-2">
              {/* <button
              type="button"
              className="flex cursor-pointer items-center gap-1 rounded-xl bg-gradient-to-r px-4 py-2 shadow-md transition duration-300 hover:text-purple-600 hover:shadow-lg"
            >
              <Paperclip size={18} />
              <label htmlFor="file-upload" className="cursor-pointer">
                Attach Document
              </label>
              <input
                id="file-upload"
                type="file"
                multiple
                className="hidden"
                onChange={handleFileChange}
                disabled={isLoading}
              />
            </button> */}
              {/* <button
              type="button"
              className="flex items-center gap-1 transition hover:text-purple-600"
            >
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
                onChange={handleFileChange}
                disabled={isLoading}
              />
            </button> */}
              {/* <Controller
                name="is_browse"
                control={control}
                render={({ field }) => (
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={field.value}
                    onChange={field.onChange}
                    disabled={isLoading}
                  />
                )}
              /> */}
              <Controller
                name="is_browse"
                control={control}
                render={({ field }) => {
                  const { value, onChange } = field;

                  return (
                    <Tooltip>
                      <TooltipTrigger>
                        <div
                          className="group relative w-max cursor-pointer"
                          onClick={() => !isLoading && onChange(!value)} // toggle state
                        >
                          <div
                            className={`flex items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 ${
                              value
                                ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white hover:text-purple-200 hover:shadow-lg'
                                : ' shadow-lg'
                            } ${isLoading ? 'cursor-not-allowed opacity-50' : ''}`}
                          >
                            <Globe className="h-5 w-5" />
                            <span className="text-sm font-medium">
                              Cari di internet
                            </span>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="hidden sm:block">
                        Search the web when necessary
                      </TooltipContent>
                    </Tooltip>
                  );
                }}
              />
            </div>

            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-900">
                {watchedPrompt?.length || 0}/1000
              </span>
              <button
                type="submit"
                disabled={!isValid || isLoading}
                className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4] disabled:cursor-not-allowed disabled:bg-gray-400"
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
                  type="button"
                  onClick={closePopup}
                  className="absolute right-4 top-4 rounded-full bg-red-600 p-2 text-white"
                >
                  <Cross2Icon className="h-6 w-6" />
                </button>
              </div>
            </div>
          )}
        </div>
        <div className="flex justify-center bg-[#EEEEEE] pt-2 text-[10px] font-bold sm:text-sm">
          Vita can make mistakes, so double-check it
        </div>
      </form>
    </div>
  );
};

export default InputDataWithForm;
