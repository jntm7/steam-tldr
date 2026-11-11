import { useEffect, useRef, useState } from "react";

// For charts: `go` turns true once the section holding them has scrolled in (PageMotion adds `bars-go` to it), or at once when scroll
// reveals are off; `animate` is false for visitors who prefer reduced motion. Draw the chart only when `go`, so its animation plays in view
export function useSectionReveal() {
  const ref = useRef(null);
  const [go, setGo] = useState(false);
  const [animate, setAnimate] = useState(true);

  useEffect(() => {
    setAnimate(!matchMedia("(prefers-reduced-motion: reduce)").matches);
    const panel = ref.current?.closest(".panel");
    if (!panel || !document.documentElement.classList.contains("reveal-ready") || panel.classList.contains("bars-go")) {
      setGo(true);
      return undefined;
    }
    const watcher = new MutationObserver(() => {
      if (panel.classList.contains("bars-go")) { setGo(true); watcher.disconnect(); }
    });
    watcher.observe(panel, { attributes: true, attributeFilter: ["class"] });
    return () => watcher.disconnect();
  }, []);

  return { ref, go, animate };
}
