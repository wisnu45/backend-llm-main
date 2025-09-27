import Cookies from 'js-cookie';

type TCookies = {
  access_token: string;
  // refresh_token: string;
  username: string;
  role: string;
  roles_id: string;
  is_company: string;
  name: string;
  error_connection: string;
};

export const SessionToken = {
  set: (values: TCookies) => {
    Cookies.set('token', values.access_token);
    Cookies.set('username', values.username);
    Cookies.set('name', values.name);
    Cookies.set('role', values.role);
    Cookies.set('roles_id', values.roles_id);
    Cookies.set('is_company', 'true');
    // Cookies.set('refresh_token', values.refresh_token);
    Cookies.set('error_connection', values.error_connection);
  },
  get: (): string | undefined => {
    const token = Cookies.get('token');

    if (!token) return undefined;
    return token;
  },
  remove: () => {
    Cookies.remove('token');
    Cookies.remove('username');
    Cookies.remove('name');
    Cookies.remove('role');
    Cookies.remove('roles_id');
    Cookies.remove('refresh_token');
    Cookies.remove('is_company');
    Cookies.remove('is_browse');
    Cookies.remove('is_general');
    Cookies.remove('search_internet');
    Cookies.remove('error_connection');
  }
};
