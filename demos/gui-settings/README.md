# Toka GUI settings demo

After `gui@0.1.0` is live in the public catalog, this demo requires macOS, a
logged-in desktop session with Metal available, and an installed Toka
`v1.0.0-rc.4` SDK. Set all three toolchain variables; the first fetch is
online. This pre-release repository state intentionally carries no demo
`package.lock`; immutable locks and demo CI follow the package release.

```text
export TOKA=/path/to/sdk/bin/toka
export TOKAC=/path/to/sdk/bin/tokac
export TOKA_LIB=/path/to/sdk/lib
$TOKA fetch
$TOKA build
./target/debug/gui_settings_demo
```

It opens a native Metal-backed window. Click the telemetry row to toggle its
state, scroll the list, press Command+R to request a redraw, and close the
window using its system close button.
