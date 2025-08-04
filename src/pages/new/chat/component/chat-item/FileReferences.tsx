import { useOpenPdf } from '@/hooks/use-donwload-file';
import { FileLink } from '../types';

export const FileReferences = ({ fileLinks }: { fileLinks: FileLink[] }) => {
  const openPdf = useOpenPdf();

  if (!fileLinks || fileLinks.length === 0) {
    return null;
  }

  return (
    <div className="w-full">
      <hr className="mb-2 w-full border-t-4 border-[#C4C4C480]" />
      <div className="font-bold">Referensi Sumber:</div>
      <div className="flex flex-col">
        {fileLinks.map((item, index) => (
          <a
            key={item.download_url}
            href="#"
            onClick={(e) => {
              e.preventDefault();
              openPdf.mutate(item.download_url);
            }}
            className="inline-block w-max cursor-pointer rounded-md px-2 py-1 text-blue-400 hover:underline"
          >
            {index + 1}. {item.filename}
          </a>
        ))}
      </div>
    </div>
  );
};
