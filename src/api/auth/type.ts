export type TLoginRequest = {
  username: string;
  password: string;
};

export type TLoginResponse = {
  authorization: string;
  message: string;
  data: {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
    userdata: {
      role: string;
      username: string;
      name: string;
      is_portal: boolean;
    };
  };
};

export type TLogoutRequest = {
  session_id: string;
};

export type TLoginSSORequest = {
  token: string;
};
