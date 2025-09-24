import { TDocItem } from '@/api/document/type';
import { useFiles } from '@/hooks/use-files';
import { useEffect } from 'react';
import useCreateDocument from '../_hooks/create-document';
import useDeleteDocument from '../_hooks/delete-document';
import useEditDocument from '../_hooks/edit-document';
import useGetDetailDocument from '../_hooks/get-detail-document';
import DeleteModal from './delete-modal';
import DetailModal from './detail-modal';
import FormModal from './form-modal';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

interface IFilesPageModals {
  modal: TModal;
  setModal: (modal: TModal) => void;
  data: TDocItem | null;
}

const FilesPageModals = ({ modal, setModal, data }: IFilesPageModals) => {
  const createMutation = useCreateDocument();
  const editMutation = useEditDocument(data?.id!);
  const deleteMutation = useDeleteDocument();
  const detailQuery = useGetDetailDocument(data?.id);
  const { setFiles } = useFiles();

  useEffect(() => {
    if (modal && modal !== 'create') {
      detailQuery.refetch();
    }
  }, [modal, detailQuery]);

  return (
    <>
      <FormModal
        open={modal === 'create'}
        mode="create"
        loading={createMutation.isPending}
        onOpenChange={() => {
          setModal(null);
          setFiles([]);
        }}
        onSubmit={(data) => {
          createMutation.mutate(data, {
            onSuccess: () => {
              setModal(null);
              setFiles([]);
            }
          });
        }}
      />
      <FormModal
        key={detailQuery.data?.data.id}
        open={modal === 'edit'}
        mode="edit"
        loading={editMutation.isPending}
        onOpenChange={() => setModal(null)}
        onSubmit={(data) => {
          editMutation.mutate(data, {
            onSuccess: () => {
              setModal(null);
              setFiles([]);
            }
          });
        }}
        defaultValues={{
          document_name: detailQuery.data?.data.metadata?.Title,
          document_path: detailQuery.data?.data.metadata?.Title,
          portal_id: detailQuery.data?.data.portal_id ?? ''
        }}
      />

      <DetailModal
        open={modal === 'detail'}
        onOpenChange={() => setModal(null)}
        data={detailQuery.data?.data}
        onDelete={() => {
          setModal('delete');
        }}
        onEdit={() => {
          setModal('edit');
        }}
      />

      <DeleteModal
        open={modal === 'delete'}
        data={{
          document_name: detailQuery.data?.data.metadata?.Title
        }}
        loading={deleteMutation.isPending}
        onDelete={() => {
          const id = detailQuery.data?.data.id || data?.id;
          deleteMutation.mutate(
            { id: id! },
            {
              onSuccess: () => {
                setModal(null);
              }
            }
          );
        }}
        onOpenChange={() => setModal(null)}
      />
    </>
  );
};

export default FilesPageModals;
