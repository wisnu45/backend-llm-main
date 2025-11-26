import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@/components/ui/select';
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';
import { TSyncStatus } from '@/api/sync-log/type';
import { CalendarIcon, Trash2, X, RotateCcw } from 'lucide-react';
import useClearSyncLogs from '../_hooks/clear-sync-logs';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger
} from '@/components/ui/alert-dialog';
import { format } from 'date-fns';
import { cn } from '@/lib/utils';
import { DateRange } from 'react-day-picker';

interface SyncLogFiltersProps {
  search: string;
  setSearch: (value: string) => void;
  dateRange: DateRange | undefined;
  setDateRange: (range: DateRange | undefined) => void;
  status: TSyncStatus | 'all';
  setStatus: (value: TSyncStatus | 'all') => void;
  onClearFilters: () => void;
}

const SyncLogFilters = ({
  search,
  setSearch,
  dateRange,
  setDateRange,
  status,
  setStatus,
  onClearFilters
}: SyncLogFiltersProps) => {
  const clearMutation = useClearSyncLogs();

  const handleClearLogs = () => {
    clearMutation.mutate();
  };

  const hasActiveFilters =
    search !== '' || dateRange !== undefined || status !== 'all';

  return (
    <div className="mb-3 rounded-lg border border-gray-200 bg-gray-50 p-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-end">
        {/* Filter Inputs */}
        <div className="grid flex-1 grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
          {/* Search */}
          <div>
            <Label htmlFor="log-search" className="text-sm font-medium">
              Search Log
            </Label>
            <div className="relative">
              <Input
                id="log-search"
                type="text"
                placeholder="Cari error, doc title, dll."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="mt-1 pr-8"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => setSearch('')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Date Range Picker */}
          <div>
            <Label className="text-sm font-medium">Tanggal</Label>
            <div className="relative">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      'mt-1 w-full justify-start text-left font-normal',
                      !dateRange && 'text-muted-foreground'
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {dateRange?.from ? (
                      dateRange.to ? (
                        <>
                          {format(dateRange.from, 'dd MMM yyyy')} -{' '}
                          {format(dateRange.to, 'dd MMM yyyy')}
                        </>
                      ) : (
                        format(dateRange.from, 'dd MMM yyyy')
                      )
                    ) : (
                      <span>Pilih rentang tanggal</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="range"
                    selected={dateRange}
                    onSelect={setDateRange}
                    numberOfMonths={2}
                    initialFocus
                    classNames={{
                      day_range_middle:
                        'aria-selected:bg-accent/30 aria-selected:text-accent-foreground',
                      day_selected:
                        'bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground'
                    }}
                  />
                </PopoverContent>
              </Popover>
              {dateRange && (
                <button
                  type="button"
                  onClick={() => setDateRange(undefined)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Status Filter */}
          <div>
            <Label htmlFor="log-status-filter" className="text-sm font-medium">
              Status
            </Label>
            <div className="relative">
              <Select
                value={status}
                onValueChange={(value) =>
                  setStatus(value as TSyncStatus | 'all')
                }
              >
                <SelectTrigger className="mt-1 w-full">
                  <SelectValue placeholder="Semua Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Semua Status</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="partial_success">
                    Partial Success
                  </SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
              {status !== 'all' && (
                <button
                  type="button"
                  onClick={() => setStatus('all')}
                  className="absolute right-8 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col gap-2 sm:flex-row md:flex-nowrap">
          {/* Clear All Filters Button */}
          {hasActiveFilters && (
            <Button
              variant="outline"
              onClick={onClearFilters}
              className="w-full sm:w-auto"
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Clear Filters
            </Button>
          )}

          {/* Clear Log Button */}
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="destructive"
                className="w-full sm:w-auto"
                disabled={clearMutation.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {clearMutation.isPending ? 'Clearing...' : 'Clear Log'}
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Are you sure?</AlertDialogTitle>
                <AlertDialogDescription>
                  This action will permanently delete all sync logs. This action
                  cannot be undone.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction onClick={handleClearLogs}>
                  Continue
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </div>
    </div>
  );
};

export default SyncLogFilters;
