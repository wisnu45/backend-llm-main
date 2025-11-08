import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import useGetSyncLogDetail from '../_hooks/get-sync-log-detail';
import { formatDate } from '@/lib/date';
import { LoaderCircle } from '@/components/shared/loader';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';

interface SyncLogDetailModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  logId: string | null;
}

const getStatusBadge = (status: string) => {
  const badges = {
    success: (
      <span className="inline-block rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-800">
        Success
      </span>
    ),
    partial_success: (
      <span className="inline-block rounded-full bg-yellow-100 px-3 py-1 text-xs font-semibold text-yellow-800">
        Partial Success
      </span>
    ),
    failed: (
      <span className="inline-block rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-800">
        Failed
      </span>
    )
  };

  return badges[status as keyof typeof badges] || null;
};

const SyncLogDetailModal = ({
  open,
  onOpenChange,
  logId
}: SyncLogDetailModalProps) => {
  const { data, isLoading } = useGetSyncLogDetail(logId || undefined);

  const detail = data?.data;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            Sync Details{' '}
            {detail &&
              `- ${formatDate(detail.timestamp, 'DD MMM YYYY HH:mm:ss')}`}
          </DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <LoaderCircle />
          </div>
        ) : detail ? (
          <div className="py-4">
            {/* Summary */}
            <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1">{getStatusBadge(detail.status)}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">
                  Total Dokumen
                </dt>
                <dd className="mt-1 text-sm font-semibold">
                  {detail.total_documents}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">
                  Berhasil Sync
                </dt>
                <dd className="mt-1 text-sm font-semibold text-green-600">
                  {detail.success_count}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">
                  Gagal Sync
                </dt>
                <dd className="mt-1 text-sm font-semibold text-red-600">
                  {detail.failed_count}
                </dd>
              </div>
            </div>

            {/* Global Error */}
            {detail.global_error && (
              <Alert variant="destructive" className="mb-4">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{detail.global_error}</AlertDescription>
              </Alert>
            )}

            {/* Failed Documents Table */}
            {detail.failed_documents && detail.failed_documents.length > 0 ? (
              <div>
                <h3 className="mb-2 text-lg font-medium text-gray-900">
                  Detail Dokumen yang Gagal
                </h3>
                <ScrollArea className="rounded-lg border">
                  <div className="max-h-[300px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Document Title</TableHead>
                          <TableHead>FileName / ID</TableHead>
                          <TableHead>Error Message</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {detail.failed_documents.map((doc, index) => (
                          <TableRow key={index}>
                            <TableCell className="font-medium">
                              {doc.title}
                            </TableCell>
                            <TableCell className="text-gray-500">
                              {doc.file_id}
                            </TableCell>
                            <TableCell className="text-red-700">
                              {doc.error_message}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </ScrollArea>
              </div>
            ) : (
              <Alert className="border-green-200 bg-green-50 text-green-700">
                <AlertDescription>
                  Semua dokumen berhasil disinkronkan. Tidak ada error untuk
                  ditampilkan.
                </AlertDescription>
              </Alert>
            )}

            {/* Footer */}
            <div className="mt-6 flex justify-end border-t pt-4">
              <Button variant="outline" onClick={() => onOpenChange(false)}>
                Close
              </Button>
            </div>
          </div>
        ) : (
          <div className="py-8 text-center text-gray-500">
            No data available
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default SyncLogDetailModal;
