import * as z from 'zod';
import {
  ArrowRightIcon,
  ChatBubbleIcon,
  EnvelopeClosedIcon,
  MixerHorizontalIcon,
  PersonIcon,
  ReloadIcon
} from '@radix-ui/react-icons';
import { useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { zodResolver } from '@hookform/resolvers/zod';
import { Controller, useForm } from 'react-hook-form';

import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';

import useCreateChat from './_hook/use-create-chat';
import useCreateNewChat from './_hook/use-create-new-chat';
import { PromptPreview, FileType } from './component/prompt-preview';
import { ModernLoadingIndicator } from './component/loading-indicator';

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

const schema = z.object({
  chat: z.string().min(1)
});

type ChatData = z.infer<typeof schema>;

const ChatPage = () => {
  const refButton = useRef<HTMLButtonElement | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [files, setFiles] = useState<FileType[]>([]);
  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);

  const mutation = useCreateChat();
  const createNewChat = useCreateNewChat();
  const queryHistorySideBar = useGetFiles();

  const navigate = useNavigate();
  const currentPath = useLocation().pathname;

  const form = useForm<ChatData>({
    mode: 'onChange',
    resolver: zodResolver(schema)
  });

  const chatLength = form.watch('chat')?.length || 0;

  const handleClickItem = (item: string) => {
    form.setValue('chat', item);
    form.trigger();
  };

  const handleSend = async (data: ChatData) => {
    const trimmedQuestion = data.chat.trim();

    // Show preview before sending
    setPreviewPrompt(trimmedQuestion);
    setPreviewFiles([...files]);
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
            form.reset();
            setLoading(false);
            setShowPreview(false);
            setPreviewPrompt('');
            setPreviewFiles([]);
            setFiles([]);
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
      <form
        className="mx-auto w-full md:max-w-4xl"
        onSubmit={form.handleSubmit(handleSend)}
      >
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

        <Controller
          control={form.control}
          name="chat"
          render={({ field }) => (
            <div className="mt-2 w-full rounded-xl border border-gray-300 bg-white p-3 md:mt-4 md:p-4">
              <textarea
                className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
                rows={3}
                placeholder="Ask CombipharGPT whatever you want....."
                maxLength={1000}
                value={field.value}
                onChange={(e) => field.onChange(e.target.value.trimStart())}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    refButton.current?.click();
                  }
                }}
              />

              <div className="mt-4 flex items-center justify-between text-sm text-gray-800">
                <div className="flex items-center gap-6">
                  <button className="flex items-center gap-1 transition hover:text-purple-600">
                    {/* <PlusCircledIcon /> Add attachment */}
                  </button>
                  <button className="flex items-center gap-1 transition hover:text-purple-600">
                    {/* <ImageIcon /> Use image */}
                  </button>
                </div>

                <div className="flex items-center gap-3">
                  <span className="text-sm text-gray-900">
                    {chatLength}/1000
                  </span>
                  <Button
                    ref={refButton}
                    size="icon"
                    type="submit"
                    disabled={!form.formState.isValid || loading}
                    className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4]"
                  >
                    <ArrowRightIcon />
                  </Button>
                </div>
              </div>
            </div>
          )}
        />
      </form>
    </div>
  );
};

export default ChatPage;
