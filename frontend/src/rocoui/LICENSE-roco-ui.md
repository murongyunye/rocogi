# License Notice — rocokingdom-ui assets

The files in this directory tree:

- `src/rocoui/style.css`
- `src/rocoui/font.css`
- `src/rocoui/fonts/roco-kingdom-rune.ttf`
- `src/rocoui/fonts/roco-kingdom-sans.ttf`

are unmodified dist assets from the npm package **rocokingdom-ui@0.0.1-beta.0**
(source: https://github.com/rookie-orange/rocokingdom-ui).

The npm manifest (`package.json`) of that package declares
`"license": "MIT"` (author: Charles Lee). The published tarball ships no
separate LICENSE file; upstream repository: https://github.com/rookie-orange/rocokingdom-ui.

The Vue 3 component ports in `src/rocoui/*.{ts,vue}` are reimplementations
against those styles (React/Radix → Vue, dependency-free) and carry the
attribution above. They are distributed under the same license as the rocogi
project. See `src/rocoui/PORT.md` for the porting notes.
