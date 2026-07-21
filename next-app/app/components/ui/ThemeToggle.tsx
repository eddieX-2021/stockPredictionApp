"use client";

import { useEffect, useState } from "react";

type ThemeChoice = "system" | "light" | "dark";

function applyTheme(choice: ThemeChoice) {
  const root = document.documentElement;
  if (choice === "system") {
    root.removeAttribute("data-theme");
  } else {
    root.dataset.theme = choice;
  }
}

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeChoice>("system");

  useEffect(() => {
    const saved = window.localStorage.getItem("theme") as ThemeChoice | null;
    const next = saved === "light" || saved === "dark" || saved === "system" ? saved : "system";
    setTheme(next);
    applyTheme(next);
  }, []);

  const cycleTheme = () => {
    const next: ThemeChoice = theme === "system" ? "light" : theme === "light" ? "dark" : "system";
    setTheme(next);
    window.localStorage.setItem("theme", next);
    applyTheme(next);
  };

  return (
    <button
      type="button"
      onClick={cycleTheme}
      className="rounded-md border border-border bg-subtle px-3 py-2 text-sm font-medium text-foreground hover:bg-surface"
      title="Cycle theme: system, light, dark"
    >
      Theme: {theme.charAt(0).toUpperCase() + theme.slice(1)}
    </button>
  );
}