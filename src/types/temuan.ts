export type TemuanSource = 'jasa_raharja' | 'dit_lantas';

export interface CountTemuanInput {
  type: string;
}
export interface ListTemuanInput {
  page: number;
  page_size: number;
  search?: string;
  filter?: {
    no_polisi?: string;
    no_rangka?: string;
    sync_at_date_start?: string;
    sync_at_date_end?: string;
    source?: string;
  };
  orders?: [
    {
      order_by: string;
      sort_by: string;
    }
  ];
}
