import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import sitemap from "@astrojs/sitemap";
import devRefresh from "./dev-refresh.mjs";

export default defineConfig({
  site: "https://steamtldr.jntam.ca",
  image: { domains: ["shared.akamai.steamstatic.com"] },
  integrations: [react(), sitemap(), devRefresh()],
});
