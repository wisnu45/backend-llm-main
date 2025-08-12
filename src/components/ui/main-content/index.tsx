import { Outlet } from 'react-router-dom';

const MainContent = () => {
  return (
    <main className="flex h-full flex-1 flex-col overflow-y-auto p-6">
      <header className="mb-10 flex items-center justify-between">
        <h3 className="mb-1 text-2xl font-bold md:text-3xl lg:text-4xl">
          VITA
        </h3>
      </header>
      <Outlet />
    </main>
  );
};

export default MainContent;
