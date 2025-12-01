import Sidebar from '@/components/ui/sidebar';
import { PropsWithChildren, useState } from 'react';
import Logout from '@/components/ui/Logout';

const MainLayout = ({ children }: PropsWithChildren) => {
  const [showModal, setShowModal] = useState(false);
  return (
    <div className="h-screen bg-[#EEEEEE] font-sans text-[#1B212D]">
      <div className="fixed inset-y-0 left-0 z-20">
        <Sidebar setShowModal={setShowModal} />
      </div>
      <div
        className="relative flex h-full flex-col"
        style={{ marginLeft: 'var(--sidebar-width, 50px)' }}
      >
        <header
          style={{ left: 'var(--sidebar-width, 50px)' }}
          className="fixed inset-x-0 top-0 z-10 flex h-16 items-center justify-between bg-[#EEEEEE] px-4"
        >
          <h3 className="text-2xl">Vita</h3>
        </header>
        <main className="relative top-16 bg-[#EEEEEE] p-4">{children}</main>
      </div>
      <Logout showModal={showModal} setShowModal={setShowModal} />
    </div>
  );
};
export default MainLayout;
