import { TLoginRequest, TLoginResponse } from '@/api/auth/type';
import { useEffect, useState, createContext, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { SessionToken } from '@/lib/cookies';
import { SessionUser } from '@/lib/local-storage';
import { useLogin } from '@/hooks/auth/use-login';

type Session = {
  signin: (payload: TLoginRequest) => void;
  signout: () => void;
  updateSession: (data: TLoginResponse['data']['user']) => void;
  session?: {
    // TODO format response login token
    // refresh_token: string;
    access_token: string;
    // user?: TLoginResponse['data']['user'];
  };
  status?: 'authenticated' | 'authenticating' | 'unauthenticated';
  errorMessage: string | null;
};

const SessionContext = createContext<Session>({
  signin: () => {},
  signout: () => {},
  updateSession: () => {},
  session: undefined,
  status: undefined,
  errorMessage: null
});

const SessionProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const navigate = useNavigate();
  const [sessionData, setSessionData] = useState<Session['session']>();
  const [status, setStatus] = useState<Session['status']>();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loginMutation = useLogin();

  useEffect(() => {
    const session = SessionToken.get();
    // const user = SessionUser.get();
    if (session) {
      // setSessionData({ ...session, ...user });
      setStatus('authenticated');
    } else {
      setStatus('unauthenticated');
    }
  }, []);

  const updateSession = (data: TLoginResponse['data']['user']) => {
    if (!sessionData) return;

    const updatedUser = {
      // ...sessionData.user,
      ...data
    };

    const updatedSession = {
      ...sessionData,
      user: updatedUser
    };

    setSessionData(updatedSession);
    SessionUser.set({ user: updatedUser });
  };

  const signin = async (payload: TLoginRequest) => {
    setStatus('authenticating');

    try {
      const res = await loginMutation.mutateAsync(payload);
      // const authHeader = res.authorization;
      const authHeader = res.data.token;
      const token = authHeader.replace('Basic ', '');
      setSessionData({
        access_token: token
      });
      SessionToken.set({ access_token: token });
      setStatus('authenticated');
      setErrorMessage(null);

      return res;
    } catch (error) {
      setStatus('unauthenticated');
      throw error;
    }
  };

  const signout = () => {
    setStatus('unauthenticated');
    setSessionData(undefined);
    SessionUser.remove();
    SessionToken.remove();
    navigate('/auth/login');
  };

  return (
    <SessionContext.Provider
      value={{
        session: sessionData,
        status,
        signin,
        signout,
        updateSession,
        errorMessage
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

// eslint-disable-next-line react-refresh/only-export-components
export const useSession = () => {
  return useContext(SessionContext);
};

export default SessionProvider;
