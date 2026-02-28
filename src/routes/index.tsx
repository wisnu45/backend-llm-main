import { Navigate, Outlet, useRoutes } from 'react-router-dom';

import ChatPage from '@/pages/(protected)/chat/page';
import FilesPage from '@/pages/(protected)/files/page';
import DetailPage from '@/pages/(protected)/chat/detail/page';
import ChatHistory from '@/pages/(protected)/history/ChatHistory';
import UserManagementPage from '@/pages/(protected)/user-management/page';
import OAuthCallbackPage from '@/pages/auth/oauth-callback';
import LoginPage from '@/pages/auth/signin';
import NotFound from '@/pages/not-found';
import ProtectedRoute from '@/components/providers/protected-route';
import MainLayout from '@/components/providers/main-layout';
import SettingTable from '@/pages/(protected)/setting/page';

export default function AppRouter() {
  const protectedRoutes = [
    {
      path: '/',
      element: (
        <ProtectedRoute>
          <MainLayout>
            <Outlet />
          </MainLayout>
        </ProtectedRoute>
      ),
      children: [
        {
          index: true,
          element: <Navigate to="/chat" replace />
        },
        {
          path: '/chat',
          element: <ChatPage />
        },
        {
          path: '/chat/:chatId',
          element: <DetailPage />
        },
        {
          path: '/files',
          element: <FilesPage />
        },
        {
          path: '/history',
          element: <ChatHistory />
        },
        {
          path: '/setting',
          element: <SettingTable />
        },
        {
          path: '/user-management',
          element: <UserManagementPage />
        }
      ]
    }
  ];

  const publicRoutes = [
    {
      path: '/auth/signin',
      element: <LoginPage />,
      index: true
    },
    {
      path: '/SSO/Validate',
      element: <OAuthCallbackPage />
    },
    {
      path: '/404',
      element: <NotFound />
    },
    {
      path: '/',
      element: <Navigate to="/auth/signin" replace />
    },
    {
      path: '*',
      element: <Navigate to="/404" replace />
    }
  ];

  const routes = useRoutes([...protectedRoutes, ...publicRoutes]);

  return routes;
}
