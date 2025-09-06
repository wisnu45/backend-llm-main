import React, { useState } from 'react';

interface RenameModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (newName: string) => void;
  loading?: boolean;
  title?: string;
  description?: string;
  initialValue?: string;
}

const RenameModal: React.FC<RenameModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  loading = false,
  title = 'Rename Chat',
  description = 'Enter a new name for this chat.',
  initialValue = ''
}) => {
  const [name, setName] = useState(initialValue);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-xl bg-white p-6 shadow-lg">
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mb-4 text-sm text-gray-500">{description}</p>

        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter new name"
          className="mb-4 w-full rounded-md border px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border px-4 py-2 hover:bg-gray-100"
            disabled={loading}
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirm(name)}
            className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
            disabled={loading || !name.trim()}
          >
            {loading ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RenameModal;
