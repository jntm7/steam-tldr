import { useEffect, useState } from "react";

// An element's width, kept up to date as it resizes, so charts can space their labels to fit
export function useWidth(ref, initial = 800) {
  const [width, setWidth] = useState(initial);
  useEffect(() => {
    if (!ref.current) return undefined;
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref]);
  return width;
}
