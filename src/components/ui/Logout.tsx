import { useLogout } from '@/hooks/auth/use-logout';

const Logout = ({ showModal, setShowModal }) => {
  const logoutMutation = useLogout();
  const handleLogout = async () => {
    try {
      const res = await logoutMutation.mutateAsync();
      console.log('CEK CEK', res);
    } catch (err) {
      console.log('cek');
    }
  };
  if (!showModal) {
    return null;
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
      <div className="w-96 rounded-lg bg-white p-6">
        <h3 className="mb-4 text-lg font-semibold">
          Are you sure you want to log out ?
        </h3>
        <div className="flex justify-end gap-4">
          <button
            onClick={() => setShowModal(false)}
            className="rounded-lg bg-gray-200 px-4 py-2 text-sm text-gray-600 hover:bg-gray-300"
          >
            Cancel
          </button>
          <button
            onClick={handleLogout}
            className="rounded-lg bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700"
          >
            Log out
          </button>
        </div>
      </div>
    </div>
  );
};

export default Logout;
