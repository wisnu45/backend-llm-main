import { Outlet } from 'react-router-dom';

const MainContent = () => {
  return (
    <main className="flex h-full flex-1 flex-col overflow-y-auto p-6">
      <header className="mb-10 flex items-center justify-between">
        <img src="/icons/logo.png" className="h-6 h-auto max-w-44" />
      </header>
      <Outlet />
    </main>
  );
};

export default MainContent;
