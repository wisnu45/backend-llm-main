import { TResponse } from '@/commons/types/response';

export type TSetting = {
  id: string;
  name: string;
  description: string;
  input: string;
  type: string;
  unit: string | null;
};

export type TResponseListSettings = TResponse<TSetting[]>;
