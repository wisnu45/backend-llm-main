/* eslint-disable @typescript-eslint/no-explicit-any */
import { CircleCheck, CircleX, File, Loader2, Upload, X } from 'lucide-react';
import React, { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

import { formatBytes } from '@/lib/utils';
import { truncateFileName } from '@/lib/utils';
import { cn } from '@/lib/utils';

import { Button } from '@/components/ui/button';
import { useFiles } from '@/hooks/use-files';

interface FileUploadProps {
  maxFiles?: number;
  maxSize?: number;
  accept: {
    [mimeType: string]: string[];
  };
}

export function FileUpload({
  accept,
  maxFiles = 1,
  maxSize = 2
}: FileUploadProps) {
  const isImage = Object.keys(accept)[0].includes('image/');

  const { files: fileStatus, setFiles, isSubmitting } = useFiles();

  const files = React.useMemo(
    () => fileStatus.map((item) => item.file),
    [fileStatus]
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles?.length && files.length < maxFiles) {
        isImage
          ? setFiles([
              ...files,
              ...acceptedFiles.map((file) =>
                Object.assign(file, { preview: URL.createObjectURL(file) })
              )
            ])
          : setFiles([...files, ...acceptedFiles]);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [files, maxFiles]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept,
    onDrop,
    maxFiles,
    multiple: true,
    maxSize: maxSize * 1024 * 1024
  });

  React.useEffect(() => {
    return () =>
      files.forEach((file) => URL.revokeObjectURL((file as any).preview));
  }, [files]);
  const handleRemove = (index: number) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  const accExtension = Object.values(accept).flat().join(' ');

  return (
    <div className="flex flex-col">
      <div {...getRootProps()}>
        <input {...getInputProps()} />
        <div
          className={cn(
            isDragActive && 'bg-muted/25',
            'flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed py-8 hover:bg-muted/25'
          )}
        >
          <Upload />
          <div className="mt-2 text-sm">
            <strong>Click to upload </strong>
            or drag and drop
          </div>
          <div className="mt-1 text-xs">Accepted types: {accExtension}</div>
          <div className="mt-1 text-xs">
            {maxFiles !== 1
              ? `up to ${maxFiles} files, ${maxSize}MB per file`
              : `up to ${maxSize}MB`}
          </div>
        </div>
      </div>
      {files.length > 0 && (
        <div className="flex items-end justify-between pb-1 pt-3">
          <div className="text-sm font-semibold">File accepted</div>
          <div
            className="text-sm hover:cursor-pointer hover:text-destructive"
            onClick={() => setFiles([])}
          >
            Clear
          </div>
          {/* <Button
            disabled={loading}
            type="button"
            className="w-28 rounded-md text-xs"
            size="sm"
            onClick={onUploadSubmit}
          >
            {loading ? (
              <LoaderCircle className="ml-2 size-4 animate-spin" />
            ) : (
              <>
                Upload files
                <CloudUpload className="ml-2 size-4" />
              </>
            )}
          </Button> */}
        </div>
      )}
      <div className="flex flex-col justify-center gap-2">
        {fileStatus.map((fs, index) => (
          <div
            className="flex justify-between rounded-md border px-4 py-3"
            key={index}
          >
            <div className="flex items-center gap-4 text-sm">
              <div className={cn('relative', isImage ? 'size-16' : 'size-8')}>
                {isImage ? (
                  <img
                    src={(fs.file as any).preview}
                    alt={fs.file.name}
                    onLoad={() => {
                      URL.revokeObjectURL((fs.file as any).preview);
                    }}
                    className="rounded-lg object-cover"
                  />
                ) : (
                  <File className="size-8" />
                )}
              </div>
              <div className="flex flex-col">
                <span className="inline-block max-w-[300px] text-sm font-semibold">
                  {truncateFileName(fs.file.name, 30)}
                </span>
                <span className="text-xs text-gray-500">
                  {formatBytes(fs.file.size)}
                </span>
                <span className="text-xs tracking-tight text-destructive">
                  {fs.errorMessage}
                </span>
              </div>
            </div>
            <div className="flex items-center">
              {fs.status === 'pending' && !isSubmitting && (
                <Button
                  variant="link"
                  size="icon"
                  type="button"
                  onClick={() => handleRemove(index)}
                >
                  <X className="size-4 hover:text-destructive" />
                </Button>
              )}
              {fs.status === 'success' && (
                <CircleCheck className="text-green-600" />
              )}
              {fs.status === 'failed' && (
                <CircleX className="text-destructive" />
              )}
              {fs.status === 'processing' && (
                <Loader2 className="animate-spin text-gray-500" />
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
