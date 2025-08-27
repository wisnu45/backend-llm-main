import Sidebar from '@/components/ui/sidebar';
import { PropsWithChildren, useState } from 'react';
import Logout from '@/components/ui/Logout';

const MainLayout = ({ children }: PropsWithChildren) => {
  const [showModal, setShowModal] = useState(false);
  return (
    <div className="flex h-screen bg-[#EEEEEE] font-sans text-[#1B212D] ">
      <Sidebar setShowModal={setShowModal} />
      <main className="flex h-full flex-1 flex-col overflow-y-auto p-4">
        <header className="mb-5 flex items-center justify-between">
          <h3 className="mb-1 text-2xl">Vita</h3>
        </header>
        {children}
      </main>
      <Logout showModal={showModal} setShowModal={setShowModal} />
    </div>
  );
};
export default MainLayout;
