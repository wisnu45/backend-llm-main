import {
  TLoginRequest,
  TLoginResponse,
  TLoginSSORequest
} from '@/api/auth/type';
import { TErrorResponse } from '@/commons/types/response';
import { useLoginSSO } from '@/hooks/auth/login-sso';
import { useLogin } from '@/hooks/auth/use-login';
import { SessionToken } from '@/lib/cookies';
import { SessionUser } from '@/lib/local-storage';
import { createContext, useContext, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

type Session = {
  signin: (payload: TLoginRequest) => void;
  signinSSO: (payload: TLoginSSORequest) => void;
  signout: () => void;
  updateSession: (data: TLoginResponse['data']['userdata']) => void;
  session?: {
    // refresh_token: string;
    access_token: string;
  };
  status?: 'authenticated' | 'authenticating' | 'unauthenticated';
  errorMessage: string | null;
};

const SessionContext = createContext<Session>({
  signin: () => {},
  signinSSO: () => {},
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
  const loginSSO = useLoginSSO();

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

  const updateSession = (data: TLoginResponse['data']['userdata']) => {
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

      setSessionData({
        access_token: res.data.access_token
        // refresh_token: res.data.refresh_token
      });
      setStatus('authenticated');
      setErrorMessage(null);

      return res;
    } catch (error) {
      setStatus('unauthenticated');
      throw error;
    }
  };

  const signinSSO = async (payload: TLoginSSORequest) => {
    setStatus('authenticating');

    try {
      const res = await loginSSO.mutateAsync(payload);
      const { access_token, userdata } = res.data;
      setSessionData({ access_token });
      SessionToken.set({
        access_token,
        // refresh_token,
        username: userdata.username,
        name: userdata.name,
        role: userdata.role.name,
        roles_id: userdata.role.id,
        error_connection:
          'Sambungan terputus. Coba periksa jaringan Anda dan muat ulang halaman'
      });
      setStatus('authenticated');
      setErrorMessage(null);
      navigate('/chat', { replace: true });
      return res;
    } catch (error) {
      const err = error as TErrorResponse;
      const message = err.response?.data.message || error;

      setStatus('unauthenticated');
      navigate(`/auth/signin?error=${message}`, { replace: true });
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
        signinSSO,
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
