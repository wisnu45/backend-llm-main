import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu';
import { ChevronDownIcon, MagnifyingGlassIcon } from '@radix-ui/react-icons';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

interface IFilesPageHeader {
  setModal: (modal: TModal) => void;
  setInput: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

const FilesPageHeader = ({ setModal, setInput }: IFilesPageHeader) => {
  return (
    <>
      <div className="mb-8 flex flex-wrap items-center justify-between">
        <div className="w-full sm:w-auto">
          <h1 className="text-3xl font-bold text-gray-800 sm:text-2xl">
            Document Files
          </h1>
          <p className="text-gray-600 sm:text-sm">
            Organize all your document files here
          </p>
        </div>
      </div>

      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div className="flex w-full items-center overflow-hidden rounded-lg border border-gray-300 bg-white shadow-sm sm:w-auto">
          <input
            type="text"
            placeholder="Search"
            onChange={setInput}
            className="w-full rounded-l-lg px-4 py-2 text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 sm:w-64"
          />
          <button className="rounded-r-lg border-l border-gray-300 bg-gray-50 p-2 hover:bg-gray-100">
            <MagnifyingGlassIcon className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 sm:w-auto">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="inline-flex items-center justify-between gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none">
                Filter Document Files
                <ChevronDownIcon className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
          </DropdownMenu>
        </div>

        <Button
          className="w-full bg-green-500 hover:bg-green-600 sm:w-auto"
          onClick={() => setModal('create')}
        >
          Add New File
        </Button>
      </div>
    </>
  );
};

export default FilesPageHeader;
