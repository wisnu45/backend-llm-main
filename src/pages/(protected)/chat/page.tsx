import {
  ChatBubbleIcon,
  EnvelopeClosedIcon,
  MixerHorizontalIcon,
  PersonIcon,
  ReloadIcon
} from '@radix-ui/react-icons';
import { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

import useCreateChat from './_hook/use-create-chat';
import { PromptPreview, FileType } from './component/prompt-preview';
import { ModernLoadingIndicator } from './component/loading-indicator';
import InputDataWithForm from './component/InputDataWithForm';
import { TChatFormData } from './schema';
import Cookies from 'js-cookie';
import { useFetchSetting } from '../setting/_hook/use-fetch-setting';

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
  const mutation = useCreateChat();
  const queryHistorySideBar = useGetFiles();

  const query = useFetchSetting();

  const dataSetting = query?.data?.data || [];
  const dataGreating =
    dataSetting
      .find((item) => item.name === 'Chat greeting')
      ?.value.toString()
      .split('[username]') || '';
  const promptValue = dataSetting.find(
    (item) => item.name === 'Prompt example'
  )?.value;
  const promsExample =
    typeof promptValue === 'string' && promptValue.trim() !== ''
      ? JSON.parse(promptValue)
      : undefined;
  const dataProms = promsExample ? promsExample : promptSuggestions;

  const navigate = useNavigate();
  const currentPath = useLocation().pathname;

  const handleClickItem = (prompt: string) => {
    setPromptRef.current?.onSetPrompt(prompt);
  };

  useEffect(() => {
    const sessionId = Cookies.get('chat_id');
    if (sessionId) {
      navigate(`${currentPath}/${sessionId}`);
    }
  }, []);

  const handleFormSubmit = async (formData: TChatFormData) => {
    const trimmedQuestion = formData.prompt.trim();

    setPreviewPrompt(trimmedQuestion);
    setPreviewFiles(formData.attachments || []);
    setShowPreview(true);
    setLoading(true);

    try {
      mutation.mutate(
        {
          // session_id: null,
          // chat_id: null,
          question: trimmedQuestion,
          is_browse: formData.is_browse,
          is_company_policy: formData.is_company_policy,
          attachments: formData.attachments,
          with_document: formData.with_document
        },
        {
          onSuccess: (data) => {
            const chatId = data?.data?.chat_id || '';
            queryHistorySideBar.refetch();
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);
            if (chatId) {
              navigate(`${currentPath}/${chatId || ''}`);
            }
          },
          onError: (err) => {
            console.error('Chat mutation failed', err);
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);
          }
        }
      );
    } catch (error) {
      console.error('Session creation failed', error);
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
              {dataGreating[0] || 'Hi'}, {Cookies.get('name') || ''}
            </h2>
            <h3 className="text-gradient-light mb-1 text-2xl font-bold md:mb-8 md:text-3xl lg:text-4xl">
              {dataGreating[1]
                ? dataGreating[1]
                : 'Apa yang bisa Vita bantu hari ini?'}
            </h3>
            <p className="mb-4 text-gray-500 md:mb-10">
              Tuliskan pertanyaanmu atau gunakan salah satu dari contoh di bawah
              ini
            </p>

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
              <ScrollBar orientation="horizontal" className="hidden md:block" />
            </ScrollArea>

            <Button variant="ghost" className="mb-2 flex text-sm md:mb-3">
              <ReloadIcon className="mr-2" />
              Refresh prompts
            </Button>
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
        <div className="">
          <InputDataWithForm
            onSubmit={handleFormSubmit}
            isLoading={loading}
            setPrompRef={setPromptRef}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
