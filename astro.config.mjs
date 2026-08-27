// @ts-check
import { defineConfig } from "astro/config";
import mdx from "@astrojs/mdx";

// Served from a project page, so everything lives under /italian-gcse/.
// Astro rewrites internal links for us; nothing in the content hard-codes it.
export default defineConfig({
  site: "https://ddb-ditto.github.io",
  base: "/italian-gcse",
  trailingSlash: "ignore",
  integrations: [mdx()],
  build: { format: "directory" },
});
