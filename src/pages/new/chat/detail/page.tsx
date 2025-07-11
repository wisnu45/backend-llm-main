import { ScrollArea } from '@/components/ui/scroll-area';
import { useEffect, useRef, useState } from 'react';
import { useGetDetailHistory } from '../_hook/use-get-history-chat';
import { useNavigate, useParams } from 'react-router-dom';
import { ChatItem } from '../component/ChatItem';
import useCreateChat from '../_hook/use-create-chat';
import { Loader } from '../component/Loader';
import InputData from '../component/InputData';

type FileType = File;

const DetailPage = () => {
  const { chatId } = useParams();
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [text, setText] = useState('');
  const navigate = useNavigate();
  const [isChecked, setIsChecked] = useState(false);
  const [files, setFiles] = useState<FileType[]>([]);

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
  }, [query.data?.data.length, loading]);

  const handleClick = () => {
    if (!text.trim()) return;
    setLoading(true);

    mutation.mutate(payload, {
      onSuccess: () => {
        setLoading(false);
        setText('');
        query.refetch();
        setFiles([]);
      },
      onError: () => {
        setLoading(false);
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
              <div ref={isLast && !loading ? scrollAreaRef : null} key={index}>
                <ChatItem key={index} data={message} />
              </div>
            );
          })}
          {loading && (
            <div className="flex w-full justify-start p-4" ref={scrollAreaRef}>
              <div className="flex max-w-[100%] gap-3">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-md border border-gray-200 bg-white">
                  <img src="/icons/logo-short.png" />
                </div>
                <div className="rounded-2xl rounded-bl-md  px-4 py-3">
                  <div className="flex space-x-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-gray-400"></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.1s' }}
                    ></div>
                    <div
                      className="h-2 w-2 animate-bounce rounded-full bg-gray-400"
                      style={{ animationDelay: '0.2s' }}
                    ></div>
                  </div>
                </div>
              </div>
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
