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

export type TSettingDocument = {
  data_type: string;
  description: string;
  id: string;
  name: string;
  type: string;
  unit: any | null;
  value: string;
};

export type TResponseSettingDocument = TResponse<TSettingDocument[]>;

export type TRequestEditSetting = FormData;
