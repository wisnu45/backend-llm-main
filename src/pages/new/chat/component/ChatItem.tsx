import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
          <IconBar />
        )}
      </div>
    </div>
  );
};

const IconBar = () => {
  return (
    <div className="flex space-x-4 p-4">
      <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
        <img src="/icons/copy.png" />
      </button>
      <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
        <img src="/icons/people.png" />
      </button>
      <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
        <img src="/icons/like.png" />
      </button>
      <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
        <img src="/icons/dislike.png" />
      </button>
      <button className="text-gray-600 hover:text-gray-800 focus:outline-none">
        <img src="/icons/ungah.png" />
      </button>
    </div>
  );
};
