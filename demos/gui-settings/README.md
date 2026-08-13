# Toka GUI settings demo

`gui@0.1.0` is live in the public catalog and this demo commits its immutable
GUI and Unicode registry lock. Manual use requires macOS, a logged-in desktop
with Metal available, and an installed Toka `v1.0.0-rc.4` SDK. Set all three
toolchain variables:

```text
export TOKA=/path/to/sdk/bin/toka
export TOKAC=/path/to/sdk/bin/tokac
export TOKA_LIB=/path/to/sdk/lib
$TOKA fetch
$TOKA build
./target/debug/gui_settings_demo
```

CI resolves and builds from an empty cache, then deletes all package and build
state and rebuilds offline from only the two locked release archives. It
compiles and links the executable but does not open a window or require a GPU.

It opens a native Metal-backed window. Click the telemetry row to toggle its
state, scroll the list, press Command+R to request a redraw, and close the
window using its system close button.
