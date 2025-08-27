import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

export const MarkdownRenderer = ({ content }: { content: string }) => (
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
        <ul className="ml-5 list-outside list-disc space-y-1" {...props} />
      ),
      ol: (props) => (
        <ol className="ml-5 list-outside list-decimal space-y-1" {...props} />
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
            className="text-black, rounded bg-gray-200 px-1 py-0.5 text-sm"
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
