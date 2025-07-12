import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckIcon } from '@radix-ui/react-icons';
interface Item {
  content: string;
  filename: string;
  download_url: string;
}

export const ChatItem = ({ data }) => {
  const [isCopied, setIsCopied] = useState(false);

  return (
    <div className="mb-10 space-y-4 ">
      <div className="flex justify-end">
        <div className="rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {data.question}
        </div>
      </div>
      <div className="col-auto flex flex-col items-start space-y-3 overflow-hidden">
        <div>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            className="prose prose-sm max-w-full space-y-4 break-words text-justify"
          >
            {data.answer}
          </ReactMarkdown>
          {/* <Markdown >{answer}</Markdown> */}
        </div>
        {data?.file_links.length ? (
          <div className=" w-full">
            <hr className="mb-2 w-full border-t-4 border-[#C4C4C480]" />
            <div className="font-bold">Referensi Sumber:</div>
            {data?.file_links?.map((item: Item, index: number) => {
              const download_url: string = item.download_url;
              return (
                <div
                  key={item.filename}
                  className="cursor-pointer text-blue-400"
                  onClick={() => {
                    window.location.href = download_url;
                    window.open(download_url, '_blank');
                  }}
                >
                  {index + 1}. {item?.filename}
                </div>
              );
            })}
          </div>
        ) : (
          <IconBar
            setIsCopied={setIsCopied}
            isCopied={isCopied}
            text={data.answer}
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
    <div className="flex items-center gap-2 pt-3">
      <button
        onClick={handleCopy}
        className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        title="Salin"
      >
        {isCopied ? (
          <CheckIcon className="h-4 w-4 text-green-500" />
        ) : (
          <img src="/icons/copy.png" alt="Copy" className="h-4 w-4" />
        )}
      </button>

      <button
        className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        title="Respon Bagus"
      >
        <img src="/icons/people.png" alt="People" className="h-4 w-4" />
      </button>

      <button
        className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        title="Like"
      >
        <img src="/icons/like.png" alt="Like" className="h-4 w-4" />
      </button>

      <button
        className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        title="Dislike"
      >
        <img src="/icons/dislike.png" alt="Dislike" className="h-4 w-4" />
      </button>

      <button
        className="flex h-8 w-8 items-center justify-center rounded-md text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700"
        title="Unggah"
      >
        <img src="/icons/ungah.png" alt="Ungah" className="h-4 w-4" />
      </button>
    </div>
  );
};
