export type TLoginRequest = {
  username: string;
  password: string;
};

export type TLoginResponse = {
  authorization: string;
  message: string;
  data: {
    token: string;
    username: string;
    userdata: {
      role: string;
      username: string;
    };
    user: {
      id: string;
      fullname: string;
      email?: string;
      username?: string;
      login_type?: 'username' | 'email';
      created_at: string;
      updated_at: string;
      role: 'admin' | 'marketing';
      avatar_path: string | null;
      avatar_url: string | null;
    };
  };
};

export type TLogoutRequest = {
  session_id: string;
};
