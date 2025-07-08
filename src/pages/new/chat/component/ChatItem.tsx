import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckIcon } from '@radix-ui/react-icons';

interface Item {
  content: string;
  metadata: {
    page: number;
    source: string;
  };
}

export const ChatItem = ({
  question,
  answer,
  sourceDocuments
}: {
  question: string;
  answer: string;
  sourceDocuments: string;
}) => {
  const sourceDocumen: Item[] = sourceDocuments
    ? JSON.parse(sourceDocuments)
    : [];
  const [isCopied, setIsCopied] = useState(false);

  return (
    <div className="mb-10 space-y-4">
      <div className="flex justify-end">
        <div className="rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {question}
        </div>
      </div>
      <div className="col-auto flex flex-col items-start space-y-3">
        <div>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm max-w-full space-y-4 break-words text-justify"
          >
            {answer}
          </ReactMarkdown>
          {/* <Markdown >{answer}</Markdown> */}
        </div>
        {sourceDocumen.length ? (
          <div className=" w-full">
            <hr className="mb-2 w-full border-t-4 border-[#C4C4C480]" />
            <div className="font-bold">Referensi Sumber:</div>
            {sourceDocumen?.map((item: Item, index: number) => (
              <div key={item.metadata.source} className="text-blue-400">
                {index + 1}. {item.metadata.source}
              </div>
            ))}
          </div>
        ) : (
          <IconBar
            setIsCopied={setIsCopied}
            isCopied={isCopied}
            text={answer}
          />
        )}
      </div>
    </div>
  );
};

const IconBar = ({ setIsCopied, isCopied, text }) => {
  const handleCopy = () => {
    const textToCopy = text;
    navigator.clipboard.writeText(textToCopy).then(() => {
      setIsCopied(true);
      setTimeout(() => {
        setIsCopied(false);
      }, 2000);
    });
  };
  return (
    <div className="flex space-x-4 p-4">
      <div className="group relative">
        <button
          onClick={handleCopy}
          className="text-gray-600 hover:text-gray-800 focus:outline-none"
        >
          {isCopied ? (
            <CheckIcon className="h-6 w-6 text-green-500" />
          ) : (
            <img src="/icons/copy.png" alt="Copy" />
          )}
        </button>
        <span className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform rounded-md bg-black p-1 text-xs text-white group-hover:block">
          Salin
        </span>
      </div>
      <div className="group relative">
        <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
          <img src="/icons/people.png" alt="People" />
        </button>
        <span className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform rounded-md bg-black p-1 text-xs text-white group-hover:block">
          Respon Bagus
        </span>
      </div>
      <div className="group relative">
        <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
          <img src="/icons/like.png" alt="Like" />
        </button>
        <span className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform rounded-md bg-black p-1 text-xs text-white group-hover:block">
          Like
        </span>
      </div>
      <div className="group relative">
        <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
          <img src="/icons/dislike.png" alt="Dislike" />
        </button>
        <span className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform rounded-md bg-black p-1 text-xs text-white group-hover:block">
          Dislike
        </span>
      </div>
      <div className="group relative">
        <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
          <img src="/icons/ungah.png" alt="Ungah" />
        </button>
        <span className="absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 transform rounded-md bg-black p-1 text-xs text-white group-hover:block">
          Unggah
        </span>
      </div>
    </div>
  );
};
