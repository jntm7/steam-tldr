import games from "../../../site_data/index.json";
import settings from "../../../site_data/site.json";

// Every exported game summary, read at build time only
const files = import.meta.glob("../../../site_data/[0-9]*.json", { eager: true, import: "default" });
export const summaries = Object.values(files);

export { games, settings };
