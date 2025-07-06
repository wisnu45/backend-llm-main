import FormModal from './form-modal';
import DetailModal from './detail-modal';
import DeleteModal from './delete-modal';
import useCreateDocument from '../_hooks/create-document';
import { TDocItem } from '@/api/document/type';
import useDeleteDocument from '../_hooks/delete-document';
import { useFiles } from '@/hooks/use-files';

type TModal = 'delete' | 'edit' | 'create' | 'detail' | null;

interface IFilesPageModals {
  modal: TModal;
  setModal: (modal: TModal) => void;
  data: TDocItem | null;
}

const FilesPageModals = ({ modal, setModal, data }: IFilesPageModals) => {
  const createMutation = useCreateDocument();
  const deleteMutation = useDeleteDocument();
  const { setFiles } = useFiles();

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
        open={modal === 'edit'}
        mode="edit"
        onOpenChange={() => setModal(null)}
        onSubmit={() => {}}
        defaultValues={{
          document_name: 'Aturan Karyawan'
        }}
      />

      <DetailModal
        open={modal === 'detail'}
        onOpenChange={() => setModal(null)}
        data={{
          document_link: 'https://github.com/oemahsolution/dashboard-llm',
          document_name: 'Undang-undang karyawan',
          created_at: '2025-06-27 15:30 PM',
          updated_at: '2025-06-27 15:30 PM'
        }}
        onDelete={() => {}}
        onEdit={() => {
          setModal('edit');
        }}
      />

      <DeleteModal
        open={modal === 'delete'}
        data={{ document_name: data?.document_name }}
        loading={deleteMutation.isPending}
        onDelete={() => {
          deleteMutation.mutate(
            { id: data?.id! },
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
