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
              Capabilities
            </span>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Chat:</span>
                <span
                  className={data?.chat ? 'text-green-600' : 'text-red-600'}
                >
                  {data?.chat ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>File Management:</span>
                <span
                  className={
                    data?.file_management ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {data?.file_management ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>History:</span>
                <span
                  className={data?.history ? 'text-green-600' : 'text-red-600'}
                >
                  {data?.history ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Chat Attachment:</span>
                <span
                  className={
                    data?.chat_attachment ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {data?.chat_attachment ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>User Management:</span>
                <span
                  className={
                    data?.user_management ? 'text-green-600' : 'text-red-600'
                  }
                >
                  {data?.user_management ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Max Chat Topics:</span>
                <span>{data?.max_chat_topic || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Chat Topic Expired Days:</span>
                <span>{data?.chat_topic_expired_days || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Max Chats:</span>
                <span>{data?.max_chat || 0}</span>
              </div>
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
