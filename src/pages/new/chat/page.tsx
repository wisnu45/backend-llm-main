import {
  ChatBubbleIcon,
  EnvelopeClosedIcon,
  MixerHorizontalIcon,
  PersonIcon,
  ReloadIcon
} from '@radix-ui/react-icons';
import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

import useCreateChat from './_hook/use-create-chat';
import useCreateNewChat from './_hook/use-create-new-chat';
import { PromptPreview, FileType } from './component/prompt-preview';
import { ModernLoadingIndicator } from './component/loading-indicator';
import InputDataWithForm from './component/InputDataWithForm';
import { TChatFormData } from './detail/schema';

const promptSuggestions = [
  {
    icon: <PersonIcon className=" text-gray-500" />,
    text: 'Write a to-do list for a personal project or task'
  },
  {
    icon: <EnvelopeClosedIcon className=" text-gray-500" />,
    text: 'Generate an email or reply to a job offer'
  },
  {
    icon: <ChatBubbleIcon className=" text-gray-500" />,
    text: 'Summarise this article or text for me in one paragraph'
  },
  {
    icon: <MixerHorizontalIcon className=" text-gray-500" />,
    text: 'How does AI work in a technical capacity.'
  }
];

const ChatPage = () => {
  const [loading, setLoading] = useState<boolean>(false);
  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [setPrompt, setSetPrompt] = useState<((prompt: string) => void) | null>(
    null
  );

  const mutation = useCreateChat();
  const createNewChat = useCreateNewChat();
  const queryHistorySideBar = useGetFiles();

  const navigate = useNavigate();
  const currentPath = useLocation().pathname;

  const handleSetPrompt = (setter: (prompt: string) => void) => {
    setSetPrompt(() => setter);
  };

  const handleClickItem = (item: string) => {
    if (setPrompt) {
      setPrompt(item);
    }
  };

  const handleFormSubmit = async (formData: TChatFormData) => {
    const trimmedQuestion = formData.prompt.trim();

    // Show preview before sending
    setPreviewPrompt(trimmedQuestion);
    setPreviewFiles(formData.attachments || []);
    setShowPreview(true);
    setLoading(true);

    try {
      const sessionResponse = await createNewChat.mutateAsync();

      const sessionId = sessionResponse?.data?.session_id;
      if (!sessionId) {
        setLoading(false);
        setShowPreview(false);
        setPreviewPrompt('');
        setPreviewFiles([]);
        return;
      }

      mutation.mutate(
        {
          session_id: sessionId,
          question: trimmedQuestion
        },
        {
          onSuccess: () => {
            queryHistorySideBar.refetch();
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);
            navigate(`${currentPath}/${sessionId}`);
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
      <div className="mx-auto w-full md:max-w-4xl">
        {!loading && (
          <div className="w-full">
            <h2 className="text-gradient-light text-2xl font-bold md:text-3xl lg:text-4xl">
              Hi there, Marvin
            </h2>
            <h3 className="text-gradient-light mt-1 text-2xl font-bold md:mt-2 md:text-3xl lg:text-4xl">
              What would you like to know?
            </h3>
            <p className="mt-2 text-gray-500 md:mt-6">
              Use one of the most common prompts below or use your own to begin
            </p>

            <ScrollArea className="mt-2 w-full overflow-x-auto md:mt-8">
              <div className="flex w-max gap-4 py-2">
                {promptSuggestions.map((prompt, index) => (
                  <div
                    key={index}
                    onClick={() => handleClickItem(prompt.text)}
                    className="flex min-h-20 w-52 shrink-0 cursor-pointer flex-col items-start rounded-md border border-gray-200 p-2 hover:bg-gray-50 md:rounded-lg md:p-4"
                  >
                    <p className="flex-1 text-xs text-gray-700 md:text-sm">
                      {prompt.text}
                    </p>
                    {prompt.icon}
                  </div>
                ))}
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>

            <Button variant="ghost" className="mt-2 flex text-sm md:mt-3">
              <ReloadIcon className="mr-2" />
              Refresh prompts
            </Button>
          </div>
        )}

        {/* Prompt Preview */}
        {showPreview && (
          <div className="mt-4">
            <PromptPreview text={previewPrompt} files={previewFiles} />
          </div>
        )}

        {/* Loading Indicator */}
        {loading && (
          <div className="mt-4">
            <ModernLoadingIndicator />
          </div>
        )}

        {/* Input Form */}
        <div className="mt-4">
          <InputDataWithForm
            onSubmit={handleFormSubmit}
            isLoading={loading}
            onSetPrompt={handleSetPrompt}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
