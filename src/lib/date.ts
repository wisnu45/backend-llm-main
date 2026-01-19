import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);

export const formatDate = (
  timestamp: string | Date,
  format: string | undefined = 'ddd, DD MMM YYYY HH:mm'
) => {
  return dayjs(timestamp).format(format);
};
