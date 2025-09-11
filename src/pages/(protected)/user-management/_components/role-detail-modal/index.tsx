import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { TRole } from '@/api/user-management/type';
import { formatDate } from '@/lib/date';

interface Props {
  open?: boolean;
  onOpenChange: () => void;
  data?: TRole;
  onEdit: (data?: TRole) => void;
  onDelete: (data?: TRole) => void;
}

const RoleDetailModal = ({
  onEdit,
  onDelete,
  data,
  open,
  onOpenChange
}: Props) => {
  if (!data) {
    return (
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="no-scrollbar sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Role Details</DialogTitle>
          </DialogHeader>
          <div className="p-4">
            <p>No role data available.</p>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="no-scrollbar sm:max-w-md"
        onInteractOutside={(e) => e.preventDefault()}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle>Role Details</DialogTitle>
          <DialogDescription>
            View role information and capabilities.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3">
          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Role ID
            </span>
            <p className="text-base text-gray-800">{data?.id ?? '-'}</p>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Role Name
            </span>
            <p className="text-base text-gray-800">{data?.name ?? '-'}</p>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Description
            </span>
            <p className="text-base text-gray-800">
              {data?.description ?? '-'}
            </p>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Role Settings
            </span>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Is Local:</span>
                <span
                  className={
                    data?.is_local === true || data?.is_local === 'true'
                      ? 'text-green-600'
                      : 'text-red-600'
                  }
                >
                  {data?.is_local === true || data?.is_local === 'true'
                    ? 'Yes'
                    : 'No'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Is Portal:</span>
                <span
                  className={
                    data?.is_portal === true || data?.is_portal === 'true'
                      ? 'text-blue-600'
                      : 'text-red-600'
                  }
                >
                  {data?.is_portal === true || data?.is_portal === 'true'
                    ? 'Yes'
                    : 'No'}
                </span>
              </div>
            </div>
          </div>

          <DialogFooter className="mt-2 sm:justify-start">
            <Button
              type="button"
              className="w-full"
              onClick={() => onEdit(data)}
            >
              Edit Role
            </Button>
            <Button
              variant="destructive"
              type="button"
              className="w-full"
              onClick={() => onDelete(data)}
            >
              Delete Role
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RoleDetailModal;
