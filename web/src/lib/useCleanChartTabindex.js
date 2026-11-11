import { useEffect } from "react";

// Recharts puts tabindex on its decorative <svg> and on the <g> layers it portals chart parts into. Neither is
// actually interactive, but the dev toolbar's a11y audit flags any tabindex on them. Charts pass
// accessibilityLayer={false} to keep the root svg clean; this removes the remaining attributes, including on
// layers that mount later (tooltips, animation dots). Only svg and g are touched, so real controls are safe.
const strip = (node) => {
  if (node.nodeType !== 1) return;
  const targets = node.matches("svg, g") ? [node] : [];
  targets.push(...node.querySelectorAll("svg, svg g"));
  for (const el of targets) if (el.hasAttribute("tabindex")) el.removeAttribute("tabindex");
};

export function useCleanChartTabindex(ref) {
  useEffect(() => {
    const root = ref.current;
    if (!root) return undefined;
    strip(root);
    const observer = new MutationObserver((records) => {
      for (const record of records) for (const node of record.addedNodes) strip(node);
    });
    observer.observe(root, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [ref]);
}
