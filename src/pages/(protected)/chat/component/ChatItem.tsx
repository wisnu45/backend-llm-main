import { useState } from 'react';
import dayjs from 'dayjs';
import {
  FileReferences,
  IconBar,
  MarkdownRenderer,
  TypingEffect
} from './chat-item';
import { ChatItemData } from './types';
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/dialog';
import { DialogTitle } from '@radix-ui/react-dialog';

interface ChatItemProps {
  data: ChatItemData;
  chatEndRef?: React.RefObject<HTMLDivElement>;
}

const isRecentMessage = (createdAt: string | Date) => {
  return dayjs().diff(dayjs(createdAt), 'second') < 5;
};

export const ChatItem = ({ data, chatEndRef }: ChatItemProps) => {
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

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewType, setPreviewType] = useState<string | null>(null);
  const [previewFileName, setPreviewFileName] = useState<string | null>(null);

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
                <div
                  key={index}
                  className="relative flex items-center justify-center rounded-lg bg-gray-700 p-3 hover:cursor-pointer"
                  onClick={() => {
                    setPreviewUrl(file.url);
                    setPreviewType(file?.mimetype);
                    setPreviewFileName(
                      file?.original_filename || file?.ext || 'file'
                    );
                  }}
                >
                  <div className="flex flex-col items-center hover:cursor-pointer">
                    {file?.mimetype?.startsWith('image') ? (
                      <img
                        src={file.url}
                        alt={file?.original_filename || file?.url}
                        className="h-24 w-24 rounded-lg object-cover hover:cursor-pointer"
                      />
                    ) : file?.mimetype === 'application/pdf' ? (
                      <iframe
                        src={file.url}
                        title={file?.original_filename || file?.ext}
                        className="h-24 w-24 rounded-lg object-cover hover:cursor-pointer"
                      />
                    ) : file?.mimetype ===
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                      file?.mimetype === 'application/vnd.ms-excel' ? (
                      <div className="flex h-24 w-24 cursor-pointer flex-col items-center justify-center rounded-lg bg-gray-100 p-2 text-center text-xs">
                        <span className="text-xl">📊</span>
                        <p className="w-full truncate text-gray-700">
                          {file?.original_filename || 'Excel'}
                        </p>
                      </div>
                    ) : file?.mimetype ===
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                      file?.mimetype === 'application/msword' ? (
                      <div className="flex h-24 w-24 cursor-pointer flex-col items-center justify-center rounded-lg bg-gray-100 p-2 text-center text-xs">
                        <span className="text-xl">📝</span>
                        <p className="w-full truncate text-gray-700">
                          {file?.original_filename || 'Word'}
                        </p>
                      </div>
                    ) : (
                      <div className="flex h-24 w-24 cursor-pointer flex-col items-center justify-center rounded-lg bg-gray-100 p-2 text-center text-xs">
                        <span className="text-xl">📄</span>
                        <p className="w-full truncate text-gray-700">
                          {file?.original_filename || file?.ext || 'Document'}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
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
          <>
            <TypingEffect
              text={cleanedAnswer}
              typingSpeed={8}
              onComplete={handleTypingComplete}
            />
            <div ref={chatEndRef}></div>
          </>
        ) : (
          <>
            <MarkdownRenderer content={cleanedAnswer} />
            <div ref={chatEndRef}></div>
          </>
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

      {previewUrl && (
        <Dialog
          open={!!previewUrl}
          onOpenChange={() => {
            setPreviewUrl(null);
            setPreviewType(null);
            setPreviewFileName(null);
          }}
        >
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>Preview File</DialogTitle>
            </DialogHeader>

            {previewType?.startsWith('image') ? (
              <img
                src={previewUrl}
                className="w-full rounded-lg"
                alt={previewFileName || 'Preview'}
              />
            ) : previewType === 'application/pdf' ? (
              <iframe src={previewUrl} className="h-[80vh] w-full rounded-lg" />
            ) : (
              <div className="flex h-[50vh] w-full flex-col items-center justify-center gap-4">
                <span className="text-6xl">
                  {previewType ===
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
                  previewType === 'application/vnd.ms-excel'
                    ? '📊'
                    : previewType ===
                          'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                        previewType === 'application/msword'
                      ? '📝'
                      : '📄'}
                </span>
                <p className="text-lg font-semibold">{previewFileName}</p>
                <p className="text-sm text-gray-500">
                  Preview tidak tersedia untuk file ini
                </p>
                <a
                  href={previewUrl}
                  download={previewFileName}
                  className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
                >
                  Download file
                </a>
              </div>
            )}
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};
