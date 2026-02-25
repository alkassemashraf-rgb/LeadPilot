"use client";

import { useEffect, useRef, useState } from "react";

type Animation = "fadeUp" | "fadeIn" | "fadeLeft" | "fadeRight" | "zoomIn";

interface Props {
  children: React.ReactNode;
  animation?: Animation;
  delay?: number;
  duration?: number;
  className?: string;
  threshold?: number;
  once?: boolean;
}

const getInitialTransform = (a: Animation): string => ({
  fadeUp:    "translateY(32px)",
  fadeIn:    "translateY(0)",
  fadeLeft:  "translateX(-32px)",
  fadeRight: "translateX(32px)",
  zoomIn:    "scale(0.92)",
}[a]);

export default function AnimateOnScroll({
  children,
  animation = "fadeUp",
  delay = 0,
  duration = 700,
  className = "",
  threshold = 0.1,
  once = true,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          if (once) observer.disconnect();
        } else if (!once) {
          setVisible(false);
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold, once]);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? "none" : getInitialTransform(animation),
        transition: `opacity ${duration}ms cubic-bezier(0.16,1,0.3,1) ${delay}ms, transform ${duration}ms cubic-bezier(0.16,1,0.3,1) ${delay}ms`,
      }}
    >
      {children}
    </div>
  );
}
