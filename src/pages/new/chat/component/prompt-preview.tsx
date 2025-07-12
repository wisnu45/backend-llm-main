export type FileType = File;

export const PromptPreview = ({
  text,
  files
}: {
  text: string;
  files: FileType[];
}) => {
  return (
    <div className="mb-10 space-y-4 duration-300 animate-in fade-in">
      <div className="flex justify-end">
        <div className="max-w-[80%] break-words rounded-xl bg-gray-200 px-4 py-2 text-sm text-gray-900">
          {text}
        </div>
      </div>
      {files.length > 0 && (
        <div className="col-auto flex flex-col items-start space-y-3">
          <div className="w-full">
            <div className="mb-2 text-sm font-bold text-gray-600">
              Attachments:
            </div>
            <div className="flex flex-wrap gap-2">
              {files.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-100 px-3 py-2"
                >
                  <span className="max-w-32 truncate text-xs text-gray-600">
                    {file.name}
                  </span>
                  <span className="text-xs text-gray-400">
                    ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
