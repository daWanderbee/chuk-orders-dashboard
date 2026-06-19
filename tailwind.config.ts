import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        karbon: ["Karbon", "Montserrat", "-apple-system", "sans-serif"],
      },
      colors: {
        chuk: {
          amber: "#F3B343",
          coral: "#F46C62",
          maroon: "#942A45",
          teal: "#33A8C3",
          green: "#95CC2E",
          kraft: "#CDB096",
          cream: "#FFF2E0",
        },
      },
    },
  },
  plugins: [],
};

export default config;
