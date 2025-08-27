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
  const lastScrollY = useRef(0);

  const updateScrollState = useCallback(
    (currentScrollY: number, scrollHeight: number, clientHeight: number) => {
      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      setScrollState((prev) => {
        const isScrollingDown =
          currentScrollY > lastScrollY.current && currentScrollY > threshold;
        const isAtTop = currentScrollY < threshold;
        const isAtBottom = currentScrollY + clientHeight >= scrollHeight - 10;

        lastScrollY.current = currentScrollY;

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
      }, 150);
    },
    [threshold]
  );

  const getScrollableElement = useCallback(() => {
    if (containerRef?.current) {
      // Try to find the actual scrollable element within the container
      const container = containerRef.current;

      // Check if the container itself is scrollable
      if (container.scrollHeight > container.clientHeight) {
        return container;
      }

      // Look for a scrollable child (like Radix UI viewport)
      const viewport = container.querySelector(
        '[data-radix-scroll-area-viewport]'
      );
      if (viewport && viewport.scrollHeight > viewport.clientHeight) {
        return viewport as HTMLElement;
      }

      // Look for any scrollable child
      const children = container.querySelectorAll('*');
      for (let i = 0; i < children.length; i++) {
        const child = children[i] as HTMLElement;
        if (child.scrollHeight > child.clientHeight) {
          return child;
        }
      }

      // Fallback to container
      return container;
    }

    return null;
  }, [containerRef]);

  useEffect(() => {
    let scrollElement: HTMLElement | null = null;
    let ticking = false;

    const debouncedHandleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          if (scrollElement) {
            updateScrollState(
              scrollElement.scrollTop,
              scrollElement.scrollHeight,
              scrollElement.clientHeight
            );
          } else if (typeof window !== 'undefined') {
            // Fallback to window scroll
            updateScrollState(
              window.scrollY,
              document.documentElement.scrollHeight,
              window.innerHeight
            );
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    // Setup scroll listening
    const setupScrollListener = () => {
      scrollElement = getScrollableElement();

      if (scrollElement) {
        scrollElement.addEventListener('scroll', debouncedHandleScroll, {
          passive: true
        });
        // Initialize scroll state
        debouncedHandleScroll();
      } else if (typeof window !== 'undefined') {
        // Fallback to window scroll
        window.addEventListener('scroll', debouncedHandleScroll, {
          passive: true
        });
        // Initialize scroll state
        debouncedHandleScroll();
      }
    };

    // Setup immediately if possible
    setupScrollListener();

    // Also observe container changes using ResizeObserver
    let resizeObserver: ResizeObserver | null = null;
    if (containerRef?.current && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        // Re-setup when container size changes
        if (scrollElement) {
          scrollElement.removeEventListener('scroll', debouncedHandleScroll);
        }
        setupScrollListener();
      });
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      // Clean up scroll listener
      if (scrollElement) {
        scrollElement.removeEventListener('scroll', debouncedHandleScroll);
      } else if (typeof window !== 'undefined') {
        window.removeEventListener('scroll', debouncedHandleScroll);
      }

      // Clean up observers
      if (resizeObserver) {
        resizeObserver.disconnect();
      }

      // Clean up timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [containerRef, getScrollableElement, updateScrollState]);

  return scrollState;
};
