import { useState, useEffect } from 'react';

const MOBILE_BREAKPOINT = 768;

export const useMobile = () => {
  const [isMobile, setIsMobile] = useState<boolean>(false);
  const [isHydrated, setIsHydrated] = useState<boolean>(false);

  useEffect(() => {
    // Mark as hydrated once we're in the client
    setIsHydrated(true);

    const checkMobile = () => {
      // Only check if window is available (client-side)
      if (typeof window !== 'undefined') {
        setIsMobile(window.innerWidth < MOBILE_BREAKPOINT);
      }
    };

    // Initial check with a small delay to ensure proper initialization
    const timeoutId = setTimeout(checkMobile, 10);

    // Set up resize listener
    let resizeListener: (() => void) | null = null;
    if (typeof window !== 'undefined') {
      resizeListener = () => {
        // Use requestAnimationFrame to avoid excessive calls during resize
        requestAnimationFrame(checkMobile);
      };
      window.addEventListener('resize', resizeListener, { passive: true });
    }

    return () => {
      clearTimeout(timeoutId);
      if (resizeListener && typeof window !== 'undefined') {
        window.removeEventListener('resize', resizeListener);
      }
    };
  }, []);

  // Return false during SSR/initial render to avoid hydration mismatches
  return isHydrated ? isMobile : false;
};
