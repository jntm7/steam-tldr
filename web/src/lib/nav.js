import { CircleHelp, Gamepad2, House, TriangleAlert } from "lucide-react";

// Site pages as (address, label, icon), for the nav
export const PAGES = [["/", "Home", House], ["/games/", "Games", Gamepad2], ["/outliers/", "Outliers", TriangleAlert], ["/faq/", "FAQ", CircleHelp]];

// A page address with a trailing slash
export const pagePath = (url) => url.pathname.replace(/\/?$/, "/");

// Whether a link is the page being shown; game pages count as Games
export const isCurrent = (here, href) => here === href || (href === "/games/" && here.startsWith("/game/"));
