import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "Panqake",
  description: "Stack Git Branches Without the Headache",
  cleanUrls: true,

  // Temporary until I clean up other pending docs sections
  ignoreDeadLinks: true,

  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    logo: "/panqake.svg",

    nav: [
      { text: "Home", link: "/" },
      { text: "Documentation", link: "/introduction" },
      { text: "GitHub", link: "https://github.com/SarthakJariwala/panqake" },
    ],

    sidebar: [
      {
        text: "Getting Started",
        items: [
          { text: "Introduction", link: "/introduction" },
          { text: "Installation", link: "/installation" },
          { text: "Quick Start", link: "/quickstart" },
        ],
      },
      {
        text: "Commands",
        items: [
          { text: "Overview", link: "/commands/" },
          {
            text: "Navigation",
            items: [
              { text: "list/ls", link: "/commands/navigation/list" },
              { text: "switch/co", link: "/commands/navigation/switch" },
              { text: "up", link: "/commands/navigation/up" },
              { text: "down", link: "/commands/navigation/down" },
            ],
          },
          {
            text: "Branch Management",
            items: [
              { text: "new", link: "/commands/branch-management/new" },
              { text: "delete", link: "/commands/branch-management/delete" },
              { text: "rename", link: "/commands/branch-management/rename" },
              { text: "track", link: "/commands/branch-management/track" },
              { text: "untrack", link: "/commands/branch-management/untrack" },
            ],
          },
          {
            text: "Update & Sync",
            items: [
              { text: "modify", link: "/commands/update-sync/modify" },
              { text: "update", link: "/commands/update-sync/update" },
              { text: "sync", link: "/commands/update-sync/sync" },
            ],
          },
          {
            text: "PR Operations",
            items: [
              { text: "pr", link: "/commands/pr-operations/pr" },
              { text: "submit", link: "/commands/pr-operations/submit" },
              { text: "merge", link: "/commands/pr-operations/merge" },
            ],
          },
        ],
      },
      {
        text: "Guides & Tutorials",
        items: [{ text: "Advanced Workflows", link: "/advanced-workflows" }],
      },
      { text: "Changelog", link: "/CHANGELOG" },
    ],

    socialLinks: [
      { icon: "github", link: "https://github.com/SarthakJariwala/panqake" },
    ],

    search: {
      provider: "local",
    },

    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2025-present",
    },
  },
});
