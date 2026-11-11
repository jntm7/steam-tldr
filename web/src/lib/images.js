import { getImage } from "astro:assets";

// Build-time only, like data.js: resized WebP copies of Steam's art, so pages don't ship full-size images
async function resized(src, width, height) {
  if (!src) return null;
  const image = await getImage({ src, width, height, format: "webp", quality: 75 });
  return image.src;
}

// A game plus small versions of its portrait cover (shown ~110px wide, so 2x) and banner
export async function withImages(game) {
  const [cover, banner] = await Promise.all([resized(game.library_image, 240, 360), resized(game.header_image, 240, 112)]);
  return { ...game, cover, banner };
}
