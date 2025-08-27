import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2 } from 'lucide-react';

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  title: string;
  itemName?: string;
  onDelete: () => void;
  loading?: boolean;
}

const DeleteModal = ({
  loading,
  onDelete,
  itemName,
  open,
  onOpenChange,
  title
}: Props) => {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-md"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>

        <p>
          {itemName && (
            <>
              <span className="font-semibold">{itemName}</span>{' '}
            </>
          )}
          will be permanently deleted. This action cannot be undone. Continue?
        </p>

        <DialogFooter className="mt-2 sm:justify-start">
          <Button
            variant="destructive"
            type="submit"
            className="w-full"
            disabled={loading}
            onClick={onDelete}
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              'Delete'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteModal;
