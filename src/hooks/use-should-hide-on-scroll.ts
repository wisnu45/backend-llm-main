import { useState, useEffect, useCallback, useRef } from 'react';

export const useShouldHideOnScroll = (
  threshold: number = 50,
  containerRef?: React.RefObject<HTMLElement>
): boolean => {
  const [shouldHide, setShouldHide] = useState(false);

  const lastScrollY = useRef(0);

  useEffect(() => {
    let ticking = false;
    let scrollElement: HTMLElement | null = null;

    const handleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          const currentScrollY = scrollElement
            ? scrollElement.scrollTop
            : window.scrollY || window.pageYOffset;

          const scrollHeight = scrollElement
            ? scrollElement.scrollHeight
            : document.body.scrollHeight;
          const clientHeight = scrollElement
            ? scrollElement.clientHeight
            : window.innerHeight;

          // Check if at the very bottom
          const isAtBottom = currentScrollY + clientHeight >= scrollHeight - 10; // -10 for a small buffer

          const isScrollingDown = currentScrollY > lastScrollY.current;
          const isPastThreshold = currentScrollY > threshold;
          lastScrollY.current = currentScrollY;

          if (isAtBottom) {
            setShouldHide(false);
          } else {
            setShouldHide(isScrollingDown && isPastThreshold);
          }

          ticking = false;
        });
        ticking = true;
      }
    };

    // Determine which element to listen to
    if (containerRef?.current) {
      scrollElement = containerRef.current;
      scrollElement.addEventListener('scroll', handleScroll, { passive: true });
    } else {
      // Fallback to window scroll
      window.addEventListener('scroll', handleScroll, { passive: true });
    }

    handleScroll(); // Initialize

    return () => {
      if (scrollElement) {
        scrollElement.removeEventListener('scroll', handleScroll);
      } else {
        window.removeEventListener('scroll', handleScroll);
      }
    };
  }, [threshold, containerRef]);

  return shouldHide;
};
