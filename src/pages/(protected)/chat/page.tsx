import {
  ChatBubbleIcon,
  EnvelopeClosedIcon,
  MixerHorizontalIcon,
  PersonIcon
  // ReloadIcon
} from '@radix-ui/react-icons';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

// import { Button } from '@/components/ui/button';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';

import Cookies from 'js-cookie';
import { useFetchSetting } from '../setting/_hook/use-fetch-setting';
import { useFetchSettingFeature } from '../setting/_hook/use-fetch-setting-feature';
import useCreateChat, { type NetworkAwareError } from './_hook/use-create-chat';
import InputDataWithForm from './component/InputDataWithForm';
import { ModernLoadingIndicator } from './component/loading-indicator';
import NetworkErrorCard from './component/NetworkErrorCard';
import { FileType, PromptPreview } from './component/prompt-preview';
import { TChatFormData } from './schema';

const promptSuggestions = [
  {
    icon: <PersonIcon className=" text-gray-500" />,
    text: 'Berikan 10 ide marketing produk obat batuk OBH Combi untuk meningkatkan brand awareness'
  },
  {
    icon: <EnvelopeClosedIcon className=" text-gray-500" />,
    text: 'Saya karyawan baru PT.Combiphar. Jelaskan kepada saya dengan lengkap tentang peraturan perusahaan, hak, kewajiban dan benefit yang saya dapatkan sebagai karyawan.'
  },
  {
    icon: <ChatBubbleIcon className=" text-gray-500" />,
    text: 'Buatkan saya kalimat email untuk menawarkan kerjasama dengan apotek baru bernama Apotek Sehat'
  },
  {
    icon: <MixerHorizontalIcon className=" text-gray-500" />,
    text: 'Bantu saya membuat formula excel'
  }
];

export type TSetPromptType = {
  onSetPrompt: (prompt: string) => void;
};

