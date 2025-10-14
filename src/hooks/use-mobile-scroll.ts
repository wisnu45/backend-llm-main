import { useState, useEffect, useCallback, useRef } from 'react';

export interface UseMobileScrollReturn {
  isMobile: boolean;
  isScrolling: boolean;
  isAtTop: boolean;
  shouldHideOnScroll: boolean;
  scrollY: number;
}

export const useMobileScroll = (
  threshold: number = 50,
  containerRef?: React.RefObject<HTMLElement>
): UseMobileScrollReturn => {
  const [state, setState] = useState({
    isMobile: false,
    isScrolling: false,
    isAtTop: true,
    scrollY: 0,
    isHydrated: false
  });

  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastScrollY = useRef(0);

  // Mobile detection
  const checkMobile = useCallback(() => {
    if (typeof window !== 'undefined') {
      const isMobile = window.innerWidth < 768;
      setState((prev) => ({
        ...prev,
        isMobile,
        isHydrated: true
      }));
    }
  }, []);

  // Scroll state update
  const updateScrollState = useCallback(
    (currentScrollY: number) => {
      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      setState((prev) => {
        const isAtTop = currentScrollY < threshold;
        lastScrollY.current = currentScrollY;

        return {
          ...prev,
          scrollY: currentScrollY,
          isAtTop,
          isScrolling: true
        };
      });

      // Set timeout to detect when scrolling stops (2 second delay)
      scrollTimeoutRef.current = setTimeout(() => {
        setState((prev) => ({
          ...prev,
          isScrolling: false
        }));
      }, 2000);
    },
    [threshold]
  );

  // Find scrollable element
  const getScrollableElement = useCallback(() => {
    if (!containerRef?.current) return null;

    const container = containerRef.current;

    // First, look for Radix UI viewport (most likely case)
    const viewport = container.querySelector(
      '[data-radix-scroll-area-viewport]'
    );
    if (viewport) {
      const viewportEl = viewport as HTMLElement;
      return viewportEl;
    }

    // Check if the container itself is scrollable
    if (container.scrollHeight > container.clientHeight) {
      return container;
    }

    // Look for any scrollable child with proper overflow settings
    const allElements = container.querySelectorAll('*');
    for (const element of allElements) {
      const el = element as HTMLElement;
      const style = getComputedStyle(el);
      const hasScrollableOverflow =
        style.overflow === 'auto' ||
        style.overflow === 'scroll' ||
        style.overflowY === 'auto' ||
        style.overflowY === 'scroll';

      if (el.scrollHeight > el.clientHeight && hasScrollableOverflow) {
        return el;
      }
    }

    return container; // Fallback
  }, [containerRef]);

  useEffect(() => {
    // Initial mobile check
    checkMobile();

    // Setup resize listener for mobile detection
    let resizeListener: (() => void) | null = null;
    if (typeof window !== 'undefined') {
      resizeListener = () => requestAnimationFrame(checkMobile);
      window.addEventListener('resize', resizeListener, { passive: true });
    }

    return () => {
      if (resizeListener && typeof window !== 'undefined') {
        window.removeEventListener('resize', resizeListener);
      }
    };
  }, [checkMobile]);

  useEffect(() => {
    let scrollElement: HTMLElement | null = null;
    let ticking = false;

    const debouncedHandleScroll = () => {
      if (!ticking) {
        requestAnimationFrame(() => {
          if (scrollElement) {
            updateScrollState(scrollElement.scrollTop);
          } else if (typeof window !== 'undefined') {
            updateScrollState(window.scrollY);
          }
          ticking = false;
        });
        ticking = true;
      }
    };

    // Setup scroll listening with retry mechanism
    const setupScrollListener = (retryCount = 0, maxRetries = 5) => {
      scrollElement = getScrollableElement();

      if (scrollElement) {
        scrollElement.addEventListener('scroll', debouncedHandleScroll, {
          passive: true
        });
        debouncedHandleScroll(); // Initialize
      } else if (retryCount < maxRetries) {
        // Retry after a short delay
        setTimeout(() => setupScrollListener(retryCount + 1, maxRetries), 200);
      } else if (typeof window !== 'undefined') {
        // Fallback to window scroll
        window.addEventListener('scroll', debouncedHandleScroll, {
          passive: true
        });
        debouncedHandleScroll(); // Initialize
      }
    };

    // Initial setup
    setupScrollListener();

    // Re-setup if container changes
    let resizeObserver: ResizeObserver | null = null;
    if (containerRef?.current && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(() => {
        if (scrollElement) {
          scrollElement.removeEventListener('scroll', debouncedHandleScroll);
        } else if (typeof window !== 'undefined') {
          window.removeEventListener('scroll', debouncedHandleScroll);
        }
        setTimeout(setupScrollListener, 100); // Small delay for DOM updates
      });
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      if (scrollElement) {
        scrollElement.removeEventListener('scroll', debouncedHandleScroll);
      } else if (typeof window !== 'undefined') {
        window.removeEventListener('scroll', debouncedHandleScroll);
      }

      if (resizeObserver) {
        resizeObserver.disconnect();
      }

      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [containerRef, getScrollableElement, updateScrollState]);

  return {
    isMobile: state.isHydrated ? state.isMobile : false,
    isScrolling: state.isScrolling,
    isAtTop: state.isAtTop,
    shouldHideOnScroll: state.isHydrated && state.isScrolling && !state.isAtTop,
    scrollY: state.scrollY
  };
};
