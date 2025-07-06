import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';
import { Link1Icon } from '@radix-ui/react-icons';

type TDetail = {
  document_link: string;
  document_name: string;
  created_at: string;
  updated_at: string;
};

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  data?: TDetail;
  onEdit: (data?: TDetail) => void;
  onDelete: (data?: TDetail) => void;
}

const DetailModal = ({ onEdit, onDelete, data, open, onOpenChange }: Props) => {
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
              Document
            </span>
            <Link
              to={data?.document_link || ''}
              target="_blank"
              className="flex items-center gap-2 text-blue-600 transition-colors duration-200 hover:text-blue-800"
            >
              <Link1Icon />
              <span className="underline">Lihat File</span>
            </Link>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Document Name
            </span>
            <p className="text-base text-gray-800">
              {data?.document_name ?? '-'}
            </p>
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
