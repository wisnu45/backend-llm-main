export type TLoginRequest = {
  username: string;
  password: string;
};

export type TLoginResponse = {
  authorization: string;
  message: string;
  data: {
    access_token: string;
    // refresh_token: string;
    token_type: string;
    expires_in: number;
    userdata: {
      role: {
        id: string;
        name: string;
      };
      roles_id: string;
      username: string;
      name: string;
      is_portal: boolean;
    };
  };
};

export type TLogoutRequest = {
  refresh_token: string;
};

export type TLoginSSORequest = {
  token: string;
};
