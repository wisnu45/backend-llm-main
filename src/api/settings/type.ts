import { TResponse } from '@/commons/types/response';

export type TSetting = {
  id: string;
  name: string;
  description: string;
  input: string;
  type: string;
  unit: string | null;
  data_type: string;
  value: string;
};

export type TResponseListSettings = TResponse<TSetting[]>;

export type TSettingDocument = {
  data_type: string;
  description: string;
  id: string;
  name: string;
  type: string;
  unit: any | null;
  value: string | boolean;
};

export type TSettingInput = {
  id: string;
  name: string;
  description: string;
  type: string;
  unit: string | null;
  data_type: string;
  value: string;
};

export type TResponseSettingDocument = TResponse<TSettingDocument[]>;

export type TRequestEditSetting = TSettingInput;
