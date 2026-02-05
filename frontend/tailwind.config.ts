import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        md: {
          surface: '#121212',
          'surface-variant': '#49454F',
          'surface-container-lowest': '#0F0F0F',
          'surface-container-low': '#1C1B1F',
          'surface-container': '#211F26',
          'surface-container-high': '#2B2930',
          'surface-container-highest': '#36343B',
          'on-surface': '#E6E1E5',
          'on-surface-variant': '#CAC4D0',
          outline: '#938F99',
          'outline-variant': '#49454F',
          primary: '#D0BCFF',
          'on-primary': '#381E72',
          'primary-container': '#4F378B',
          'on-primary-container': '#EADDFF',
        }
      }
    }
  },
  plugins: [require("@tailwindcss/typography")]
};

export default config;
