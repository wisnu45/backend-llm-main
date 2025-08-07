import { Suspense, useState, useEffect } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/shared/data-table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { LoaderCircle } from '@/components/shared/loader';
import { TDocItem, TDocParams } from '@/api/document/type';
import useGetListDocument from './_hooks/get-list-document';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import FilesPageHeader from './_components/files-page-header';
import FilesPageModals from './_components/files-page-modals';
import { useDebounce } from 'use-debounce';
import { Link, useSearchParams } from 'react-router-dom'; // Import useSearchParams
import { useOpenPdf } from '@/hooks/use-donwload-file';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

const useFilesPage = () => {
  const [modal, setModal] = useState<TModal>(null);
  const [data, setData] = useState<TDocItem | null>(null);
  const [tab, setTab] = useState<TDocParams['doc_type']>('all');
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
  const limitFromURL = searchParams.get('page_size')
    ? Number(searchParams.get('page_size'))
    : 10;

  useEffect(() => {
    setPageIndex(pageFromURL);
    setPageSize(limitFromURL);
  }, [searchParams]);

  const query = useGetListDocument({
    search: debouncedValue,
    page: pageIndex,
    page_size: pageSize,
    doc_type: tab
  });

  const updateURLParams = (newPageIndex: number, newPageSize: number) => {
    setSearchParams({
      page: newPageIndex.toString(),
      page_size: newPageSize.toString(),
      tab: 'all'
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
  const downloadFile = useOpenPdf();

  const getColumns = (
    setModal: (modal: TModal, data: TDocItem) => void,
    tab: string,
    startFrom: number
  ): ColumnDef<TDocItem>[] => [
    {
      accessorKey: 'id',
      header: 'NO',
      cell: ({ row }) => <div>{row.index + 1 + startFrom}</div>
    },
    {
      accessorKey: 'id',
      header: 'file id',
      cell: ({ row }) => (
        <div className="max-w-[150px]">{row.getValue('id')}</div>
      )
    },
    ...(tab !== 'upload'
      ? [
          {
            accessorKey: 'portal_id',
            header: 'PORTAL ID',
            cell: ({ row }) => (
              <div className="min-w-28">{row.getValue('portal_id') ?? '-'}</div>
            )
          }
        ]
      : []),
    {
      id: 'document-info',
      header: 'document name',
      cell: ({ row }) => (
        <div className="flex min-w-40 flex-col">
          <span>{row.original.document_name?.split('.pdf')[0]}</span>
          <Link
            to="#"
            onClick={(e) => {
              e.preventDefault();
              downloadFile.mutate('#'); // TODO: replace with file link. waiting for api to be updated
            }}
          >
            <span className="font-semibold text-gray-400">PDF</span>
          </Link>
        </div>
      )
    },
    {
      accessorKey: 'dateCreate',
      header: 'Data Create',
      cell: ({ row }) => (
        <div className="min-w-28">{formatDate(row.original.created_at)}</div>
      )
    },
    {
      accessorKey: 'dateUpdate',
      header: 'Data Update',
      cell: ({ row }) => (
        <div className="min-w-28">
          {(row.original.updated_at && formatDate(row.original.updated_at)) ||
            '-'}
        </div>
      )
    },
    {
      accessorKey: 'metadata',
      header: '',
      cell: ({ row }) => {
        const isMetadata = row.original.portal_id;

        return (
          <div className="min-w-40">
            {isMetadata ? (
              <span className="inline-block rounded-lg bg-[#5C47DB]/10 px-2 py-1 text-[#5C47DB]">
                Metadata Document
              </span>
            ) : (
              <span className="inline-block rounded-lg bg-[#20AB4A]/10 px-2 py-1 text-[#20AB4A]">
                Upload Document
              </span>
            )}
          </div>
        );
      }
    },
    {
      header: 'Action',
      cell: ({ row }) => {
        // const isMetadata = Boolean(row.original.portal_id);

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
              // className={isMetadata ? 'hidden' : ''}
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

  const { page, page_size, total_pages, total } = query.data?.pagination || {};
  const startFrom = (Number(page) - 1) * Number(page_size);
  const columns = getColumns(setModal, tab, startFrom);
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
          setTab(val as TDocParams['doc_type']);
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
              pageCount={total_pages || 0}
              loading={query.isLoading}
              data={query.data?.data || []}
              columns={columns}
              pageSizeOptions={[10, 20, 30, 40, 50]}
              setPageIndex={handlePageChange}
              pageIndex={pageIndex}
              setPageSize={handlePageSizeChange}
              total={total || 0}
              pageSize={page_size || 10}
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
