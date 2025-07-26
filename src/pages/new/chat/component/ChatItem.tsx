import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckIcon } from '@radix-ui/react-icons';
import useCreateFeedbackChat from '../_hook/use-mutate-response';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';

interface Item {
  content: string;
  filename: string;
  download_url: string;
}

// const TypingEffect = ({
//   text,
//   typingSpeed = 10
// }: {
//   text: string;
//   typingSpeed?: number;
// }) => {
//   const [displayedText, setDisplayedText] = useState<string>('');

//   useEffect(() => {
//     let index = 0;

//     const intervalId = setInterval(() => {
//       setDisplayedText((prevText) => prevText + text.charAt(index));
//       index++;

//       if (index >= text.length) {
//         clearInterval(intervalId);
//       }
//     }, typingSpeed);

//     return () => clearInterval(intervalId);
//   }, [text, typingSpeed]);

// return (
//   <ReactMarkdown
//     remarkPlugins={[remarkGfm]}
//     className="prose prose-sm max-w-full space-y-4 break-words text-justify"
//   >
//     {displayedText}
//   </ReactMarkdown>
// );

// console.log('displayedText', displayedText);
// return (
//   <ReactMarkdown
//     remarkPlugins={[remarkGfm]}
//     className="prose prose-sm max-w-full space-y-4 break-words text-justify"
//   >
//     {displayedText}
//   </ReactMarkdown>
// );
// };

export const ChatItem = ({ data }) => {
  // console.log('data ITem', data);
  const [isCopied, setIsCopied] = useState(false);

  // const isLast = (createdAt) => {
  //   const dataDate = new Date(createdAt);
  //   const now = new Date();

  //   return (
  //     dataDate.getFullYear() === now.getFullYear() &&
  //     dataDate.getMonth() === now.getMonth() &&
  //     dataDate.getDate() === now.getDate() &&
  //     dataDate.getHours() === now.getHours() &&
  //     dataDate.getMinutes() === now.getMinutes()
  //   );
  // };

  return (
    <div className="mb-10 space-y-4 ">
      <div className="flex justify-end">
        <div className="rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {data.question}
        </div>
      </div>
      <div className="col-auto flex flex-col items-start space-y-3 overflow-hidden">
        <div>
          {/* <TypingEffect text={data.answer} typingSpeed={10} /> */}
          {/* {isLast(data.created_at) ? (
            <TypingEffect text={data.answer} typingSpeed={10} />
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm max-w-full space-y-4 break-words text-justify"
            >
              {data.answer}
            </ReactMarkdown>
          )} */}
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm max-w-full space-y-4 break-words text-justify"
          >
            {data.answer}
          </ReactMarkdown>
        </div>
        {data?.file_links?.length && data?.file_links?.length > 0 ? (
          <div className="w-full">
            <hr className="mb-2 w-full border-t-4 border-[#C4C4C480]" />
            <div className="font-bold">Referensi Sumber:</div>
            {data?.file_links?.map((item: Item, index: number) => {
              const download_url: string = item.download_url;
              return (
                <div
                  key={item.filename}
                  className="cursor-pointer text-blue-400"
                  onClick={() => {
                    window.open(download_url, '_blank');
                  }}
                >
                  {index + 1}. {item?.filename}
                </div>
              );
            })}
          </div>
        ) : null}
        <IconBar
          setIsCopied={setIsCopied}
          isCopied={isCopied}
          text={data.answer}
          id={data.id}
          session_id={data.session_id}
          feedback={data.feedback}
        />
      </div>
    </div>
  );
};

const IconBar = ({ setIsCopied, isCopied, text, id, session_id, feedback }) => {
  const { mutate } = useCreateFeedbackChat();
  const query = useGetDetailHistory({ session_id: session_id || '' });

  const handleCopy = () => {
    const textToCopy = text;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setIsCopied(true);
      setTimeout(() => {
        setIsCopied(false);
      }, 2000);
    });
  };

  const handleLike = () => {
    mutate(
      { feedback: '1', chat_id: id },
      {
        onSuccess: () => {
          query.refetch();
        }
      }
    );
  };
  const handledisLike = () => {
    mutate(
      { feedback: '-1', chat_id: id },
      {
        onSuccess: () => {
          query.refetch();
        }
      }
    );
  };

  return (
    <div className="flex items-center gap-2 pt-3">
      {/* Copy Button */}
      <div className="group relative">
        <button
          onClick={handleCopy}
          className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        >
          {isCopied ? (
            <CheckIcon className="h-4 w-4 text-green-500" />
          ) : (
            <img src="/icons/copy.png" alt="Copy" className="h-4 w-4" />
          )}
        </button>
        <span className="absolute -top-7 left-1/2 -translate-x-1/2 scale-90 rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
          Salin
        </span>
      </div>
      {(feedback == 1 || feedback === null) && (
        <div className="group relative">
          <button
            onClick={handleLike}
            className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <img src="/icons/like.png" alt="Like" className="h-4 w-4" />
          </button>
          <span className="absolute -top-7 left-1/2 -translate-x-1/2 scale-90 rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
            Suka
          </span>
        </div>
      )}
      {(feedback == -1 || feedback === null) && (
        <div className="group relative">
          <button
            onClick={handledisLike}
            className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <img src="/icons/dislike.png" alt="Dislike" className="h-4 w-4" />
          </button>
          <span className="absolute -top-7 left-1/2 -translate-x-1/2 scale-90 rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
            Tidak Suka
          </span>
        </div>
      )}
    </div>
  );
};
