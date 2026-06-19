import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CHUK Orders",
  icons: {
    icon: "https://chuk.in/wp-content/uploads/2022/08/cropped-chuk-favicon-new-192x192.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