const ChatPage = () => {
  const setPromptRef = useRef<TSetPromptType | null>();
  const [loading, setLoading] = useState<boolean>(false);
  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [networkError, setNetworkError] = useState<boolean>(false);
  const [lastFailedRequest, setLastFailedRequest] =
    useState<TChatFormData | null>(null);
  const mutation = useCreateChat();
  const queryHistorySideBar = useGetFiles();

  const query = useFetchSetting();
  const queryFeature = useFetchSettingFeature();

  const dataSetting = query?.data?.data || [];
  const settingFeature = queryFeature?.data?.data;
  const getMenuValue = (name) =>
    settingFeature?.find((menu) => menu.name.toLocaleLowerCase() === name)
      ?.value;
  const dataGreating =
    dataSetting
      .find((item) => item.name === 'Chat greeting')
      ?.value.toString()
      .split(', [username]') || '';
  const promptValue = dataSetting.find(
    (item) => item.name === 'Prompt example'
  )?.value;
  const promsExample =
    typeof promptValue === 'string' && promptValue.trim() !== ''
      ? JSON.parse(promptValue)
      : undefined;
  const dataProms = promsExample ? promsExample : promptSuggestions;

  const maxChatTopic = Number(getMenuValue('max chat topic')) || 0;
  const currentChatCount = queryHistorySideBar.data?.data.length || 0;
  const isLimitExceeded = maxChatTopic > 0 && currentChatCount >= maxChatTopic;
  const errorConnectionMessage = String(
    getMenuValue('error connection') ||
      'Koneksi internet terputus. Coba lagi nanti'
  );

  const navigate = useNavigate();
  const currentPath = useLocation().pathname;
  const maxText = Number(getMenuValue('chat max text')) || 1000;

  const handleClickItem = (prompt: string) => {
    const limitedPrompt =
      prompt.length > maxText ? prompt.slice(0, maxText) : prompt;
    setPromptRef.current?.onSetPrompt(limitedPrompt);
  };

  const handleRetry = () => {
    if (lastFailedRequest) {
      // Pass isRetry=true to preserve network error state during retry
      handleFormSubmit(lastFailedRequest, true);
    }
  };

  useEffect(() => {
    const sessionId = Cookies.get('chat_id');
    if (sessionId) {
      navigate(`${currentPath}/${sessionId}`);
    }
  }, []);

  const handleFormSubmit = async (
    formData: TChatFormData,
    isRetry: boolean = false
  ) => {
    if (isLimitExceeded) {
      return;
    }

    const trimmedQuestion = formData.prompt.trim();

    // Only clear network error for new submissions, not retries
    if (!isRetry) {
      setNetworkError(false);
      setLastFailedRequest(null);
    }

    setPreviewPrompt(trimmedQuestion);
    setPreviewFiles(formData.with_document || []);
    setShowPreview(true);
    setLoading(true);

    try {
      mutation.mutate(
        {
          question: trimmedQuestion,
          is_browse: formData.is_browse,
          is_company: formData.is_company,
          is_general: formData.is_general,
          // attachments: formData.attachments,
          with_document: formData.with_document
        },
        {
          onSuccess: (data) => {
            const chatId = data?.data?.chat_id || '';
            queryHistorySideBar.refetch();

            // Clear all states including network error on success
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);
            setNetworkError(false);
            setLastFailedRequest(null);

            if (chatId) {
              navigate(`${currentPath}/${chatId || ''}`);
            }
          },
          onError: (err: Error) => {
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);

            // Check if this is a network error
            const networkError = err as NetworkAwareError;
            if (networkError.isNetworkError) {
              setNetworkError(true);
              setLastFailedRequest(formData);
            } else {
              // Clear network error for non-network errors
              setNetworkError(false);
              setLastFailedRequest(null);
            }
          }
        }
      );
    } catch (error) {
      setLoading(false);
      setShowPreview(false);
      setPreviewPrompt('');
      setPreviewFiles([]);
    }
  };

  return (
    <div className="flex w-full flex-1 flex-col items-center justify-center text-left">
      <div className="relative mx-auto w-full md:max-w-4xl">
        {!loading && (
          <div className="mb-4 mt-4 w-full">
            <img
              src="/icons/logo_vita.png"
              alt="Combiphar Logo"
              className="w-32"
            />
            <h2 className="text-gradient-light mb-1 text-2xl font-bold md:mb-2 md:text-3xl lg:text-4xl">
              {dataGreating[0] || 'Hi'} {` ${Cookies.get('name')}`},{' '}
              {dataGreating[1]
                ? dataGreating[1]
                : 'Apa yang bisa Vita bantu hari ini?'}
            </h2>
            <p className="mb-4 text-gray-500 md:mb-10">
              Tuliskan pertanyaanmu atau gunakan salah satu dari contoh di bawah
              ini
            </p>

            {!isLimitExceeded && (
              <>
                <ScrollArea className="mb-2 w-full md:mb-8">
                  <div className="flex w-full flex-col gap-4 py-2 md:w-max md:flex-row md:gap-4">
                    {dataProms?.map((prompt: any, index: number) => (
                      <div
                        key={index}
                        onClick={() => handleClickItem(prompt.text || prompt)}
                        className="flex min-h-20 w-full shrink-0 cursor-pointer flex-col items-start rounded-md border border-gray-200 p-2 hover:bg-gray-50 md:w-52 md:rounded-lg md:p-4"
                      >
                        <p className="flex-1 text-xs text-gray-700 md:text-sm">
                          {prompt.text || prompt}
                        </p>
                        {prompt.icon}
                      </div>
                    ))}
                  </div>
                  <ScrollBar
                    orientation="horizontal"
                    className="hidden md:block"
                  />
                </ScrollArea>
                {/* 
                <Button variant="ghost" className="mb-2 flex text-sm md:mb-3">
                  <ReloadIcon className="mr-2" />
                  Refresh prompts
                </Button> */}
              </>
            )}
          </div>
        )}
        {showPreview && (
          <div className="mb-4">
            <PromptPreview text={previewPrompt} files={previewFiles} />
          </div>
        )}
        {loading && (
          <div className="mb-4">
            <ModernLoadingIndicator />
          </div>
        )}
        {networkError && (
          <div className="mb-4">
            <NetworkErrorCard
              onRetry={handleRetry}
              message={errorConnectionMessage}
            />
          </div>
        )}
        {isLimitExceeded && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Batas Chat Tercapai
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>
                    Anda telah mencapai batas maksimum topik chat (
                    {currentChatCount}/{maxChatTopic}). Silakan hapus beberapa
                    chat yang sudah ada untuk membuat yang baru.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
        <div className="">
          <InputDataWithForm
            onSubmit={handleFormSubmit}
            isLoading={loading || isLimitExceeded}
            setPrompRef={setPromptRef}
            isHistory={false}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
