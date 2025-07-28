import useGetListDocument from '@/pages/new/files/_hooks/get-list-document';
import { FileTextIcon } from '@radix-ui/react-icons';
import { Link } from 'react-router-dom';

interface Props {
  isSidebarOpen: boolean;
}

const DocumentMenu = ({ isSidebarOpen }: Props) => {
  const queryDocument = useGetListDocument();

  return (
    <Link
      to="/files"
      className="flex items-center justify-between rounded-lg p-2 text-sm text-gray-700 hover:bg-gray-400/20"
    >
      {isSidebarOpen ? (
        <div className="flex w-full items-center justify-between">
          <div className="flex gap-2">
            <FileTextIcon className="font-bold" />
            <span className="truncate font-semibold">Document File</span>
          </div>
          <div className="w-12 rounded-full bg-[#B9B7C5] p-1 text-center text-xs text-[#5C47DB]">
            {queryDocument.data?.pagination?.total || 0}
          </div>
        </div>
      ) : (
        <FileTextIcon className="font-bold" />
      )}
    </Link>
  );
};

export default DocumentMenu;
