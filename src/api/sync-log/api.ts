import {
  TResponseSyncLogDetail,
  TResponseSyncLogs,
  TSyncLogDetail,
  TSyncLogItem,
  TSyncLogParams
} from './type';

// Dummy data for development
const dummySyncLogs: TSyncLogItem[] = [
  {
    id: '1',
    timestamp: '2025-11-04T17:30:15',
    status: 'partial_success',
    total_documents: 50,
    success_count: 48,
    failed_count: 2,
    metadata: { title: 'Sync Log 1' }
  },
  {
    id: '2',
    timestamp: '2025-11-04T09:15:00',
    status: 'success',
    total_documents: 50,
    success_count: 50,
    failed_count: 0,
    metadata: { title: 'Sync Log 2' }
  },
  {
    id: '3',
    timestamp: '2025-11-03T14:00:10',
    status: 'failed',
    total_documents: 50,
    success_count: 0,
    failed_count: 50,
    global_error:
      "API Request Gagal: 'https://portal.combiphar.com' tidak merespon (500 Internal Server Error). Token mungkin kedaluwarsa atau server down.",
    metadata: { title: 'Sync Log 3' }
  },
  {
    id: '4',
    timestamp: '2025-11-02T10:20:30',
    status: 'success',
    total_documents: 45,
    success_count: 45,
    failed_count: 0,
    metadata: { title: 'Sync Log 4' }
  },
  {
    id: '5',
    timestamp: '2025-11-01T16:45:20',
    status: 'partial_success',
    total_documents: 52,
    success_count: 50,
    failed_count: 2,
    metadata: { title: 'Sync Log 5' }
  }
];

const dummySyncLogDetails: TSyncLogDetail[] = [
  {
    id: '1',
    timestamp: '2025-11-04T17:30:15',
    status: 'partial_success',
    total_documents: 50,
    success_count: 48,
    failed_count: 2,
    metadata: { title: 'Sync Log 1' },
    failed_documents: [
      {
        title: 'SK Direksi - Tunjangan Mutasi',
        file_id: 'a226-cee...338d',
        error_message: 'Gagal mengunduh: File not found (404) on Portal.'
      },
      {
        title: 'SK Direksi - Bantuan Penggantian Biaya Kacamata',
        file_id: 'b722-e89...59',
        error_message: "Error database: DocumentId '45' already exists."
      }
    ]
  },
  {
    id: '2',
    timestamp: '2025-11-04T09:15:00',
    status: 'success',
    total_documents: 50,
    success_count: 50,
    failed_count: 0,
    metadata: { title: 'Sync Log 2' },
    failed_documents: []
  },
  {
    id: '3',
    timestamp: '2025-11-03T14:00:10',
    status: 'failed',
    total_documents: 50,
    success_count: 0,
    failed_count: 50,
    metadata: { title: 'Sync Log 3' },
    global_error:
      "API Request Gagal: 'https://portal.combiphar.com' tidak merespon (500 Internal Server Error). Token mungkin kedaluwarsa atau server down.",
    failed_documents: [
      {
        title: 'Gagal mengambil daftar',
        file_id: 'N/A',
        error_message: 'Lihat global error di atas'
      }
    ]
  },
  {
    id: '4',
    timestamp: '2025-11-02T10:20:30',
    status: 'success',
    total_documents: 45,
    success_count: 45,
    failed_count: 0,
    metadata: { title: 'Sync Log 4' },
    failed_documents: []
  },
  {
    id: '5',
    timestamp: '2025-11-01T16:45:20',
    status: 'partial_success',
    total_documents: 52,
    success_count: 50,
    failed_count: 2,
    metadata: { title: 'Sync Log 5' },
    failed_documents: [
      {
        title: 'Laporan Tahunan 2024',
        file_id: 'c123-abc...456',
        error_message: 'File size exceeds limit (50MB).'
      },
      {
        title: 'Peraturan Internal Baru',
        file_id: 'd456-def...789',
        error_message: 'Invalid file format: expected PDF, got DOCX.'
      }
    ]
  }
];

export const getSyncLogs = async (
  params?: TSyncLogParams
): Promise<TResponseSyncLogs> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 500));

  console.log('Fetching sync logs with params:', params);

  let filteredLogs = [...dummySyncLogs];

  // Filter by search
  if (params?.search) {
    const searchLower = params.search.toLowerCase();
    filteredLogs = filteredLogs.filter(
      (log) =>
        log.id.toLowerCase().includes(searchLower) ||
        log.status.toLowerCase().includes(searchLower) ||
        log?.title?.toLowerCase().includes(searchLower) ||
        log?.metadata?.title?.toLowerCase().includes(searchLower) ||
        log?.original_filename?.toLowerCase().includes(searchLower)
    );
  }

  // Filter by status
  if (params?.status && params.status !== 'all') {
    filteredLogs = filteredLogs.filter((log) => log.status === params.status);
  }

  // Filter by date range
  if (params?.date_start) {
    filteredLogs = filteredLogs.filter(
      (log) => new Date(log.timestamp) >= new Date(params.date_start!)
    );
  }
  if (params?.date_end) {
    filteredLogs = filteredLogs.filter(
      (log) => new Date(log.timestamp) <= new Date(params.date_end!)
    );
  }

  // Sort by timestamp descending
  filteredLogs.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  // Pagination
  const page = params?.page || 1;
  const pageSize = params?.page_size || 10;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedLogs = filteredLogs.slice(startIndex, endIndex);

  const totalPages = Math.ceil(filteredLogs.length / pageSize);

  return {
    data: paginatedLogs,
    message: 'Success',
    pageCount: totalPages,
    page: page,
    pagination: {
      currentPage: page,
      total: filteredLogs.length,
      totalPage: totalPages,
      hasPreviousPage: page > 1,
      hasNextPage: page < totalPages,
      page_size: pageSize,
      page: page,
      total_pages: totalPages
    }
  };
};

export const getSyncLogDetail = async (
  id: string
): Promise<TResponseSyncLogDetail> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 300));

  const detail = dummySyncLogDetails.find((log) => log.id === id);

  if (!detail) {
    throw new Error('Sync log not found');
  }

  return {
    data: detail,
    message: 'Success',
    pageCount: 1,
    page: 1
  };
};

export const clearSyncLogs = async (): Promise<{ message: string }> => {
  // Simulate API delay
  await new Promise((resolve) => setTimeout(resolve, 1000));

  // In real implementation, this would clear the logs from database
  return {
    message: 'All sync logs have been cleared successfully'
  };
};
