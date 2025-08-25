import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseScrollReturn {
  isScrollingDown: boolean;
  scrollY: number;
  isAtTop: boolean;
  isAtBottom: boolean;
  isScrolling: boolean;
}

export const useScroll = (
  threshold: number = 50,
  containerRef?: React.RefObject<HTMLElement>
): UseScrollReturn => {
  const [scrollState, setScrollState] = useState({
    isScrollingDown: false,
    scrollY: 0,
    isAtTop: true,
    isAtBottom: false,
    isScrolling: false
  });

  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const handleScroll = useCallback(() => {
    let currentScrollY: number;
    let scrollHeight: number;
    let clientHeight: number;

    if (containerRef?.current) {
      // Use container scroll values
      const container = containerRef.current;
      currentScrollY = container.scrollTop;
      scrollHeight = container.scrollHeight;
      clientHeight = container.clientHeight;
    } else {
      // Fall back to window scroll values
      currentScrollY = window.scrollY;
      scrollHeight = document.documentElement.scrollHeight;
      clientHeight = window.innerHeight;
    }

    // Clear existing timeout
    if (scrollTimeoutRef.current) {
      clearTimeout(scrollTimeoutRef.current);
    }

    setScrollState((prev) => {
      const isScrollingDown =
        currentScrollY > prev.scrollY && currentScrollY > threshold;
      const isAtTop = currentScrollY < threshold;
      const isAtBottom = currentScrollY + clientHeight >= scrollHeight - 10;

      return {
        isScrollingDown,
        scrollY: currentScrollY,
        isAtTop,
        isAtBottom,
        isScrolling: true
      };
    });

    // Set timeout to detect when scrolling stops
    scrollTimeoutRef.current = setTimeout(() => {
      setScrollState((prev) => ({
        ...prev,
        isScrolling: false
      }));
    }, 150); // 150ms delay after scroll stops
  }, [threshold, containerRef]);

  useEffect(() => {
    let ticking = false;

    const debouncedHandleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          handleScroll();
          ticking = false;
        });
        ticking = true;
      }
    };

    if (containerRef?.current) {
      containerRef.current.addEventListener('scroll', debouncedHandleScroll, {
        passive: true
      });
    } else {
      window.addEventListener('scroll', debouncedHandleScroll, {
        passive: true
      });
    }

    handleScroll(); // Initialize state

    return () => {
      if (containerRef?.current) {
        containerRef.current.removeEventListener(
          'scroll',
          debouncedHandleScroll
        );
      } else {
        window.removeEventListener('scroll', debouncedHandleScroll);
      }
      // Clean up timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [handleScroll, containerRef]);

  return scrollState;
};
