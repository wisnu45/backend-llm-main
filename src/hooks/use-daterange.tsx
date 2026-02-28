import dayjs from 'dayjs';
import { DateRange } from 'react-day-picker';
import { useSearchParams } from 'react-router-dom';

export function useDateRangeParams(fromKey = 'from', toKey = 'to') {
  const [searchParams, setSearchParams] = useSearchParams();

  const dateRange: DateRange | undefined = {
    from: searchParams.get(fromKey)
      ? dayjs(searchParams.get(fromKey)).toDate()
      : undefined,
    to: searchParams.get(toKey)
      ? dayjs(searchParams.get(toKey)).toDate()
      : undefined
  };

  const setDateRange = (value: DateRange | undefined) => {
    const newSearchParams = new URLSearchParams(searchParams);

    if (value?.from) {
      newSearchParams.set(fromKey, dayjs(value.from).format('YYYY-MM-DD'));
    } else {
      newSearchParams.delete(fromKey);
    }

    if (value?.to) {
      newSearchParams.set(toKey, dayjs(value.to).format('YYYY-MM-DD'));
    } else {
      newSearchParams.delete(toKey);
    }

    setSearchParams(newSearchParams);
  };

  return [dateRange, setDateRange] as const;
}
