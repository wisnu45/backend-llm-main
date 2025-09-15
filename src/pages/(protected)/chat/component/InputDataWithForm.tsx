import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { useMobileScroll } from '@/hooks/use-mobile-scroll';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowRightIcon, Cross2Icon } from '@radix-ui/react-icons';
import clsx from 'clsx';
import Cookies from 'js-cookie';
import { Globe, Mic, Paperclip, Columns4Icon } from 'lucide-react';
import { useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { TSetPromptType } from '../page';
import { ChatFormSchema, TChatFormData } from '../schema';

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
  const defaultIsCompanyPolicy = Cookies.get('is_company_policy') === 'true';

  // Combined mobile detection and scroll state
  const { shouldHideOnScroll } = useMobileScroll(50, scrollContainerRef);

  // Determine if form should be hidden
  const shouldHide = shouldHideOnScroll && isFloating;

  const {
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { isValid, errors },
    reset,
    trigger
  } = useForm<TChatFormData>({
    resolver: zodResolver(ChatFormSchema),

    defaultValues: {
      prompt: initialPrompt,
      attachments: [],
      with_document: [],
      is_browse: defaultIsBrowse,
      is_company_policy: defaultIsCompanyPolicy
    },
    mode: 'onChange'
  });

  const watchedAttachments = watch('attachments');
  const watch_with_document = watch('with_document');
  const watchedPrompt = watch('prompt');

  const openPopup = (file: File) => {
    setPopupFile(file);
    setIsPopupOpen(true);
  };

  const closePopup = () => {
    setIsPopupOpen(false);
    setPopupFile(null);
  };

  const convertFileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        resolve(reader.result as string); // Return Base64 string
      };
      reader.onerror = (error) => reject(error);
      reader.readAsDataURL(file); // Convert file to Base64
    });
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const currentAttachments = watchedAttachments || [];
      setValue('attachments', [...currentAttachments, ...droppedFiles]);
      Promise.all(droppedFiles.map((file) => convertFileToBase64(file)))
        .then((base64Files) => {
          // Mengupdate nilai 'with_document' setelah konversi selesai
          setValue('with_document', [
            ...(watch('with_document') || []),
            ...base64Files
          ]);
        })
        .catch((error) => {
          console.error('Error converting files to Base64:', error);
        });
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      const newFiles = Array.from(selectedFiles);
      const currentAttachments = watchedAttachments || [];
      setValue('attachments', [...currentAttachments, ...newFiles]);
      Promise.all(newFiles.map((file) => convertFileToBase64(file)))
        .then((base64Files) => {
          setValue('with_document', [
            ...(watch('with_document') || []),
            ...base64Files
          ]);
        })
        .catch((error) => {
          console.error('Error converting files to Base64:', error);
        });
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    const currentAttachments = watchedAttachments || [];
    const updatedAttachments = currentAttachments.filter((_, i) => i !== index);
    setValue('attachments', updatedAttachments);
    const currentDocuments = watch('with_document') || [];
    const updatedDocuments = currentDocuments.filter((_, i) => i !== index);
    setValue('with_document', updatedDocuments);
  };

  const onFormSubmit = (data: TChatFormData) => {
    console.log('testing', data);
    onSubmit(data);
    reset({
      prompt: '',
      attachments: [],
      with_document: [],
      is_browse: Cookies.get('search_internet') === 'true',
      is_company_policy: Cookies.get('is_company_policy') === 'true'
    });
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

  const [isRecording, setIsRecording] = useState(false);
  const recognitionRef = useRef<any>(null);
  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      const SpeechRecognition =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.lang = 'id-ID';
      recognitionRef.current.interimResults = true;

      recognitionRef.current.onresult = (event: any) => {
        const transcript = Array.from(event.results)
          .map((result: any) => result[0].transcript)
          .join('');

        setValue('prompt', transcript);
        trigger('prompt');
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  }, [setValue, trigger]);

  useEffect(() => {
    const cookieValue = Cookies.get('search_internet') === 'true';
    setValue('is_browse', cookieValue); // update nilai form
  }, []);

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert('Browser tidak mendukung Speech Recognition');
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

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

          <div className="mt-4 flex flex-col items-start justify-between text-sm text-gray-800 sm:flex-row sm:items-center">
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:gap-2">
              <button
                type="button"
                className="flex cursor-pointer items-center gap-1 rounded-xl bg-gradient-to-r px-4 py-2 shadow-md transition duration-300 hover:text-purple-600 hover:shadow-lg"
              >
                <Paperclip size={18} />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer md:inline"
                >
                  Add photos & files
                </label>
                <input
                  id="file-upload"
                  type="file"
                  multiple
                  className="hidden"
                  onChange={handleFileChange}
                  disabled={isLoading}
                />
              </button>
              <Controller
                name="is_company_policy"
                control={control}
                render={({ field }) => {
                  const { value, onChange } = field;
                  return (
                    <Tooltip>
                      <TooltipTrigger>
                        <div
                          className="group relative w-max cursor-pointer"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            if (!isLoading) {
                              const newValue = !value;
                              onChange(newValue);
                              Cookies.set(
                                'is_company_policy',
                                newValue ? 'true' : 'false'
                              );
                            }
                          }}
                        >
                          <div
                            className={`flex items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 ${
                              value
                                ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                : 'shadow-lg'
                            }`}
                          >
                            <Columns4Icon className="h-5 w-5" />
                            <span className="text-sm font-medium md:inline">
                              Combiphar & Kebijakan Perusahaan
                            </span>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="hidden sm:block">
                        Search Combiphar & Kebijakan Perusahaan
                      </TooltipContent>
                    </Tooltip>
                  );
                }}
              />
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
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            if (!isLoading) {
                              const newValue = !value;
                              onChange(newValue);
                              Cookies.set(
                                'search_internet',
                                newValue ? 'true' : 'false'
                              );
                            }
                          }}
                        >
                          <div
                            className={`flex items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 ${
                              value
                                ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                : 'shadow-lg'
                            }`}
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
            <div className="mt-3 flex w-full flex-col items-center gap-3 sm:mt-0 sm:w-auto sm:flex-row">
              <Tooltip>
                <TooltipTrigger>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      toggleRecording();
                    }}
                    disabled={isLoading}
                    className={`hidden items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 md:flex ${
                      isRecording
                        ? 'animate-pulse bg-red-500 text-white'
                        : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                    }`}
                  >
                    <Mic className="h-5 w-5" />
                    {isRecording && <span>{'Merekam...'}</span>}
                  </button>
                </TooltipTrigger>
                <TooltipContent className="hidden sm:block">
                  Ucapkan pertanyaanmu
                </TooltipContent>
              </Tooltip>
              <div className="mt-3 flex w-full items-center justify-end gap-2 sm:mt-0 sm:w-auto sm:justify-end">
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
