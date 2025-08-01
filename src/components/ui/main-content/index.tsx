import { Outlet } from 'react-router-dom';

const MainContent = () => {
  return (
    <main className="flex h-full flex-1 flex-col overflow-y-auto p-6">
      <header className="mb-10 flex items-center justify-between">
        <img src="/icons/logo_vita.png" className="h-auto max-w-24" />
      </header>
      <Outlet />
    </main>
  );
};

export default MainContent;
