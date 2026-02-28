import { Suspense } from 'react';
import { HelmetProvider } from 'react-helmet-async';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

import SessionProvider from './components/providers/session';
import ThemeProvider from './components/providers/theme-provider';
import { Toaster } from './components/ui/toaster';
import AppRouter from './routes';

const queryClient = new QueryClient();

export default function App() {
  return (
    <Suspense>
      <HelmetProvider>
        <BrowserRouter>
          {/* <ErrorBoundary FallbackComponent={ErrorFallback}> */}
          <QueryClientProvider client={queryClient}>
            <ReactQueryDevtools />
            <ThemeProvider defaultTheme="light" storageKey="vite-ui-theme">
              <SessionProvider>
                <AppRouter />
              </SessionProvider>
            </ThemeProvider>
            <Toaster />
          </QueryClientProvider>
          {/* </ErrorBoundary> */}
        </BrowserRouter>
      </HelmetProvider>
    </Suspense>
  );
}
