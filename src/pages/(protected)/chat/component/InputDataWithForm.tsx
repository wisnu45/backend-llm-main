import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '@/components/ui/tooltip';
import { useMobileScroll } from '@/hooks/use-mobile-scroll';
import { zodResolver } from '@hookform/resolvers/zod';
import { ArrowRightIcon, Cross2Icon } from '@radix-ui/react-icons';
import clsx from 'clsx';
import {
  Globe,
  Mic,
  Paperclip,
  Lightbulb,
  Building,
  SlidersHorizontal
} from 'lucide-react';
import {
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  useMemo
} from 'react';
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
  // isPopupOpen: boolean;
  setIsPopupOpen: (isOpen: boolean) => void;
  setPopupFile: (popupFile: File | null) => void;
}

const InputDataWithForm = ({
  isFloating,
  onSubmit,
  isLoading = false,
  initialPrompt = '',
  setPrompRef,
  scrollContainerRef,
  isHistory = true,
  lastData,
  // isPopupOpen,
  setIsPopupOpen,
  setPopupFile
}: InputDataWithFormProps) => {
  // const [isPopupOpen, setIsPopupOpen] = useState(false);
  // const [popupFile, setPopupFile] = useState<File | null>(null);
  const [hasInitialized, setHasInitialized] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const { shouldHideOnScroll } = useMobileScroll(50, scrollContainerRef);
  const shouldHide = shouldHideOnScroll && isFloating;

  const queryFeature = useFetchSettingFeature();
  const settingFeature = queryFeature?.data?.data;
  const getMenuValue = (name) =>
    settingFeature?.find(
      (menu) => menu.name.toLowerCase() === name.toLowerCase()
    )?.value;
  const settingAttachment = getMenuValue('Attachment');
  const maxText = getMenuValue('chat max text') || 1000;
  const fileSize = getMenuValue('Attachment file size') || 10;
  const rawFileTypes = getMenuValue('Attachment file types');
  const settingVoice = getMenuValue('Voice typing');
  const settingSearchInternet = getMenuValue('Search internet');
  const settingGeneralInsight = getMenuValue('General insight');
  const settingCompanyInsight = getMenuValue('Company insight');

  const fileTypeAllow: string[] =
    typeof rawFileTypes === 'string' ? JSON.parse(rawFileTypes) : [];

  const getSmartDefaults = () => {
    if (isHistory) {
      if (lastData) {
        return {
          is_company: lastData.is_company || false,
          is_browse: lastData.is_browse || false,
          is_general: lastData.is_general || false
        };
      }
      return {
        is_company: false,
        is_browse: false,
        is_general: false
      };
    } else {
      return {
        is_company: true,
        is_browse: false,
        is_general: false
      };
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
      // attachments: [],
      with_document: [],
      ...getSmartDefaults()
    },
    mode: 'onChange'
  });

  const saveTogglePreferences = (
    newToggles?: Partial<{
      is_company: boolean;
      is_browse: boolean;
      is_general: boolean;
    }>
  ) => {
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

  const handleToggleChange = (
    toggleType: 'is_company' | 'is_browse' | 'is_general',
    currentValue: boolean,
    onChange: (value: boolean) => void
  ) => {
    if (!isLoading) {
      const newValue = !currentValue;
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

  useEffect(() => {
    setHasInitialized(false);
  }, [lastData?.id]);

  useEffect(() => {
    if (lastData && isHistory && !hasInitialized) {
      setValue('is_company', lastData.is_company || false);
      setValue('is_browse', lastData.is_browse || false);
      setValue('is_general', lastData.is_general || false);
      setHasInitialized(true);
    }
  }, [lastData, isHistory, hasInitialized, setValue]);

  const is_company_current = watch('is_company');
  const is_browse_current = watch('is_browse');
  const is_general_current = watch('is_general');

  useEffect(() => {
    if (!is_company_current && !is_browse_current && !is_general_current) {
      // Activate company insight as fallback
      setValue('is_company', true);
    }
  }, [setValue, is_company_current, is_browse_current, is_general_current]);

  const watchedAttachments = watch('with_document');
  const watchedPrompt = watch('prompt');

  // Memoize blob URLs to prevent re-creating them on every render
  const filePreviewUrls = useMemo(() => {
    if (!watchedAttachments || watchedAttachments.length === 0) return [];

    return watchedAttachments.map((file) => ({
      file,
      url: URL.createObjectURL(file)
    }));
  }, [watchedAttachments]);

  // Cleanup blob URLs when component unmounts or files change
  useEffect(() => {
    return () => {
      filePreviewUrls.forEach(({ url }) => {
        URL.revokeObjectURL(url);
      });
    };
  }, [filePreviewUrls]);

  useEffect(() => {
    if (maxText === watchedPrompt?.length) {
      toast({
        variant: 'destructive',
        title: 'Maksimum karakter tercapai',
        description: `Anda telah mencapai batas maksimum karakter untuk pesan ini sebanyak ${maxText} karakter.`
      });
    }
  }, [watchedPrompt?.length]);

  const openPopup = (file: File) => {
    setPopupFile(file);
    setIsPopupOpen(true);
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
            description: `File "${file.name}" terlalu besar (max ${fileSize} MB).`
          });
          return false;
        }
        return true;
      });

      if (validFiles.length === 0) {
        return;
      }
      const currentAttachments = watchedAttachments || [];
      setValue('with_document', [...currentAttachments, ...droppedFiles]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      const newFiles = Array.from(selectedFiles);
      const currentAttachments = watchedAttachments || [];

      const validFiles = newFiles.filter(validateFile);
      if (validFiles.length === 0) return;

      setValue('with_document', [...currentAttachments, ...newFiles]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    const currentAttachments = watchedAttachments || [];
    const updatedAttachments = currentAttachments.filter((_, i) => i !== index);
    setValue('with_document', updatedAttachments);
  };

  const generateClipboardFileName = (file: File, index: number = 0): string => {
    const timestamp = new Date().toISOString().slice(0, 10);
    const extension = file.type.split('/')[1] || 'png';

    if (file.name === 'image.png' || file.name === 'image') {
      return `Pasted Image ${index + 1} (${timestamp}).${extension}`;
    }

    return file.name;
  };

  const handlePaste = async (e: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    const files: File[] = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.kind === 'file') {
        const file = item.getAsFile();
        if (file) {
          const renamedFile = new File(
            [file],
            generateClipboardFileName(file, files.length),
            { type: file.type }
          );
          files.push(renamedFile);
        }
      }
    }

    if (files.length > 0) {
      e.preventDefault();
      const validFiles = files.filter(validateFile);
      if (validFiles.length === 0) return;
      toast({
        title: 'Uploading files...',
        description: `Processing ${validFiles.length} file(s) from clipboard`
      });

      try {
        const currentAttachments = watchedAttachments || [];
        setValue('with_document', [...currentAttachments, ...validFiles]);
        toast({
          title: 'Files uploaded successfully',
          description: `${validFiles.length} file(s) added from clipboard`
        });
      } catch (error) {
        toast({
          variant: 'destructive',
          title: 'Upload failed',
          description: 'Failed to process files from clipboard'
        });
      }
    }
  };

  const onFormSubmit = (data: TChatFormData) => {
    const currentToggles = {
      is_company: data.is_company,
      is_browse: data.is_browse,
      is_general: data.is_general
    };
    if (!isHistory) {
      TogglePreferences.set(currentToggles);
    }
    onSubmit({
      ...data,
      prompt: data.prompt.trim(),
      with_document: data.with_document
    });

    reset({
      prompt: '',
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
          {filePreviewUrls.length > 0 && (
            <>
              <h4 className="text-sm text-gray-400">Files:</h4>
              <div className="mb-4 overflow-x-auto hide-scrollbar">
                <div className="mt-2 flex gap-4">
                  {filePreviewUrls.map(({ file, url }, index) => (
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
                            src={url}
                            alt={file?.name}
                            className="h-24 w-24 rounded-lg object-cover"
                            onClick={() => openPopup(file)}
                          />
                        ) : file?.type === 'application/pdf' ? (
                          <iframe
                            src={url}
                            title={file?.name}
                            className="h-24 w-24 rounded-lg object-cover"
                            onClick={() => openPopup(file)}
                          />
                        ) : file?.type ===
                            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                          file?.type === 'application/vnd.ms-excel' ? (
                          <div
                            className="flex h-24 w-24 cursor-pointer flex-col items-center justify-center rounded-lg bg-gray-100 p-2 text-center text-xs"
                            onClick={() => openPopup(file)}
                          >
                            <span className="text-xl">📊</span>
                            <p className="w-full truncate">{file?.name}</p>
                          </div>
                        ) : (
                          <div
                            className="flex h-24 w-24 cursor-pointer flex-col items-center justify-center rounded-lg bg-gray-100 p-2 text-center text-xs"
                            onClick={() => openPopup(file)}
                          >
                            <span className="text-xl">📄</span>
                            <p className="w-full truncate">{file?.name}</p>
                          </div>
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

          <div className="mt-4 flex flex-col items-start justify-between gap-3 text-sm text-gray-800 sm:flex-row sm:items-center">
            <div className="order-2 flex w-full flex-wrap items-center gap-2.5 sm:order-1 sm:w-auto sm:flex-row sm:gap-2">
              <div className="hidden flex-wrap items-center gap-2 sm:flex">
                {settingAttachment && (
                  <>
                    <label
                      htmlFor="file-upload"
                      className={`flex min-h-[44px] cursor-pointer items-center justify-center gap-1 rounded-xl bg-gradient-to-r px-3 py-2 shadow-md transition duration-300 sm:px-4 sm:py-2.5 ${
                        !settingAttachment
                          ? 'cursor-not-allowed opacity-50 shadow-none'
                          : 'hover:text-purple-600 hover:shadow-lg active:scale-95'
                      }`}
                    >
                      <Paperclip className="h-4 w-4 sm:h-5 sm:w-5" />
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
              </div>

              {/* ✅ DESKTOP MENU (original buttons) */}
              <div className="hidden flex-wrap items-center gap-2 sm:flex">
                {settingCompanyInsight && (
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
                                handleToggleChange(
                                  'is_company',
                                  value,
                                  onChange
                                );
                              }}
                            >
                              <div
                                className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                  value
                                    ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                    : 'bg-white shadow-lg hover:shadow-xl'
                                }`}
                              >
                                <Building className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                <span
                                  className={`text-sm font-medium sm:inline ${
                                    value ? '' : 'hidden'
                                  }`}
                                >
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
                )}
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
                                handleToggleChange(
                                  'is_general',
                                  value,
                                  onChange
                                );
                              }}
                            >
                              <div
                                className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                  value
                                    ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                    : 'bg-white shadow-lg hover:shadow-xl'
                                }`}
                              >
                                <Lightbulb className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                <span
                                  className={`text-sm font-medium sm:inline ${
                                    value ? '' : 'hidden'
                                  }`}
                                >
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
                                handleToggleChange(
                                  'is_browse',
                                  value,
                                  onChange
                                );
                              }}
                            >
                              <div
                                className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                  value
                                    ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                    : 'bg-white shadow-lg hover:shadow-xl'
                                }`}
                              >
                                <Globe className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                <span
                                  className={`text-sm font-medium sm:inline ${
                                    value ? '' : 'hidden'
                                  }`}
                                >
                                  Search
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
            </div>
            <div className="order-1 flex w-full items-center justify-between gap-3 sm:order-2 sm:mt-0 sm:w-auto sm:justify-end">
              {/* ✅ MOBILE MENU (collapsed) */}
              <div className="flex sm:hidden">
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="flex min-h-[50px] items-center justify-center rounded-xl bg-white p-2 shadow-lg"
                >
                  <SlidersHorizontal className="h-5 w-5" />
                </button>

                {mobileMenuOpen && (
                  <div className="absolute bottom-[80px] left-2 z-[100] flex flex-col gap-2 rounded-xl border bg-white p-3 shadow-2xl">
                    {settingCompanyInsight && (
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
                                    handleToggleChange(
                                      'is_company',
                                      value,
                                      onChange
                                    );
                                  }}
                                >
                                  <div
                                    className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                      value
                                        ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                        : 'bg-white shadow-lg hover:shadow-xl'
                                    }`}
                                  >
                                    <Building className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                    <span
                                      className={`text-sm font-medium sm:inline`}
                                    >
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
                    )}

                    {/* General */}
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
                                    handleToggleChange(
                                      'is_general',
                                      value,
                                      onChange
                                    );
                                  }}
                                >
                                  <div
                                    className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                      value
                                        ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                        : 'bg-white shadow-lg hover:shadow-xl'
                                    }`}
                                  >
                                    <Lightbulb className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                    <span
                                      className={`text-sm font-medium sm:inline`}
                                    >
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

                    {/* Browse */}
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
                                    handleToggleChange(
                                      'is_browse',
                                      value,
                                      onChange
                                    );
                                  }}
                                >
                                  <div
                                    className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                                      value
                                        ? 'bg-[#772f8e] text-white hover:text-purple-200 hover:shadow-lg'
                                        : 'bg-white shadow-lg hover:shadow-xl'
                                    }`}
                                  >
                                    <Globe className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                                    <span
                                      className={`text-sm font-medium sm:inline`}
                                    >
                                      Search
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
                )}
              </div>
              <div className="flex gap-2">
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
                        className={`flex min-h-[44px] items-center gap-2 rounded-xl px-3 py-2 shadow-md transition-all duration-300 active:scale-95 sm:px-4 sm:py-2.5 ${
                          isRecording
                            ? 'animate-pulse bg-red-500 text-white'
                            : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
                        }`}
                      >
                        <Mic className="h-4 w-4 flex-shrink-0 sm:h-5 sm:w-5" />
                        {isRecording && (
                          <span className="text-sm">{'Merekam...'}</span>
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent className="hidden sm:block">
                      Ucapkan pertanyaanmu
                    </TooltipContent>
                  </Tooltip>
                )}
                <div className="flex items-center gap-2.5">
                  <span className="text-sm font-medium text-gray-900">
                    {watchedPrompt?.length || 0}/{maxText || 1000}
                  </span>
                  <button
                    type="submit"
                    disabled={!isValid || isLoading}
                    className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#7051f8] text-white shadow-md transition-all hover:bg-[#5b3de4] hover:shadow-lg active:scale-95 disabled:cursor-not-allowed disabled:bg-gray-400 sm:h-11 sm:w-11"
                  >
                    <ArrowRightIcon className="h-4 w-4 sm:h-5 sm:w-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="flex justify-center bg-[#EEEEEE] pt-2 text-[10px] font-bold sm:text-sm">
          Vita can make mistakes, so double-check it
        </div>
      </form>
    </div>
  );
};

export default InputDataWithForm;
