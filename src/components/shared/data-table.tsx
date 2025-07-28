import { Button } from '@/components/ui/button';
import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow
} from '@/components/ui/table';
import {
  ColumnDef,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable,
  PaginationState
} from '@tanstack/react-table';
import { ChevronLeftIcon, ChevronRightIcon } from 'lucide-react';
import { LoaderCircle } from './loader';

interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  loading: boolean;
  pageSizeOptions?: number[];
  pageCount: number;
  pageIndex: number;
  setPageIndex: (pageIndex: number) => void;
  setPageSize: (pageSize: number) => void;
  total: number;
  pageSize: number;
}

export function DataTable<TData, TValue>({
  columns,
  data,
  pageCount,
  loading,
  pageSizeOptions = [10, 20, 30, 40, 50],
  pageIndex,
  setPageIndex,
  setPageSize,
  total,
  pageSize
}: DataTableProps<TData, TValue>) {
  const table = useReactTable({
    data,
    columns,
    pageCount: pageCount ?? -1,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    state: {
      pagination: { pageIndex, pageSize: pageSize }
    },
    onPaginationChange: (
      updater: PaginationState | ((prev: PaginationState) => PaginationState)
    ) => {
      if (typeof updater === 'function') {
        const newState = updater({
          pageIndex,
          pageSize: 10
        });
        setPageIndex(newState.pageIndex);
        setPageSize(newState.pageSize);
      } else {
        setPageIndex(updater.pageIndex);
        setPageSize(updater.pageSize);
      }
    },
    getPaginationRowModel: getPaginationRowModel(),
    manualPagination: true,
    manualFiltering: true
  });

  return (
    <>
      <ScrollArea className="rounded-md border">
        <Table className="relative">
          <TableHeader className="bg-[#5C47DB]">
            {table.getHeaderGroups().map((headerGroup, index) => (
              <TableRow key={index}>
                {headerGroup.headers.map((header, index) => (
                  <TableHead key={index} className="uppercase text-white">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext()
                        )}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody className="bg-white">
            <tr className="h-2" />
            {loading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center">
                  <LoaderCircle />
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row, index) => (
                <TableRow key={index}>
                  {row.getVisibleCells().map((cell, index) => (
                    <TableCell key={index}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-20 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      <div className="mt-4 flex items-center justify-between rounded-lg bg-[#F8F8F8] px-4 py-3">
        <div className="text-sm">
          Showing page {pageIndex} to {pageCount} of {total} entries
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-sm">Items per page</span>
          <Select
            value={`${table.getState().pagination.pageSize}`}
            onValueChange={(value: string) => {
              table.setPageSize(Number(value));
            }}
          >
            <SelectTrigger className="h-8 w-[60px] bg-white">
              <SelectValue
                placeholder={`${table.getState().pagination.pageSize}`}
              />
            </SelectTrigger>
            <SelectContent side="top">
              {pageSizeOptions.map((pageSize, index) => (
                <SelectItem key={index} value={`${pageSize}`}>
                  {pageSize}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="flex gap-2">
            <Button
              aria-label="Go to previous page"
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => setPageIndex(pageIndex - 1)}
              disabled={pageIndex <= 0}
            >
              <ChevronLeftIcon className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              aria-label="Go to next page"
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => setPageIndex(pageIndex + 1)}
              disabled={pageIndex >= pageCount}
            >
              <ChevronRightIcon className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
