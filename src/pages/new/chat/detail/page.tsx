import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowRightIcon } from '@radix-ui/react-icons';
import { useEffect, useRef, useState } from 'react';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';
import { useParams } from 'react-router-dom';
import { ChatItem } from '../component/ChatItem';
import useCreateChat from '../_hook/use-create-chat';
import { Loader } from '../component/Loader';

const DetailPage = () => {
  const { chatId } = useParams();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [text, setText] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
  };

  const query = useGetDetailHistory({ session_id: chatId || '' });
  const mutation = useCreateChat();

  const payload = {
    question: text,
    session_id: chatId || ''
  };

  useEffect(() => {
    query.refetch();
  }, [chatId]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollIntoView({
        behavior: 'smooth'
      });
    }
  }, [query.data?.data.length, loading]);

  const handleClick = () => {
    if (!text.trim()) return;
    setLoading(true);

    mutation.mutate(payload, {
      onSuccess: () => {
        setLoading(false);
        setText('');
        query.refetch();
      },
      onError: () => {
        setLoading(false);
      }
    });
  };

  return (
    <>
      <ScrollArea className="flex-1">
        <div className="mx-auto min-h-full w-[80%]">
          {/* {chat.messages.map((message) => (
            <div
              className={`flex w-full p-4 ${message.isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-4`}>
                {!message.isUser ? (
                  <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white">
                    <img src="/icons/logo-short.png" />
                  </div>
                ) : null}
                <div
                  className={`rounded-2xl ${
                    message.isUser && 'rounded-br-md bg-[#D9D9D9] px-4 py-3'
                  }`}
                >
                  <p className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.text}
                  </p>
                </div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex w-full justify-start p-4">
              <div className="flex max-w-[70%] gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white">
                  <img src="/icons/logo-short.png" />
                </div>
                <div className="rounded-2xl rounded-bl-md  px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.1s' }}
                    ></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.2s' }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          )}
           */}
          {query.isLoading && <Loader />}

          {query?.data?.data?.map((message, index) => {
            const isLast = index === (query?.data?.data?.length ?? 0) - 1;
            return (
              <div ref={isLast && !loading ? scrollAreaRef : null} key={index}>
                <ChatItem
                  key={index}
                  question={message.question}
                  answer={message.answer}
                  sourceDocuments={message.source_documents}
                />
              </div>
            );
          })}
          {loading && (
            <div className="flex w-full justify-start p-4" ref={scrollAreaRef}>
              <div className="flex max-w-[70%] gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white">
                  <img src="/icons/logo-short.png" />
                </div>
                <div className="rounded-2xl rounded-bl-md  px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.1s' }}
                    ></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.2s' }}
                    ></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>
      <div className="mx-auto w-[80%] rounded-xl border border-gray-300 bg-white p-4">
        <textarea
          className="w-full resize-none border-none text-sm outline-none placeholder:text-gray-400"
          rows={4}
          placeholder="Ask CombipharGPT whatever you want....."
          maxLength={1000}
          value={text}
          onChange={handleChange}
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
              onClick={handleClick}
              className="flex h-8 w-8 items-center justify-center rounded-md bg-[#7051f8] text-white transition hover:bg-[#5b3de4]"
            >
              <ArrowRightIcon />
            </button>
          </div>
        </div>
      </div>
    </>
  );
};

export default DetailPage;
