import axios, { AxiosError } from 'axios';
import Cookies from 'js-cookie';
import { SessionToken } from './cookies'; // penyimpanan access_token

const api = axios.create({
  baseURL: import.meta.env.VITE_API_ENDPOINT,
  headers: {
    'Content-Type': 'application/json'
  }
});

api.interceptors.request.use((config) => {
  const accessToken = SessionToken.get();
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

async function refreshAccessToken() {
  const refreshToken = Cookies.get('refresh_token'); // simpan di cookie

  if (!refreshToken) return null;

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_ENDPOINT}auth/refresh`,
      { refresh_token: refreshToken },
      {
        headers: { 'Content-Type': 'application/json' }
      }
    );

    const newAccessToken = response.data.data.access_token;
    const newRefreshToken = response.data.data.refresh_token;
    SessionToken.set(newAccessToken);
    Cookies.set('refresh_token', newRefreshToken);
    return newAccessToken;
  } catch (err) {
    console.error('Refresh token failed:', err);
    return null;
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as typeof error.config & {
      _retry?: boolean;
    };

    // Jika token expired
    if (error.response?.status === 401 && !originalRequest?._retry) {
      originalRequest._retry = true;

      const newToken = await refreshAccessToken();

      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api(originalRequest); // ulangi request
      } else {
        SessionToken.remove();
        Cookies.remove('refresh_token');
        window.location.href =
          '/auth/signin?error=Session expired. Please log in again.';
      }
    }

    return Promise.reject(error);
  }
);

export default api;
