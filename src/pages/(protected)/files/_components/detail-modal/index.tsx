import { TDocItem } from '@/api/document/type';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { useOpenPdf } from '@/hooks/use-donwload-file';
import { Link } from 'react-router-dom';

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  data?: TDocItem;
  onEdit: (data?: TDocItem) => void;
  onDelete: (data?: TDocItem) => void;
}

const DetailModal = ({ onEdit, onDelete, data, open, onOpenChange }: Props) => {
  const downloadFile = useOpenPdf();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-md"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Detail Document</DialogTitle>
          <DialogDescription>
            Details of AI training document.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              File ID
            </span>
            <p className="text-base text-gray-800">{data?.id ?? '-'}</p>
          </div>
          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Portal ID
            </span>
            <p className="text-base text-gray-800">{data?.portal_id ?? '-'}</p>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Document Name
            </span>
            <Link
              to="#"
              onClick={(e) => {
                e.preventDefault();
                downloadFile.mutate(data?.url || '#');
              }}
            >
              <p className="w-fit text-gray-800 text-primary underline">
                {data?.metadata?.Title || data?.original_filename || '-'}
              </p>
            </Link>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Created Date
            </span>
            <p className="text-base text-gray-800">{data?.created_at ?? '-'}</p>
          </div>
          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Last Updated
            </span>
            <p className="text-base text-gray-800">{data?.updated_at ?? '-'}</p>
          </div>

          <DialogFooter className="mt-2 sm:justify-start">
            <Button
              type="submit"
              className="w-full"
              onClick={() => onEdit(data)}
            >
              Edit
            </Button>
            <Button
              variant="destructive"
              type="submit"
              className="w-full"
              onClick={() => onDelete(data)}
            >
              Delete
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default DetailModal;
