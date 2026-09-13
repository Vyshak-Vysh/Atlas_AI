const THEME_INIT_SCRIPT = `
(function () {
  try {
    var raw = localStorage.getItem("atlasai.ui");
    var theme = raw ? JSON.parse(raw).state.theme : "system";
    if (theme === "light" || theme === "dark") {
      document.documentElement.setAttribute("data-theme", theme);
    }
  } catch (e) {}
})();
`;

/** Runs before hydration so the light/dark choice applies on first paint —
 * without this, the page would flash the "system" theme and then snap to
 * the user's stored preference once React hydrates. */
export function ThemeScript() {
  // eslint-disable-next-line react/no-danger
  return <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />;
}
