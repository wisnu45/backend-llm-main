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
            View role information and assigned permissions.
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
              Permissions ({data?.permissions?.length || 0})
            </span>
            <div className="flex flex-wrap gap-1">
              {data?.permissions?.map((permission) => (
                <span
                  key={permission.id}
                  className="inline-block rounded-lg bg-green-50 px-2 py-1 text-xs text-green-600"
                >
                  {permission.name}
                </span>
              )) || (
                <span className="text-sm text-gray-500">
                  No permissions assigned
                </span>
              )}
            </div>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Created Date
            </span>
            <p className="text-base text-gray-800">
              {data?.created_at ? formatDate(data.created_at) : '-'}
            </p>
          </div>

          <div>
            <span className="mb-1 block text-sm font-semibold text-gray-500">
              Last Updated
            </span>
            <p className="text-base text-gray-800">
              {data?.updated_at ? formatDate(data.updated_at) : '-'}
            </p>
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
