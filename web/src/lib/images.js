import { getImage } from "astro:assets";

// Build-time only, like data.js: resized WebP copies of Steam's art, so pages don't ship full-size images
async function resized(src, width, height, quality = 75) {
  if (!src) return null;
  const image = await getImage({ src, width, height, format: "webp", quality });
  return image.src;
}

// A game plus small versions of its portrait cover, its banner and a list-view thumbnail (shown ~110px wide, so 2x)
export async function withImages(game) {
  const [cover, banner, thumb] = await Promise.all([
    resized(game.library_image, 240, 360),
    resized(game.header_image, 240, 112),
    resized(game.header_image, 220, 103, 70),
  ]);
  return { ...game, cover, banner, thumb };
}
