import NotFound from '@/pages/old/not-found';
import { lazy } from 'react';
import { Navigate, Outlet, useRoutes } from 'react-router-dom';
import PublicRoute from './public-route';
import ProtectedRoute from './protected-route';

import GeneralFile from '@/pages/old/files/general';
import DivisionFile from '@/pages/old/files/division';
import ChatPage from '@/pages/new/chat/page';
import FilesPage from '@/pages/new/files/page';
import DetailPage from '@/pages/new/chat/detail/page';
import ChatHistory from '@/pages/history/ChatHistory';

const SignInPage = lazy(() => import('@/pages/auth/signin'));

const MainLayout = lazy(() => import('@/components/layout/main-layout'));
const NewMainLayout = lazy(() => import('@/components/layout/new-main-layout'));

const OldChatPage = lazy(() => import('@/pages/old/chat'));
const EnhancePage = lazy(() => import('@/pages/old/enhance'));

const ThankyouPage = lazy(() => import('@/pages/old/thankyou'));

// ----------------------------------------------------------------------

export default function AppRouter() {
  const dashboardRoutes = [
    {
      path: '/old',
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
          element: <Navigate to="/old/chat" replace />
        },
        {
          path: '/old/chat',
          element: <OldChatPage />
        },
        {
          path: '/old/files/general',
          element: <GeneralFile />
        },
        {
          path: '/old/files/division',
          element: <DivisionFile />
        },
        {
          path: '/old/enhance',
          element: <EnhancePage />
        }
      ]
    },
    {
      path: '/',
      element: (
        <ProtectedRoute>
          <NewMainLayout />
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
        }
      ]
    }
  ];

  const publicRoutes = [
    {
      path: '/auth/signin',
      element: (
        <PublicRoute>
          <SignInPage />
        </PublicRoute>
      ),
      index: true
    },
    {
      path: '/thankyou',
      element: <ThankyouPage />,
      index: true
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

  const routes = useRoutes([...dashboardRoutes, ...publicRoutes]);

  return routes;
}
