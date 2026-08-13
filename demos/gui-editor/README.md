# Toka grapheme editor demo

This macOS demo renders a custom single-line `TextEditor` document. Click the
window, then type; the `|` character is the self-drawn insertion caret. It
accepts committed platform text and applies left/right, Backspace, and Forward
Delete at extended-grapheme boundaries. Composition updates are deliberately
ignored; there is no native text-field widget, selection highlight, mouse
placement, IME editing state, shaping, bidi layout, or multiline layout.

`gui@0.1.0` is live in the public catalog and this demo commits its immutable
GUI and Unicode registry lock. Run from this directory with an installed Toka
`v1.0.0-rc.4` SDK and all three toolchain variables set:

```text
export TOKA=/path/to/sdk/bin/toka
export TOKAC=/path/to/sdk/bin/tokac
export TOKA_LIB=/path/to/sdk/lib
$TOKA fetch
$TOKA run
```

CI resolves and builds from an empty cache, then deletes all package and build
state and rebuilds offline from only the two locked release archives. It does
not run the executable; manual use requires a logged-in macOS desktop with a
Metal device.
