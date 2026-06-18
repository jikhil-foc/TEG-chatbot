import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import type { Source } from "@/types";

interface CitationPopoverProps {
  index: number;
  source: Source;
}

function formatSourceUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const path = `${parsed.pathname}${parsed.search}`;
    return path === "/" ? parsed.hostname : `${parsed.hostname}${path}`;
  } catch {
    return url;
  }
}

function OpenInNewIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M14 3h7v7M10 14 21 3M21 14v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CitationPopover({ index, source }: CitationPopoverProps) {
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const open = Boolean(anchorEl);
  const title = source.title || formatSourceUrl(source.url) || `Source ${index}`;
  const showUrl =
    Boolean(source.url) &&
    source.title.length > 0 &&
    source.url !== source.title;

  return (
    <span className="teg-citation">
      <button
        type="button"
        className="teg-citation__trigger"
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label={`Source ${index}: ${title}`}
        onClick={(event) => setAnchorEl(event.currentTarget)}
      >
        [{index}]
      </button>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        transformOrigin={{ vertical: "top", horizontal: "center" }}
        slotProps={{
          paper: {
            className: "teg-citation-menu",
            sx: {
              minWidth: 240,
              maxWidth: 320,
              mt: 0.75,
            },
          },
          list: {
            sx: { py: 0 },
          },
        }}
      >
        <Box className="teg-citation-menu__header">
          <Typography
            component="p"
            variant="caption"
            className="teg-citation-menu__label"
          >
            Source [{index}]
          </Typography>
          <Typography
            component="p"
            variant="body2"
            className="teg-citation-menu__title"
          >
            {title}
          </Typography>
          {showUrl && source.url ? (
            <Typography
              component="p"
              variant="caption"
              className="teg-citation-menu__url"
            >
              {formatSourceUrl(source.url)}
            </Typography>
          ) : null}
        </Box>
        {source.url ? (
          <>
            <Divider />
            <MenuItem
              component="a"
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="teg-citation-menu__action"
              onClick={() => setAnchorEl(null)}
            >
              <ListItemIcon className="teg-citation-menu__action-icon">
                <OpenInNewIcon />
              </ListItemIcon>
              <ListItemText
                primary="Open source"
                slotProps={{
                  primary: {
                    className: "teg-citation-menu__action-text",
                  },
                }}
              />
            </MenuItem>
          </>
        ) : null}
      </Menu>
    </span>
  );
}
