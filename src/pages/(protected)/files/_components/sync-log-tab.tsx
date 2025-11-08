import { DataTable } from '@/components/shared/data-table';
import { ColumnDef } from '@tanstack/react-table';
import { useState } from 'react';
import { useDebounce } from 'use-debounce';
import SyncLogFilters from './sync-log-filters';
import SyncLogDetailModal from './sync-log-detail-modal';
import useGetSyncLogs from '../_hooks/get-sync-logs';
import { TSyncLogItem, TSyncStatus } from '@/api/sync-log/type';
import { formatDate } from '@/lib/date';
import { Button } from '@/components/ui/button';
import { DateRange } from 'react-day-picker';
import { format } from 'date-fns';

const getStatusBadge = (status: TSyncStatus) => {
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

  return badges[status];
};

const SyncLogTab = () => {
  const [search, setSearch] = useState('');
  const [dateRange, setDateRange] = useState<DateRange | undefined>();
  const [status, setStatus] = useState<TSyncStatus | 'all'>('all');
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [selectedLogId, setSelectedLogId] = useState<string | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const [debouncedSearch] = useDebounce(search, 1000);

  const query = useGetSyncLogs({
    search: debouncedSearch,
    date_start: dateRange?.from ? format(dateRange.from, 'yyyy-MM-dd') : '',
    date_end: dateRange?.to ? format(dateRange.to, 'yyyy-MM-dd') : '',
    status: status,
    page: pageIndex + 1,
    page_size: pageSize
  });

  const handleViewDetails = (logId: string) => {
    setSelectedLogId(logId);
    setIsDetailModalOpen(true);
  };

  const handleClearFilters = () => {
    setSearch('');
    setDateRange(undefined);
    setStatus('all');
  };

  const columns: ColumnDef<TSyncLogItem>[] = [
    {
      accessorKey: 'timestamp',
      header: 'Tanggal & Waktu',
      cell: ({ row }) => (
        <div className="min-w-40">
          {formatDate(row.original.timestamp, 'DD MMM YYYY HH:mm:ss')}
        </div>
      )
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <div className="min-w-32">{getStatusBadge(row.original.status)}</div>
      )
    },
    {
      accessorKey: 'success_count',
      header: 'Dok. Berhasil',
      cell: ({ row }) => (
        <div className="min-w-28 font-bold text-green-600">
          {row.original.success_count}
        </div>
      )
    },
    {
      accessorKey: 'failed_count',
      header: 'Dok. Gagal',
      cell: ({ row }) => (
        <div className="min-w-28 font-bold text-red-600">
          {row.original.failed_count}
        </div>
      )
    },
    {
      id: 'actions',
      header: 'Aksi',
      cell: ({ row }) => (
        <div className="min-w-32">
          <Button
            variant="ghost"
            onClick={() => handleViewDetails(row.original.id)}
          >
            View Details
          </Button>
        </div>
      )
    }
  ];

  const { page, page_size, total_pages, total } = query.data?.pagination || {};

  return (
    <div className="">
      <SyncLogFilters
        search={search}
        setSearch={setSearch}
        dateRange={dateRange}
        setDateRange={setDateRange}
        status={status}
        setStatus={setStatus}
        onClearFilters={handleClearFilters}
      />

      <DataTable
        pageCount={total_pages || 0}
        loading={query.isLoading}
        data={query.data?.data || []}
        columns={columns}
        pageSizeOptions={[10, 20, 30, 40, 50]}
        setPageIndex={setPageIndex}
        pageIndex={pageIndex}
        setPageSize={setPageSize}
        total={total || 0}
        pageSize={page_size || 10}
      />

      <SyncLogDetailModal
        open={isDetailModalOpen}
        onOpenChange={setIsDetailModalOpen}
        logId={selectedLogId}
      />
    </div>
  );
};

export default SyncLogTab;
