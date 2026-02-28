import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { MagnifyingGlassIcon } from '@radix-ui/react-icons';
import useGetDocumentFromPortal from '../_hooks/get-doument-from-portal';
import { TErrorResponse } from '@/commons/types/response';

import { TDocParams } from '@/api/document/type';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;
type TTab = TDocParams['source_type'] | 'synclog';

interface IFilesPageHeader {
  setModal: (modal: TModal) => void;
  setInput: (event: React.ChangeEvent<HTMLInputElement>) => void;
  tab: TTab;
}

const FilesPageHeader = ({ setModal, setInput, tab }: IFilesPageHeader) => {
  const { mutateAsync, isPending } = useGetDocumentFromPortal();

  const handleSyncPortal = async () => {
    try {
      const res = await mutateAsync();
      if (res) {
        toast({
          title: 'Success',
          description: res.message
            ? res.message
            : 'Documents synced successfully from portal.'
        });
      }
    } catch (error) {
      const err = error as TErrorResponse;
      toast({
        title: 'Error',
        description: `Failed to sync documents. ${err.response?.data.message}`,
        variant: 'destructive'
      });
    }
  };
  return (
    <>
      <div className="mb-8 flex flex-wrap items-center justify-between">
        <div className="w-full sm:w-auto">
          <h1 className="text-3xl font-bold text-gray-800 sm:text-2xl">
            Document Files
          </h1>
          <p className="text-gray-600 sm:text-sm">
            Organize all your files document here
          </p>
        </div>
      </div>

      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        {tab !== 'synclog' && (
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
        )}
        <div className={`flex gap-3 ${tab === 'synclog' ? 'ml-auto' : ''}`}>
          <Button
            variant="destructive"
            className={`sm:w-auto ${tab !== 'synclog' ? 'hidden' : ''}`}
            onClick={handleSyncPortal}
          >
            {isPending ? 'Syncing...' : 'Sync Portal'}
          </Button>
          {tab !== 'synclog' && (
            <Button
              className="w-full bg-green-500 hover:bg-green-600 sm:w-auto"
              onClick={() => setModal('create')}
            >
              Add New File
            </Button>
          )}
        </div>
      </div>
    </>
  );
};

export default FilesPageHeader;
