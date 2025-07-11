import Cookies from 'js-cookie';

type TCookies = {
  access_token: string;
  username: string;
};

export const SessionToken = {
  set: (values: TCookies) => {
    Cookies.set('token', values.access_token);
    Cookies.set('username', values.username);
  },
  get: (): string | undefined => {
    const token = Cookies.get('token');

    if (!token) return undefined;
    return token;
  },
  remove: () => Cookies.remove('token')
};
