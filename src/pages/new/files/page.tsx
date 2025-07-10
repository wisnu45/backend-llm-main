import { Suspense, useState, useEffect } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/shared/data-table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { LoaderCircle } from '@/components/shared/loader';
import { TDocItem } from '@/api/document/type';
import useGetListDocument from './_hooks/get-list-document';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import FilesPageHeader from './_components/files-page-header';
import FilesPageModals from './_components/files-page-modals';
import { useDebounce } from 'use-debounce';
import { useSearchParams } from 'react-router-dom'; // Import useSearchParams

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

const useFilesPage = () => {
  const [modal, setModal] = useState<TModal>(null);
  const [data, setData] = useState<TDocItem | null>(null);
  const [tab, setTab] = useState('all');
  const [textSearch, setTextSearch] = useState<string>('');
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [debouncedValue] = useDebounce(textSearch, 1000);

  const [searchParams, setSearchParams] = useSearchParams();

  const handleSetModal = (modal: TModal, data: TDocItem | null) => {
    setModal(modal);
    setData(data);
  };
  const pageFromURL = searchParams.get('page')
    ? Number(searchParams.get('page'))
    : 0;
  const limitFromURL = searchParams.get('limit')
    ? Number(searchParams.get('limit'))
    : 10;

  useEffect(() => {
    setPageIndex(pageFromURL);
    setPageSize(limitFromURL);
  }, [searchParams]);

  const query = useGetListDocument(debouncedValue, pageIndex, pageSize);

  const updateURLParams = (newPageIndex: number, newPageSize: number) => {
    setSearchParams({
      page: newPageIndex.toString(),
      limit: newPageSize.toString()
    });
  };

  useEffect(() => {
    setPageIndex(1);
  }, [textSearch]);

  return {
    data,
    modal,
    setModal: handleSetModal,
    tab,
    setTab,
    textSearch,
    setTextSearch,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    query,
    updateURLParams
  };
};

const getColumns = (
  setModal: (modal: TModal, data: TDocItem) => void,
  tab: string
): ColumnDef<TDocItem>[] => [
  {
    accessorKey: 'id',
    header: 'NO',
    cell: ({ row }) => <div>{row.index + 1}</div>
  },
  {
    accessorKey: 'id',
    header: 'file id',
    cell: ({ row }) => <div className="max-w-[150px]">{row.getValue('id')}</div>
  },
  ...(tab !== 'upload'
    ? [
        {
          accessorKey: 'portal_id',
          header: 'PORTAL ID',
          cell: ({ row }) => <div>{row.getValue('portal_id') ?? '-'}</div>
        }
      ]
    : []),
  {
    id: 'document-info',
    header: 'document name',
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span>{row.original.document_name?.split('.pdf')[0]}</span>
        <span className="font-semibold text-gray-400">PDF</span>
      </div>
    )
  },
  {
    accessorKey: 'dateCreate',
    header: 'Data Create',
    cell: ({ row }) => <div>{formatDate(row.original.created_at)}</div>
  },
  {
    accessorKey: 'dateUpdate',
    header: 'Data Update',
    cell: ({ row }) => (
      <div>
        {(row.original.updated_at && formatDate(row.original.updated_at)) ||
          '-'}
      </div>
    )
  },
  {
    header: 'Action',
    cell: ({ row }) => {
      return (
        <div>
          <Button
            variant="ghost"
            onClick={() => setModal('detail', row.original)}
          >
            View
          </Button>
          <Button
            variant="ghost"
            onClick={() => setModal('edit', row.original)}
          >
            Edit
          </Button>
          <Button
            className={row.original.portal_id ? 'hidden' : ''}
            variant="ghost"
            onClick={() => setModal('delete', row.original)}
          >
            Delete
          </Button>
        </div>
      );
    }
  }
];

const FilesPage = () => {
  const {
    modal,
    setModal,
    data,
    tab,
    setTab,
    setTextSearch,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
    query,
    updateURLParams
  } = useFilesPage();

  const columns = getColumns(setModal, tab);

  const setInput = (value: React.ChangeEvent<HTMLInputElement>) => {
    setPageIndex(0);
    setTextSearch(value.target.value);
  };

  const handlePageChange = (newPageIndex: number) => {
    setPageIndex(newPageIndex);
    updateURLParams(newPageIndex, pageSize);
  };

  const handlePageSizeChange = (newPageSize: number) => {
    setPageSize(newPageSize);
    updateURLParams(pageIndex, newPageSize);
  };

  return (
    <div>
      <FilesPageHeader
        setModal={(modal) => setModal(modal, null)}
        setInput={setInput}
      />
      <Tabs
        defaultValue="all"
        onValueChange={(val) => {
          setTab(val);
        }}
      >
        <ScrollArea className="w-full">
          <TabsList className="flex w-max min-w-full flex-row space-x-4">
            <TabsTrigger value="all" className="w-full sm:w-auto">
              All Document Files
            </TabsTrigger>
            <TabsTrigger value="metadata" className="w-full sm:w-auto">
              Metadata Document
            </TabsTrigger>
            <TabsTrigger value="upload" className="w-full sm:w-auto">
              Upload Document
            </TabsTrigger>
          </TabsList>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
        <TabsContent value={tab}>
          <Suspense fallback={<LoaderCircle />}>
            <DataTable
              pageCount={query.data?.pagination?.total_pages || 0}
              loading={query.isLoading}
              data={query.data?.data || []}
              columns={columns}
              pageSizeOptions={[10, 20, 30, 40, 50]}
              setPageIndex={handlePageChange}
              pageIndex={pageIndex}
              setPageSize={handlePageSizeChange}
              total={query.data?.pagination?.total || 0}
            />
          </Suspense>
        </TabsContent>
      </Tabs>

      <FilesPageModals
        data={data}
        modal={modal}
        setModal={(modal) => setModal(modal, data)}
      />
    </div>
  );
};

export default FilesPage;
