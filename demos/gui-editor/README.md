# Toka grapheme editor demo

This macOS demo renders a custom single-line `TextEditor` document. Click the
window, then type; the `|` character is the self-drawn insertion caret. It
accepts committed platform text and applies left/right, Backspace, and Forward
Delete at extended-grapheme boundaries. Composition updates are deliberately
ignored; there is no native text-field widget, selection highlight, mouse
placement, IME editing state, shaping, bidi layout, or multiline layout.

After `gui@0.1.0` is live in the public catalog, run from this directory with
an installed Toka `v1.0.0-rc.4` SDK. Set all three toolchain variables; the
first fetch is online. This pre-release repository state intentionally carries
no demo `package.lock`; immutable locks and demo CI follow the package release.

```text
export TOKA=/path/to/sdk/bin/toka
export TOKAC=/path/to/sdk/bin/tokac
export TOKA_LIB=/path/to/sdk/lib
$TOKA fetch
$TOKA run
```
