import {
  ArrowRightIcon,
  ChatBubbleIcon,
  EnvelopeClosedIcon,
  MixerHorizontalIcon,
  PersonIcon,
  ReloadIcon
} from '@radix-ui/react-icons';
import { SetStateAction, useEffect, useRef, useState } from 'react';
import useCreateChat from './_hook/use-create-chat';
import useCreateNewChat from './_hook/use-create-new-chat';
import { useGetDetailHistory } from './_hook/use-get-history-chat';
import { ScrollArea } from '@radix-ui/react-scroll-area';
import { ChatItem } from './component/ChatItem';
import { Loader } from './component/Loader';
import { useNavigate } from 'react-router-dom';
import { useGetFiles } from '@/components/ui/sidebar/_hook/use-get-history-chat';

type ChatResult = {
  data?: {
    answer?: string;
    source_documents?: string[];
  };
};

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
  const [text, setText] = useState('');
  const [chat, setChat] = useState<ChatResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [sessionId, setSessionId] = useState<string>();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const mutation = useCreateChat();
  const createNewChat = useCreateNewChat();
  const navigate = useNavigate();
  const currentPath = window.location.pathname;

  const payload = {
    question: text,
    session_id: sessionId || ''
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
  };
  const query = useGetDetailHistory({ session_id: sessionId || '' });
  const queryHistorySideBar = useGetFiles();
  const handleClickItem = (item: SetStateAction<string>) => {
    setText(item);
  };
  const handleClick = () => {
    if (!text.trim()) return;
    setChat({});
    setLoading(true);
    mutation.mutate(payload, {
      onSuccess: (data) => {
        setLoading(false);
        setChat({
          data: data?.data ?? undefined
        });
        setText('');
        query.refetch();
        queryHistorySideBar.refetch();
        navigate(`${currentPath}/${sessionId}`);
      },
      onError: () => {
        setLoading(false);
      }
    });
  };
  useEffect(() => {
    if (!sessionId) {
      createNewChat.mutate(undefined, {
        onSuccess: (data) => {
          setSessionId(data.data.session_id);
        },
        onError: (error) => {
          console.error('error', error);
        }
      });
    }
  }, []);

  return (
    <div className="mx-auto flex w-full  flex-1 flex-col items-center justify-center text-left">
      {loading ? (
        <Loader />
      ) : chat && !loading ? (
        <ScrollArea className="scrollbar-hide flex-1" ref={scrollAreaRef}>
          <div className="min-h-full">
            {query?.data?.data?.map((message, index) => (
              <ChatItem
                key={index}
                question={message.question}
                answer={message.answer}
                sourceDocuments={message.source_documents}
              />
            ))}
          </div>
        </ScrollArea>
      ) : (
        <div className="mx-auto w-full md:max-w-4xl">
          <h2 className="text-gradient-light text-4xl font-bold">
            Hi there, Marvin
          </h2>
          <h3 className="text-gradient-light mt-2 text-4xl font-bold">
            What would you like to know?
          </h3>
          <p className="mt-6 text-gray-500">
            Use one of the most common prompts below or use your own to begin
          </p>

          {/* Mobile: horizontal scroll, Desktop: grid */}
          <div className="mt-8 block md:hidden">
            <ScrollArea className="w-full max-w-full overflow-x-auto">
              <div className="flex min-w-max gap-4">
                {promptSuggestions.map((prompt, index) => (
                  <div
                    key={index}
                    onClick={() => handleClickItem(prompt.text)}
                    className="flex min-h-20 w-40 cursor-pointer flex-col items-start rounded-md border border-gray-200 p-2 hover:bg-gray-50 md:rounded-lg md:p-4"
                  >
                    <p className="flex-1 text-xs text-gray-700 md:text-sm">
                      {prompt.text}
                    </p>
                    {prompt.icon}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
          {/* Desktop: grid layout */}
          <div className="mt-8 hidden grid-cols-1 gap-4 text-left md:grid md:grid-cols-4">
            {promptSuggestions.map((prompt, index) => (
              <div
                key={index}
                onClick={() => handleClickItem(prompt.text)}
                className="flex min-h-20 min-w-[90px] cursor-pointer flex-col items-start rounded-md border border-gray-200 p-2 hover:bg-gray-50 md:min-h-32 md:min-w-[120px] md:rounded-lg md:p-4"
              >
                <p className="flex-1 text-xs text-gray-700 md:text-sm">
                  {prompt.text}
                </p>
                {prompt.icon}
              </div>
            ))}
          </div>

          <button className="mt-6 flex text-sm text-gray-600 hover:text-gray-900">
            <ReloadIcon className="mr-2" />
            Refresh prompts
          </button>
        </div>
      )}

      <div className="mt-16 w-full rounded-xl border border-gray-300 bg-white p-4">
        <textarea
          className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
          rows={4}
          placeholder="Ask CombipharGPT whatever you want....."
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
          <div className="flex items-center gap-6">
            <button className="flex items-center gap-1 transition hover:text-purple-600">
              {/* <PlusCircledIcon /> Add attachment */}
            </button>
            <button className="flex items-center gap-1 transition hover:text-purple-600">
              {/* <ImageIcon /> Use image */}
            </button>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-900">{text.length}/1000</span>
            <button
              className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4]"
              onClick={handleClick}
            >
              <ArrowRightIcon />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatPage;
