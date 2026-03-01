"use client";

import { useEffect, useRef, type RefObject } from "react";

/**
 * Scroll-reveal hook: adds a CSS class when the element enters the viewport.
 * Fires once, then disconnects the observer.
 */
export function useReveal<T extends HTMLElement>(
  className = "reveal-visible",
): RefObject<T | null> {
  const ref = useRef<T>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add(className);
          observer.unobserve(el);
        }
      },
      { threshold: 0.1 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [className]);

  return ref;
}
