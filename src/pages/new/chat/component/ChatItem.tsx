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

const MarkdownRenderer = ({ content }: { content: string }) => (
  <ReactMarkdown
    remarkPlugins={[remarkGfm]}
    components={{
      h1: (props) => <h1 className="my-4 text-3xl font-bold" {...props} />,
      h2: (props) => <h2 className="my-3 text-2xl font-semibold" {...props} />,
      h3: (props) => <h3 className="my-2 text-xl font-semibold" {...props} />,
      h4: (props) => <h4 className="my-1.5 text-lg font-medium" {...props} />,
      h5: (props) => <h5 className="my-1 text-base font-medium" {...props} />,
      h6: (props) => <h6 className="my-1 text-sm font-medium" {...props} />,
      p: (props) => (
        <p className="my-2 leading-relaxed text-gray-800" {...props} />
      ),
      strong: (props) => <strong className="font-semibold" {...props} />,
      em: (props) => <em className="italic text-gray-700" {...props} />,
      del: (props) => <del className="text-red-500 line-through" {...props} />,
      a: (props) => (
        <a
          className="text-blue-500 underline"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        />
      ),
      img: (props) => <img className="my-2 max-w-full rounded-md" {...props} />,
      blockquote: (props) => (
        <blockquote
          className="my-3 border-l-4 border-blue-400 pl-4 italic text-gray-600"
          {...props}
        />
      ),
      ul: (props) => (
        <ul className="ml-4 list-inside list-disc space-y-1" {...props} />
      ),
      ol: (props) => (
        <ol className="ml-4 list-inside list-decimal space-y-1" {...props} />
      ),
      li: (props) => (
        <li
          className="text-gray-800"
          style={{ display: 'list-item' }}
          {...props}
        />
      ),
      hr: () => <hr className="my-4 border-t border-gray-300" />,
      code: (props) => {
        const { children, ...rest } = props as any;
        return (
          <code
            className="rounded bg-gray-200 px-1 py-0.5 text-sm text-black"
            {...rest}
          >
            {children}
          </code>
        );
      },
      table: (props) => (
        <table className="my-4 w-full table-auto border-collapse" {...props} />
      ),
      thead: (props) => <thead className="bg-gray-200 text-left" {...props} />,
      tbody: (props) => <tbody {...props} />,
      tr: (props) => <tr className="border-b border-gray-300" {...props} />,
      th: (props) => (
        <th className="border border-gray-300 p-2 font-semibold" {...props} />
      ),
      td: (props) => <td className="border border-gray-300 p-2" {...props} />
    }}
  >
    {content}
  </ReactMarkdown>
);

export const ChatItem = ({ data }) => {
  const [isCopied, setIsCopied] = useState(false);
  const answer = (data.answer ?? '')
    .replace(/\n\s+\n/g, '\n\n')
    .replace(/\n{2,}/g, '\n');
  return (
    <div className="mb-10 space-y-4 ">
      <div className="flex justify-end">
        <div className="rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {data.question}
        </div>
      </div>
      <div className="col-auto flex flex-col items-start space-y-3 overflow-hidden">
        <div>
          <MarkdownRenderer content={answer} />
        </div>
        {data?.file_links?.length && data?.file_links?.length > 0 ? (
          <div className="w-full">
            <hr className="mb-2 w-full border-t-4 border-[#C4C4C480]" />
            <div className="font-bold">Referensi Sumber:</div>
            <div className="flex flex-col">
              {data?.file_links?.map((item: Item, index: number) => {
                const download_url: string = item.download_url;
                return (
                  <div
                    key={item.filename}
                    className="inline-block max-w-full  break-words "
                  >
                    <div
                      className="w-max cursor-pointer rounded-md px-2 py-1 text-blue-400 hover:underline"
                      onClick={() => {
                        window.open(download_url, '_blank');
                      }}
                    >
                      {index + 1}. {item?.filename}
                    </div>
                  </div>
                );
              })}
            </div>
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
