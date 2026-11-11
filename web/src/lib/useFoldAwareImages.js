import { useEffect } from "react";

// Rows and cards straddle the fold, and which images should load eagerly depends on the viewport, so set the
// loading attribute at runtime: above the fold eager, below lazy. Runs after every render, so paging, filtering
// and re-sorts keep it correct
export function useFoldAwareImages(ref) {
  useEffect(() => {
    const root = ref.current;
    if (!root) return undefined;
    const apply = () => {
      const fold = window.innerHeight;
      for (const img of root.querySelectorAll("img")) {
        let y = 0;
        for (let el = img; el; el = el.offsetParent) y += el.offsetTop;
        img.loading = y <= fold ? "eager" : "lazy";
      }
    };
    apply();
    window.addEventListener("resize", apply);
    return () => window.removeEventListener("resize", apply);
  });
}
