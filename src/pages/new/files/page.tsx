import { Suspense, useState, useEffect } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { DataTable } from '@/components/shared/data-table';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { LoaderCircle } from '@/components/shared/loader';
import { TDocItem } from '@/api/document/type';
import useGetListDocument from './_hooks/get-list-document';
import { formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import FilesPageHeader from './_components/files-page-header';
import FilesPageModals from './_components/files-page-modals';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

const useFilesPage = () => {
  const [modal, setModal] = useState<TModal>(null);
  const [data, setData] = useState<TDocItem | null>(null);
  const [tab, setTab] = useState('all');
  const query = useGetListDocument();

  const handleSetModal = (modal: TModal, data: TDocItem | null) => {
    setModal(modal);
    setData(data);
  };

  useEffect(() => {
    if (query.error) {
      toast({
        title: 'Failed to fetch documents',
        description: query.error?.message || 'An unexpected error occurred',
        variant: 'destructive'
      });
    }
  }, [query.error]);

  return {
    data,
    modal,
    setModal: handleSetModal,
    tab,
    setTab,
    query
  };
};

const getColumns = (
  setModal: (modal: TModal, data: TDocItem) => void
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
  {
    accessorKey: 'portal_id',
    header: 'PORTAL ID',
    cell: ({ row }) => <div>{row.getValue('portal_id') ?? '-'}</div>
  },
  {
    id: 'document-info',
    header: 'document name',
    cell: ({ row }) => (
      <div className="flex flex-col">
        <span>{row.original.document_name?.split('.')[0]}</span>
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
    accessorKey: 'metaData',
    header: '',
    cell: ({ row }) => {
      const isMetaDocument = row.original.metadata === 'Meta Data Document';
      const color = isMetaDocument ? '#5C47DB' : '#20AB4A';

      return (
        <div>
          <Badge
            className={`bg-[${color}]/10 text-[${color}] hover:bg-[${color}/15]`}
          >
            TODO
          </Badge>
        </div>
      );
    }
  },
  {
    header: 'Action',
    cell: ({ row }) => (
      <div>
        <Button
          variant="ghost"
          onClick={() => setModal('detail', row.original)}
        >
          View
        </Button>
        <Button variant="ghost" onClick={() => setModal('edit', row.original)}>
          Edit
        </Button>
        <Button
          className={
            row.original.metadata === 'Meta Data Document' ? 'hidden' : ''
          }
          variant="ghost"
          onClick={() => setModal('delete', row.original)}
        >
          Delete
        </Button>
      </div>
    )
  }
];

const FilesPage = () => {
  const { modal, setModal, data, tab, setTab, query } = useFilesPage();
  const columns = getColumns(setModal);

  return (
    <div>
      <FilesPageHeader setModal={(modal) => setModal(modal, null)} />
      <Tabs
        defaultValue="all"
        onValueChange={(val) => {
          setTab(val);
        }}
      >
        <TabsList>
          <TabsTrigger value="all">All Document Files</TabsTrigger>
          <TabsTrigger value="metadata">Metadata Document</TabsTrigger>
          <TabsTrigger value="upload">Upload Document</TabsTrigger>
        </TabsList>
        <TabsContent value={tab}>
          <Suspense fallback={<LoaderCircle />}>
            <DataTable
              pageCount={10}
              loading={query.isLoading}
              data={query.data?.data || []}
              columns={columns}
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
