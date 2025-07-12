import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useRef, useState } from 'react';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';
import { useNavigate, useParams } from 'react-router-dom';
import { ChatItem } from '../component/ChatItem';
import useCreateChat from '../_hook/use-create-chat';
import { Loader } from '../component/Loader';
import InputData from '../component/InputData';
import { FileType, PromptPreview } from '../component/prompt-preview';
import { ModernLoadingIndicator } from '../component/loading-indicator';

const DetailPage = () => {
  const { chatId } = useParams();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [text, setText] = useState('');
  const navigate = useNavigate();
  const [isChecked, setIsChecked] = useState(false);
  const [files, setFiles] = useState<FileType[]>([]);

  const [previewPrompt, setPreviewPrompt] = useState<string>('');
  const [previewFiles, setPreviewFiles] = useState<FileType[]>([]);
  const [showPreview, setShowPreview] = useState<boolean>(false);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
  };

  const query = useGetDetailHistory({ session_id: chatId || '' });
  const mutation = useCreateChat();

  if (!query.data?.data.length) {
    navigate('/new/chat');
  }

  const payload = {
    question: text,
    session_id: chatId || ''
  };

  useEffect(() => {
    query.refetch();
  }, [chatId]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollIntoView({
        behavior: 'smooth'
      });
    }
  }, [query.data?.data.length, loading, showPreview]);

  const handleClick = () => {
    if (!text.trim()) return;

    setPreviewPrompt(text);
    setPreviewFiles([...files]);
    setShowPreview(true);
    setLoading(true);

    mutation.mutate(payload, {
      onSuccess: () => {
        setLoading(false);
        setText('');
        setShowPreview(false);
        setPreviewPrompt('');
        setPreviewFiles([]);
        query.refetch();
        setFiles([]);
      },
      onError: () => {
        setLoading(false);
        setShowPreview(false);
        setPreviewPrompt('');
        setPreviewFiles([]);
      }
    });
  };

  const handleCheckboxChange = () => {
    setIsChecked(!isChecked);
  };

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      setFiles((prevFiles) => [...prevFiles, ...droppedFiles]);
    } else {
      console.error('Tidak ada file yang ditemukan pada drag-and-drop.');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = e.target.files;
    if (selectedFiles) {
      const newFiles = Array.from(selectedFiles);
      setFiles((prevFiles) => [...prevFiles, ...newFiles]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const removeFile = (index: number) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  return (
    <>
      <ScrollArea className="scrollbar-hide flex-1">
        <div className="mx-auto min-h-full w-[95%] ">
          {query.isLoading && <Loader />}
          {query?.data?.data?.map((message, index) => {
            const isLast = index === (query?.data?.data?.length ?? 0) - 1;
            return (
              <div
                ref={isLast && !loading && !showPreview ? scrollAreaRef : null}
                key={index}
              >
                <ChatItem key={index} data={message} />
              </div>
            );
          })}

          {showPreview && (
            <div ref={scrollAreaRef}>
              <PromptPreview text={previewPrompt} files={previewFiles} />
            </div>
          )}

          {loading && (
            <div ref={scrollAreaRef}>
              <ModernLoadingIndicator />
            </div>
          )}
        </div>
      </ScrollArea>
      <InputData
        handleFileDrop={handleFileDrop}
        handleDragOver={handleDragOver}
        files={files}
        removeFile={removeFile}
        text={text}
        handleChange={handleChange}
        handleFileChange={handleFileChange}
        isChecked={isChecked}
        setText={setText}
        handleCheckboxChange={handleCheckboxChange}
        handleClick={handleClick}
      />
    </>
  );
};

export default DetailPage;
