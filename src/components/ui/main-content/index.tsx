import { Outlet } from 'react-router-dom';

const MainContent = () => {
  return (
    <main className="flex h-full flex-1 flex-col overflow-y-auto p-6">
      <header className="mb-10 flex items-center justify-between">
        <h3 className="text-1xl mb-1 font-bold">VITA</h3>
      </header>
      <Outlet />
    </main>
  );
};

export default MainContent;
