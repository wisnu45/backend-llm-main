import { useState, useEffect } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

export default function MarkdownViewer({ text }) {
  const [htmlContent, setHtmlContent] = useState('');

  useEffect(() => {
    const parseMarkdown = async () => {
      const rawHtml = await marked.parse(text || '', { breaks: true });
      const safeHtml = DOMPurify.sanitize(rawHtml);
      setHtmlContent(safeHtml);
    };
    parseMarkdown();
  }, [text]);

  return (
    <div
      className="prose max-w-none text-gray-800"
      dangerouslySetInnerHTML={{ __html: htmlContent }}
    />
  );
}
