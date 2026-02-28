import { AxiosError } from 'axios';

export type TErrorItem = {
  code: number;
  message: string;
};

export type TErrorResponse = AxiosError<TErrorItem>;
