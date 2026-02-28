import { Icons } from '@/components/ui/icons';

export interface NavItem {
  title: string;
  href: string;
  disabled?: boolean;
  external?: boolean;
  icon?: keyof typeof Icons;
  label?: string;
  description?: string;
}

export interface NavItemWithChildren extends NavItem {
  items: NavItemWithChildren[];
}

export interface NavItemWithOptionalChildren extends NavItem {
  items?: NavItemWithChildren[];
}

export interface FooterItem {
  title: string;
  items: {
    title: string;
    href: string;
    external?: boolean;
  }[];
}

export type MainNavItem = NavItemWithOptionalChildren;

export type SidebarNavItem = NavItemWithChildren;

export interface PaginationInput {
  pageIndex: number;
  pageSize: number;
  total: number;
  totalPage: number;
  onPageChange: (newPage: number) => void;
  onPageSizeChange: (newPageSize: number) => void;
}

export type OptionType = {
  label: string;
  value: string;
};

export type BreadcrumbItem = {
  id: string;
  name: string;
};

export type ActionType =
  | 'create'
  | 'detail'
  | 'edit'
  | 'import'
  | 'delete'
  | undefined;
