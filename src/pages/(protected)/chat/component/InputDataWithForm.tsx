import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { useMobileScroll } from '@/hooks/use-mobile-scroll';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowRightIcon, Cross2Icon } from '@radix-ui/react-icons';
import clsx from 'clsx';
import { Globe, Mic, Paperclip, Lightbulb, Building } from 'lucide-react';
import { useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { TSetPromptType } from '../page';
import { ChatFormSchema, TChatFormData } from '../schema';
import { toast } from '@/components/ui/use-toast';
import { useFetchSettingFeature } from '../../setting/_hook/use-fetch-setting-feature';
import { ChatItemData } from './types';
import { TogglePreferences } from '@/lib/local-storage';

interface InputDataWithFormProps {
  onSubmit: (data: TChatFormData) => void;
  isLoading?: boolean;
  initialPrompt?: string;
  setPrompRef?: React.MutableRefObject<TSetPromptType | null | undefined>;
  scrollContainerRef?: React.RefObject<HTMLElement>;
  isFloating?: boolean;
  isHistory?: boolean;
  lastData?: ChatItemData;
}

const InputDataWithForm = ({
  isFloating,
  onSubmit,
  isLoading = false,
  initialPrompt = '',
  setPrompRef,
  scrollContainerRef,
  isHistory = true,
  lastData
}: InputDataWithFormProps) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);
  const [popupFile, setPopupFile] = useState<File | null>(null);
  const [hasInitialized, setHasInitialized] = useState(false);
  const { shouldHideOnScroll } = useMobileScroll(50, scrollContainerRef);
  const shouldHide = shouldHideOnScroll && isFloating;

  console.log('CEK DISINI', shouldHideOnScroll);

  const queryFeature = useFetchSettingFeature();
  const settingFeature = queryFeature?.data?.data;
  const getMenuValue = (name) =>
    settingFeature?.find((menu) => menu.name === name)?.value;
  const settingAttachment = getMenuValue('Attachment');
  const maxText = getMenuValue('Max chats') || 1000;
  const fileSize = getMenuValue('Attachment file size') || 10;
  const rawFileTypes = getMenuValue('Attachment file types');
  const settingVoice = getMenuValue('Voice typing');
  const settingSearchInternet = getMenuValue('Search internet');
  const settingGeneralInsight = getMenuValue('General insight');
  const fileTypeAllow: string[] =
    typeof rawFileTypes === 'string' ? JSON.parse(rawFileTypes) : [];

  // Get smart defaults based on context
  const getSmartDefaults = () => {
    if (isHistory) {
      // For chat detail page, ALWAYS prioritize chat context (lastData)
      if (lastData) {
        return {
          is_company: lastData.is_company || false,
          is_browse: lastData.is_browse || false,
          is_general: lastData.is_general || false
        };
      }
      // Fallback if no lastData yet (loading state)
      return {
        is_company: false,
        is_browse: false,
        is_general: false
      };
    } else {
      // For new chat page, use stored user preferences
      return TogglePreferences.getWithDefaults();
    }
  };

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
      with_document: [],
      ...getSmartDefaults()
    },
    mode: 'onChange'
  });

  // Save toggle preferences only for new chat, not for chat detail
  const saveTogglePreferences = (
    newToggles?: Partial<{
      is_company: boolean;
      is_browse: boolean;
      is_general: boolean;
    }>
  ) => {
    // Only save as global preference for new chat page
    if (!isHistory) {
      const currentToggles = newToggles || {
        is_company: watch('is_company'),
        is_browse: watch('is_browse'),
        is_general: watch('is_general')
      };
      TogglePreferences.set(
        currentToggles as {
          is_company: boolean;
          is_browse: boolean;
          is_general: boolean;
        }
      );
    }
  };

  // Helper function to handle toggle changes with validation
  const handleToggleChange = (
    toggleType: 'is_company' | 'is_browse' | 'is_general',
    currentValue: boolean,
    onChange: (value: boolean) => void
  ) => {
    if (!isLoading) {
      const newValue = !currentValue;

      // If we're turning off this toggle, check if it's the only active one
      if (!newValue) {
        const activeToggles = [
          toggleType !== 'is_company' && watch('is_company'),
          toggleType !== 'is_browse' && watch('is_browse'),
          toggleType !== 'is_general' && watch('is_general')
        ].filter(Boolean);

        // If this is the last active toggle, activate company insight instead
        if (activeToggles.length === 0) {
          setValue('is_company', true);
          if (toggleType !== 'is_company') {
            onChange(newValue);
          }
          const newToggles = {
            is_company: true,
            is_browse:
              toggleType === 'is_browse' ? newValue : watch('is_browse'),
            is_general:
              toggleType === 'is_general' ? newValue : watch('is_general')
          };
          saveTogglePreferences(newToggles);
          return;
        }
      }

      // Normal toggle behavior
      onChange(newValue);
      const newToggles = {
        is_company:
          toggleType === 'is_company' ? newValue : watch('is_company'),
        is_browse: toggleType === 'is_browse' ? newValue : watch('is_browse'),
        is_general: toggleType === 'is_general' ? newValue : watch('is_general')
      };
      saveTogglePreferences(newToggles);
    }
  };

  // Reset initialization when chat changes (for proper chat switching)
  useEffect(() => {
    setHasInitialized(false);
  }, [lastData?.id]);

  useEffect(() => {
    if (lastData && isHistory && !hasInitialized) {
      // Update toggles with chat-specific context
      setValue('is_company', lastData.is_company || false);
      setValue('is_browse', lastData.is_browse || false);
      setValue('is_general', lastData.is_general || false);
      setHasInitialized(true);
    }
  }, [lastData, isHistory, hasInitialized, setValue]);

  // Toggle validation - ensure at least one toggle is always active
  const is_company_current = watch('is_company');
  const is_browse_current = watch('is_browse');
  const is_general_current = watch('is_general');

  useEffect(() => {
    // Ensure at least one toggle is always active
    if (!is_company_current && !is_browse_current && !is_general_current) {
      // Activate company insight as fallback
      setValue('is_company', true);
    }
  }, [setValue, is_company_current, is_browse_current, is_general_current]);

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

  const convertFileToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        resolve(reader.result as string);
      };
      reader.onerror = (error) => reject(error);
      reader.readAsDataURL(file);
    });
  };

  const validateFile = (file: File) => {
    const fileExtension = file.name.split('.').pop()?.toLowerCase();
    if (file.size > Number(fileSize) * 1024 * 1024) {
      toast({
        variant: 'destructive',
        title: 'Upload gagal',
        description: `File "${file.name}" terlalu besar (max ${fileSize} MB).`
      });
      return false;
    }
    if (!fileTypeAllow.includes(fileExtension || '')) {
      toast({
        variant: 'destructive',
        title: 'Upload gagal',
        description: `File "${file.name}" tidak diizinkan. Format yang diperbolehkan: ${fileTypeAllow.join(', ')}`
      });
      return false;
    }

    return true;
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const validTypeFile = droppedFiles.filter(validateFile);
      if (validTypeFile.length === 0) return;

      const validFiles = droppedFiles.filter((file) => {
        if (file.size > Number(fileSize) * 1024 * 1024) {
          toast({
            variant: 'destructive',
            title: 'Upload gagal',
            description: `File "${file.name}" terlalu besar (max 2 MB).`
          });
          return false;
        }
        return true;
      });

      if (validFiles.length === 0) {
        return;
      }
      const currentAttachments = watchedAttachments || [];
      setValue('attachments', [...currentAttachments, ...droppedFiles]);
      Promise.all(droppedFiles.map((file) => convertFileToBase64(file)))
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      const newFiles = Array.from(selectedFiles);
      const currentAttachments = watchedAttachments || [];

      const validFiles = newFiles.filter(validateFile);
      if (validFiles.length === 0) return;

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

  // Helper function to generate descriptive names for clipboard images
  const generateClipboardFileName = (file: File, index: number = 0): string => {
    const timestamp = new Date().toISOString().slice(0, 10);
    const extension = file.type.split('/')[1] || 'png';

    if (file.name === 'image.png' || file.name === 'image') {
      return `Pasted Image ${index + 1} (${timestamp}).${extension}`;
    }

    return file.name;
  };

  // Handle paste events for file upload
  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const files: File[] = [];

    // Process clipboard items
    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      // Handle files
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          // Generate descriptive name for clipboard images
          const renamedFile = new File(
            [file],
            generateClipboardFileName(file, files.length),
            { type: file.type }
          );
          files.push(renamedFile);
        }
      }
    }

    // If files were found, process them
    if (files.length > 0) {
      e.preventDefault(); // Prevent default paste behavior

      // Validate files
      const validFiles = files.filter(validateFile);
      if (validFiles.length === 0) return;

      // Show loading toast
      toast({
        title: 'Uploading files...',
        description: `Processing ${validFiles.length} file(s) from clipboard`
      });

      try {
        const currentAttachments = watchedAttachments || [];
        setValue('attachments', [...currentAttachments, ...validFiles]);

        const base64Files = await Promise.all(
          validFiles.map((file) => convertFileToBase64(file))
        );

        setValue('with_document', [
          ...(watch('with_document') || []),
          ...base64Files
        ]);

        // Success toast
        toast({
          title: 'Files uploaded successfully',
          description: `${validFiles.length} file(s) added from clipboard`
        });
      } catch (error) {
        console.error('Error processing pasted files:', error);
        toast({
          variant: 'destructive',
          title: 'Upload failed',
          description: 'Failed to process files from clipboard'
        });
      }
    }
  };

  const onFormSubmit = (data: TChatFormData) => {
    // Capture current state immediately before any operations
    const currentToggles = {
      is_company: data.is_company,
      is_browse: data.is_browse,
      is_general: data.is_general
    };

    // Only save as global preference for new chat, not for chat detail
    if (!isHistory) {
      TogglePreferences.set(currentToggles);
    }

    onSubmit(data);

    // Reset with the captured state (not from localStorage to avoid race condition)
    reset({
      prompt: '',
      attachments: [],
      with_document: [],
      ...currentToggles
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

  // useEffect(() => {
  //   const cookieValue = Cookies.get('search_internet') === 'true';
  //   const is_company_policy = Cookies.get('is_company') === 'true';
  //   setValue('is_browse', cookieValue);
  //   setValue('is_company', is_company_policy);
  // }, []);

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
                  maxLength={maxText ? Number(maxText) : 1000}
                  onKeyDown={handleKeyDown}
                  onPaste={handlePaste}
                  disabled={isLoading}
                />
              </div>
            )}
          />

          <div className="mt-4 flex flex-col items-start justify-between text-sm text-gray-800 sm:flex-row sm:items-center">
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:gap-2">
              {settingAttachment && (
                <>
                  <label
                    htmlFor="file-upload"
                    className={`flex cursor-pointer items-center gap-1 rounded-xl bg-gradient-to-r px-4 py-2 shadow-md transition duration-300 ${
                      !settingAttachment
                        ? 'cursor-not-allowed opacity-50 shadow-none'
                        : 'hover:text-purple-600 hover:shadow-lg'
                    }`}
                  >
                    <Paperclip size={18} />
                  </label>

                  <input
                    id="file-upload"
                    type="file"
                    multiple
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={isLoading || !settingAttachment}
                  />
                </>
              )}
              <Controller
                name="is_company"
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
                            handleToggleChange('is_company', value, onChange);
                          }}
                        >
                          <div
                            className={`flex items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 ${
                              value
                                ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                : 'shadow-lg'
                            }`}
                          >
                            <Building className="h-5 w-5" />
                            <span className="text-sm font-medium md:inline">
                              Company Insights
                            </span>
                          </div>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent className="hidden sm:block">
                        Search Company Insights
                      </TooltipContent>
                    </Tooltip>
                  );
                }}
              />
              {settingGeneralInsight && (
                <Controller
                  name="is_general"
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
                              handleToggleChange('is_general', value, onChange);
                            }}
                          >
                            <div
                              className={`flex items-center gap-2 rounded-xl px-4 py-2 shadow-md transition-all duration-300 ${
                                value
                                  ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                  : 'shadow-lg'
                              }`}
                            >
                              <Lightbulb className="h-5 w-5" />
                              <span className="text-sm font-medium md:inline">
                                General Insights
                              </span>
                            </div>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent className="hidden sm:block">
                          Search General Insights
                        </TooltipContent>
                      </Tooltip>
                    );
                  }}
                />
              )}
              {settingSearchInternet && (
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
                              handleToggleChange('is_browse', value, onChange);
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
              )}
            </div>
            <div className="mt-3 flex w-full flex-col items-center gap-3 sm:mt-0 sm:w-auto sm:flex-row">
              {settingVoice && (
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
              )}
              <div className="mt-3 flex w-full items-center justify-end gap-2 sm:mt-0 sm:w-auto sm:justify-end">
                <span className="text-sm text-gray-900">
                  {watchedPrompt?.length || 0}/{maxText || 1000}
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
