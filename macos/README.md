# Hermes Studio Native macOS Desktop Shell

Native Cocoa & WebKit desktop application wrapper for Hermes Studio v2, providing custom borderless window chrome, integrated macOS traffic light semaphores inside the dark sidebar, native window dragging, and keyboard shortcuts.

---

## Features

- **Borderless Dark Chrome**: Configured with `fullSizeContentView` and `titlebarAppearsTransparent`.
- **Integrated Traffic Lights**: Native window close, miniaturize, and zoom buttons sit seamlessly in the top of the sidebar.
- **Window Dragging**: Full window draggable across header and sidebar areas via `isMovableByWindowBackground`.
- **Keyboard Shortcuts Bridge**: Native WebKit user script injection supporting `Cmd+B` (toggle sidebar) and `Cmd+N` (new conversation).
- **Auto-Retry Healthcheck**: Automatic reconnection loop waiting for FastAPI (`:8765`) and Next.js (`:3000`) servers to become ready.
- **Full macOS Edit Menus**: Standard Cut, Copy, Paste, Select All, Undo, and Redo keyboard handling.

---

## Build & Installation

### Prerequisites
- macOS 12.0+ (Apple Silicon or Intel)
- Xcode Command Line Tools (`swiftc`)

### Compile Standalone App
```bash
./macos/build-app.sh
```
The compiled application bundle will be created at `macos/build/Hermes Studio.app`.

### Compile & Install into /Applications
```bash
./macos/build-app.sh --install
```
This installs the standalone application directly to `/Applications/Hermes Studio.app`.

---

## Unified Studio Launcher

To start both background services (FastAPI on `:8765` + Next.js on `:3000`) and launch the native desktop app:

```bash
./start-studio.sh
```
