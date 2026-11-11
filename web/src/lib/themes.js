import {
  BookOpen, Bug, Gamepad2, Gauge, KeyRound, Layers, Music, Palette, Puzzle, Server, Shapes, ShieldX, Skull, Swords, Tag, Users, Wrench,
} from "lucide-react";

// Icon for each theme
const THEME_ICONS = {
  "performance": Gauge,
  "bugs & crashes": Bug,
  "price & monetization": Tag,
  "servers & matchmaking": Server,
  "cheaters": ShieldX,
  "community": Users,
  "co-op & multiplayer": Gamepad2,
  "story & characters": BookOpen,
  "gameplay & combat": Swords,
  "graphics & art": Palette,
  "music & sound": Music,
  "content & grind": Layers,
  "difficulty": Skull,
  "developers & updates": Wrench,
  "mods & customization": Puzzle,
  "accounts & launchers": KeyRound,
};

// A theme's icon, with a fallback for themes added later
export const themeIcon = (theme) => THEME_ICONS[theme] ?? Shapes;

// Text with its first letter capitalized
export const capitalize = (text) => text[0].toUpperCase() + text.slice(1);
