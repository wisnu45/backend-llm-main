import { useState } from 'react';
import dayjs from 'dayjs';
import {
  FileReferences,
  IconBar,
  MarkdownRenderer,
  TypingEffect
} from './chat-item';
import { ChatItemData } from './types';

interface ChatItemProps {
  data: ChatItemData;
}

const isRecentMessage = (createdAt: string | Date) => {
  return dayjs().diff(dayjs(createdAt), 'second') < 5;
};

export const ChatItem = ({ data }: ChatItemProps) => {
  const {
    question,
    answer,
    created_at,
    id,
    chat_id,
    feedback,
    source_documents,
    attachments
  } = data;

  const cleanedAnswer = (answer ?? '')
    .replace(/([.])\n(?=•)/g, '$1\n\n')
    .replace(/\n{1,}(?=\s*-\s)/g, '\n');
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  const handleTypingComplete = () => {
    setIsTypingComplete(true);
  };

  return (
    <div className="mb-10 space-y-4">
      <div className="flex justify-end">
        <div className="rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {question}
          {attachments && attachments.length > 0 && (
            <div className="mt-2 flex space-x-2 overflow-x-auto pb-2">
              {attachments.map((file, index) => (
                <img
                  key={index}
                  src={file.url}
                  alt={`attachment-${index}`}
                  className="h-60 w-auto flex-shrink-0 rounded"
                />
              ))}
            </div>
          )}
          <IconBar
            text={question}
            id={id}
            chat_id={chat_id}
            feedback={feedback}
            isQuestion={true}
          />
        </div>
      </div>
      <div className="col-auto flex flex-col items-start space-y-3 overflow-hidden">
        {isRecentMessage(created_at) ? (
          <TypingEffect
            text={cleanedAnswer}
            typingSpeed={8}
            onComplete={handleTypingComplete}
          />
        ) : (
          <MarkdownRenderer content={cleanedAnswer} />
        )}
        {(isTypingComplete || !isRecentMessage(created_at)) && (
          <>
            <FileReferences fileLinks={source_documents || []} />
            <IconBar
              text={answer}
              id={id}
              chat_id={chat_id}
              feedback={feedback}
              isQuestion={false}
            />
          </>
        )}
      </div>
    </div>
  );
};
