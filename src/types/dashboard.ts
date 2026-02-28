export type countBpkaTypes = 'jasa_raharja' | 'ditlantas' | undefined;

export type CountBpkaInput = {
  is_jasa_raharja?: boolean;
  is_ditlantas?: boolean;
};

export type ListKecamatanInput = {
  kode_upt: string;
};

export type ListKelurahanInput = {
  kd_pos: string;
};

export type RegionData = {
  id: string;
  name: string;
  total: number;
  sync: number;
  jr: number;
  dl: number;
  jr_dl: number;
};

export interface BaseCardProps {
  title: string;
  value: number;
  unit?: string;
}

export interface RegionCardProps {
  data: RegionData;
  routeOnClick: string;
}

export interface WilayahSectionProps {
  title: string;
  data: RegionData[];
}
