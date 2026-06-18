import { createTheme } from "@mui/material/styles";

/** MUI theme scoped to the chat widget (menus must sit above the panel). */
export function createWidgetTheme() {
  return createTheme({
    typography: {
      fontFamily:
        '"Open Sans", system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    },
    palette: {
      primary: {
        main: "#477bb8",
      },
      text: {
        primary: "#444444",
        secondary: "#555555",
      },
    },
    shape: {
      borderRadius: 12,
    },
    zIndex: {
      modal: 2_147_483_647,
    },
    components: {
      MuiMenu: {
        styleOverrides: {
          paper: {
            border: "1px solid #dadada",
            boxShadow: "0 12px 32px rgba(71, 123, 184, 0.2)",
          },
        },
      },
      MuiDivider: {
        styleOverrides: {
          root: {
            borderColor: "#dadada",
          },
        },
      },
    },
  });
}
