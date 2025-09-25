import { useState } from 'react';
import { CheckIcon } from '@radix-ui/react-icons';
import { formatMarkdownToPlainText } from '@/lib/markdown';
import useCreateFeedbackChat from '../../_hook/use-mutate-response';
import { useGetDetailHistory } from '../../_hook/use-get-history-chat';

interface IconBarProps {
  text: string;
  id: string;
  chat_id: string;
  feedback: '1' | '-1' | null;
}

export const IconBar = ({ text, id, chat_id, feedback }: IconBarProps) => {
  const [isCopied, setIsCopied] = useState(false);
  const { mutate } = useCreateFeedbackChat();
  const query = useGetDetailHistory({ chat_id: chat_id || '' });

  const handleCopy = () => {
    const textToCopy = formatMarkdownToPlainText(text);
    navigator.clipboard.writeText(textToCopy).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    });
  };

  const handleFeedback = (newFeedback: '1' | '-1') => {
    mutate(
      { feedback: newFeedback, chat_id: id },
      {
        onSuccess: () => {
          query.refetch();
        }
      }
    );
  };

  return (
    <div className="flex items-center gap-2 pt-3">
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
      {(feedback === '1' || feedback === null) && (
        <div className="group relative">
          <button
            onClick={() => handleFeedback('1')}
            className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
          >
            <img src="/icons/like.png" alt="Like" className="h-4 w-4" />
          </button>
          <span className="absolute -top-7 left-1/2 -translate-x-1/2 scale-90 rounded bg-gray-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
            Suka
          </span>
        </div>
      )}
      {(feedback === '-1' || feedback === null) && (
        <div className="group relative">
          <button
            onClick={() => handleFeedback('-1')}
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
