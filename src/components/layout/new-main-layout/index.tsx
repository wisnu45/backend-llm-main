import MainContent from '@/components/ui/main-content';
import Sidebar from '@/components/ui/sidebar';
import { useState } from 'react';
import Logout from '@/components/ui/Logout';

const MainLayout = () => {
  const [showModal, setShowModal] = useState(false);
  return (
    <div className="flex h-screen bg-[#EEEEEE] font-sans text-[#1B212D] ">
      <Sidebar setShowModal={setShowModal} />
      <MainContent />
      <Logout showModal={showModal} setShowModal={setShowModal} />
    </div>
  );
};
export default MainLayout;
