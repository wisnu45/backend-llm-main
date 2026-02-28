import { useQuery } from '@tanstack/react-query';
import { getMenuSettings } from '@/api/settings/api';
import Cookies from 'js-cookie';

import { TResponseListSettings } from '@/api/settings/type';

export const useGetMenuBar = () => {
  return useQuery<TResponseListSettings>({
    queryKey: ['get-menu-bar'],
    queryFn: async () => getMenuSettings(Cookies.get('roles_id') || '')
  });
};
