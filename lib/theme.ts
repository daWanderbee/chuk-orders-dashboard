// CHUK brand palette (ported from chuk_orders_dashboard.py DARK/LIGHT dicts).
//   amber #F3B343 · coral #F46C62 · maroon #942A45 · teal #33A8C3
//   green #95CC2E · kraft #CDB096 · cream #FFF2E0
export type Palette = {
  app_bg: string; sidebar_bg: string; logo_bg: string; logo_pad: string;
  text: string; muted: string; val: string; lbl: string;
  card_bg: string; card_border: string; card_hover: string;
  hero_bg: string; hero_title: string; hero_text: string;
  tab_bg: string; tab_text: string;
  df_border: string; table_bg: string; table_text: string;
  btn_bg: string; btn_border: string; btn_text: string;
  chart_font: string; chart_title: string; grid: string; axis: string;
};

export const DARK: Palette = {
  app_bg: "#221318", sidebar_bg: "#1B0F13", logo_bg: "#FFF2E0", logo_pad: "8px 14px",
  text: "#FFF2E0", muted: "#CDB096", val: "#FFF8EF", lbl: "#B79877",
  card_bg: "#2E1B22", card_border: "#4A2E36", card_hover: "#F3B343",
  hero_bg: "#F3B343", hero_title: "#3A1620", hero_text: "#5A2A18",
  tab_bg: "#2E1B22", tab_text: "#CDB096",
  df_border: "#4A2E36", table_bg: "#2A1A20", table_text: "#FFF2E0",
  btn_bg: "#F3B343", btn_border: "#F3B343", btn_text: "#3A1620",
  chart_font: "#E8D6BE", chart_title: "#FFF2E0", grid: "#3A2630", axis: "#5A3E48",
};

export const LIGHT: Palette = {
  app_bg: "#F5ECD9", sidebar_bg: "#EFE4CC", logo_bg: "transparent", logo_pad: "0",
  text: "#942A45", muted: "#8A5A45", val: "#6E1F33", lbl: "#A07A5C",
  card_bg: "#FFFFFF", card_border: "#EADFCB", card_hover: "#F46C62",
  hero_bg: "#942A45", hero_title: "#FFF2E0", hero_text: "#F2DABB",
  tab_bg: "#F2DABB", tab_text: "#8A5A45",
  df_border: "#EADFCB", table_bg: "#FFFFFF", table_text: "#5A1A2C",
  btn_bg: "#F3B343", btn_border: "#F3B343", btn_text: "#3A1620",
  chart_font: "#7A3A4A", chart_title: "#942A45", grid: "#EADFCB", axis: "#CBB89E",
};

export type ThemeMode = "light" | "dark";
export const palette = (m: ThemeMode): Palette => (m === "light" ? LIGHT : DARK);

// CHUK brand status colors
export const STATUS_COLOR: Record<string, string> = {
  pending: "#F3B343",     // amber
  processing: "#33A8C3",  // teal
  "on-hold": "#CDB096",   // kraft
  completed: "#6FA52A",   // green
  cancelled: "#F46C62",   // coral
  refunded: "#E08A3C",    // burnt amber
  failed: "#942A45",      // maroon
};

export const GROUP_COLOR: Record<string, string> = {
  Processing: "#F3B343",
  Completed: "#6FA52A",
  "Failed/Cancelled": "#F46C62",
  Other: "#CDB096",
};
