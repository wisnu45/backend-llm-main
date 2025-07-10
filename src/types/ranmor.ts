export interface ListRanmorInput {
  page: number;
  page_size: number;
  search?: string;
  filter?: {
    no_polisi?: string;
    no_rangka?: string;
    sync_at_date_start?: string;
    sync_at_date_end?: string;
    status?: string;
    kd_kel?: string;
  };
  orders?: [
    {
      order_by: string;
      sort_by: string;
    }
  ];
}

export type RanmorStatus = 'bpka' | 'jr' | 'bpka_jr';

export interface Ranmor {
  id: string;
  no_polisi: string;
  no_rangka: string;
  kode_upt: string;
  kd_pos: string;
  kd_kel: null;
  sync_jasa_raharja: null;
  sync_dit_lantas: null;
  status: string;
  sync_at: string;
  action: null;
  created_at: string;
  updated_at: string;
  deleted_at: string;
}
