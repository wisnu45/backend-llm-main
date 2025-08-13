import { Outlet } from 'react-router-dom';

const MainContent = () => {
  return (
    <main className="flex h-full flex-1 flex-col overflow-y-auto p-4">
      <header className="mb-5 flex items-center justify-between">
        <h3 className="mb-1 text-2xl font-bold">VITA</h3>
      </header>
      <Outlet />
    </main>
  );
};

export default MainContent;
