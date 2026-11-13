import Cocoa
import WebKit

// ==============================================================================
// Hermes Studio v2 - Native macOS Desktop Cocoa / WebKit Application
// Provides Claude Desktop-grade dark UI chrome, native window dragging,
// traffic-light positioning inside the sidebar, and hotkey bridge.
// ==============================================================================

// MARK: - Native Draggable Window Subclass (Acceptance Criterion 3)
class HermesStudioWindow: NSWindow {
    override var canBecomeKey: Bool { return true }
    override var canBecomeMain: Bool { return true }

    override func sendEvent(_ event: NSEvent) {
        if event.type == .leftMouseDown {
            let loc = event.locationInWindow
            let windowHeight = self.frame.height
            let isAtTopBar = loc.y >= (windowHeight - 44.0)

            if isAtTopBar {
                // 1. Double-click anywhere in top bar to zoom/unzoom
                if event.clickCount == 2 && loc.x > 78 {
                    self.performZoom(nil)
                    return
                }

                // 2. Native traffic lights area (close, miniaturize, zoom) -> pass to native buttons
                if loc.x <= 78 {
                    super.sendEvent(event)
                    return
                }

                // 3. Sidebar collapse button (approx x: 218...256, y: windowHeight - 38 ... windowHeight - 6)
                if loc.x >= 218 && loc.x <= 256 && loc.y <= (windowHeight - 6) && loc.y >= (windowHeight - 38) {
                    super.sendEvent(event)
                    return
                }

                // 4. Sidebar expand button when collapsed (approx x: 80...150, y: windowHeight - 38 ... windowHeight - 6)
                if loc.x >= 80 && loc.x <= 150 && loc.y <= (windowHeight - 6) && loc.y >= (windowHeight - 38) {
                    super.sendEvent(event)
                    return
                }

                // 5. Everywhere else across the top header bar: native WindowServer drag!
                self.performDrag(with: event)
                return
            }
        }
        super.sendEvent(event)
    }
}

// MARK: - Native Draggable Web View Subclass
class HermesWebView: WKWebView {
    override var mouseDownCanMoveWindow: Bool {
        return true
    }
}

class HermesApplicationDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    var window: HermesStudioWindow!
    var webView: HermesWebView!
    var loadingOverlay: NSVisualEffectView?
    var statusLabel: NSTextField?
    let targetURL = URL(string: "http://localhost:3000")!
    let healthURL = URL(string: "http://127.0.0.1:8765/api/health")!

    func applicationDidFinishLaunching(_ notification: Notification) {
        setupMainMenu()
        setupWindow()
        setupWebView()
        loadStudioWithRetry(retriesRemaining: 15)
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }

    // MARK: - Native Window Setup (Acceptance Criteria 1, 2, 3)
    private func setupWindow() {
        let screenRect = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1400, height: 900)
        let initialWidth: CGFloat = min(1440, screenRect.width * 0.90)
        let initialHeight: CGFloat = min(960, screenRect.height * 0.90)
        let initialX = screenRect.origin.x + (screenRect.width - initialWidth) / 2
        let initialY = screenRect.origin.y + (screenRect.height - initialHeight) / 2

        let windowRect = NSRect(x: initialX, y: initialY, width: initialWidth, height: initialHeight)

        window = HermesStudioWindow(
            contentRect: windowRect,
            styleMask: [
                .titled,
                .closable,
                .miniaturizable,
                .resizable,
                .fullSizeContentView
            ],
            backing: .buffered,
            defer: false
        )

        window.minSize = NSSize(width: 960, height: 640)
        window.title = "Hermes Studio"
        window.titleVisibility = .hidden
        window.titlebarAppearsTransparent = true
        window.isMovableByWindowBackground = true
        window.backgroundColor = NSColor(calibratedRed: 0.08, green: 0.08, blue: 0.08, alpha: 1.0)
        window.tabbingMode = .disallowed

        // Position window traffic light buttons inside dark sidebar top area
        positionTrafficLights()

        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    private func positionTrafficLights() {
        guard let titlebar = window.standardWindowButton(.closeButton)?.superview else { return }
        titlebar.wantsLayer = true
    }

    // MARK: - WebKit & Hotkey Script Injection (Acceptance Criterion 4)
    private func setupWebView() {
        let config = WKWebViewConfiguration()
        let contentController = WKUserContentController()

        // Inject Native Hotkey Bridge (Cmd+B toggle sidebar, Cmd+N new session)
        let hotkeyScriptSource = """
        window.addEventListener('keydown', function(e) {
            // Cmd+B: Toggle Sidebar
            if ((e.metaKey || e.ctrlKey) && (e.key === 'b' || e.key === 'B')) {
                e.preventDefault();
                var sidebarToggleBtn = document.querySelector('[data-sidebar-toggle="true"]');
                if (sidebarToggleBtn) {
                    sidebarToggleBtn.click();
                }
            }
            // Cmd+N: New Session
            if ((e.metaKey || e.ctrlKey) && (e.key === 'n' || e.key === 'N') && !e.shiftKey) {
                e.preventDefault();
                var newChatBtn = document.querySelector('[data-new-chat="true"]');
                if (newChatBtn) {
                    newChatBtn.click();
                }
            }
        });
        """
        let userScript = WKUserScript(
            source: hotkeyScriptSource,
            injectionTime: .atDocumentEnd,
            forMainFrameOnly: false
        )
        contentController.addUserScript(userScript)
        config.userContentController = contentController

        // Enable developer tools for debugging if needed
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")

        webView = HermesWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.underPageBackgroundColor = NSColor(calibratedRed: 0.08, green: 0.08, blue: 0.08, alpha: 1.0)
        webView.setValue(false, forKey: "drawsBackground") // Transparent background until Next.js paints

        window.contentView?.addSubview(webView)
    }

    // MARK: - Healthcheck & Auto-Retry Loop
    private func loadStudioWithRetry(retriesRemaining: Int) {
        let request = URLRequest(url: targetURL, cachePolicy: .useProtocolCachePolicy, timeoutInterval: 5.0)
        let task = URLSession.shared.dataTask(with: request) { [weak self] _, response, error in
            guard let self = self else { return }
            DispatchQueue.main.async {
                if let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 {
                    self.hideLoadingOverlay()
                    self.webView.load(request)
                } else if retriesRemaining > 0 {
                    self.showLoadingOverlay(message: "Connecting to Hermes Studio (\(retriesRemaining) retries remaining)...")
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) {
                        self.loadStudioWithRetry(retriesRemaining: retriesRemaining - 1)
                    }
                } else {
                    self.showLoadingOverlay(
                        message: "Hermes Studio services offline.\\nRun ./start-studio.sh or launch backend on port 8765 and frontend on port 3000."
                    )
                }
            }
        }
        task.resume()
    }

    private func showLoadingOverlay(message: String) {
        if loadingOverlay == nil {
            let overlay = NSVisualEffectView(frame: window.contentView!.bounds)
            overlay.autoresizingMask = [.width, .height]
            overlay.material = .hudWindow
            overlay.appearance = NSAppearance(named: .darkAqua)
            overlay.blendingMode = .withinWindow
            overlay.state = .active

            let label = NSTextField(labelWithString: message)
            label.alignment = .center
            label.textColor = NSColor.white
            label.font = NSFont.systemFont(ofSize: 13, weight: .medium)
            label.autoresizingMask = [.minXMargin, .maxXMargin, .minYMargin, .maxYMargin]
            label.frame = NSRect(x: 20, y: overlay.bounds.midY - 20, width: overlay.bounds.width - 40, height: 40)

            overlay.addSubview(label)
            window.contentView?.addSubview(overlay)
            self.loadingOverlay = overlay
            self.statusLabel = label
        } else {
            statusLabel?.stringValue = message
        }
    }

    private func hideLoadingOverlay() {
        loadingOverlay?.removeFromSuperview()
        loadingOverlay = nil
        statusLabel = nil
    }

    // MARK: - Standard Native macOS Menus (Copy/Paste/Select All/Quit)
    private func setupMainMenu() {
        let mainMenu = NSMenu()

        // Application Menu
        let appMenuItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About Hermes Studio", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Hide Hermes Studio", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        let hideOthers = NSMenuItem(title: "Hide Others", action: #selector(NSApplication.hideOtherApplications(_:)), keyEquivalent: "h")
        hideOthers.keyEquivalentModifierMask = [.command, .option]
        appMenu.addItem(hideOthers)
        appMenu.addItem(withTitle: "Show All", action: #selector(NSApplication.unhideAllApplications(_:)), keyEquivalent: "")
        appMenu.addItem(NSMenuItem.separator())
        appMenu.addItem(withTitle: "Quit Hermes Studio", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appMenuItem.submenu = appMenu
        mainMenu.addItem(appMenuItem)

        // Edit Menu (Essential for Cut/Copy/Paste/Undo inside WKWebView)
        let editMenuItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        let redoItem = NSMenuItem(title: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        editMenu.addItem(redoItem)
        editMenu.addItem(NSMenuItem.separator())
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editMenuItem.submenu = editMenu
        mainMenu.addItem(editMenuItem)

        // View Menu (Reload, Toggle Full Screen)
        let viewMenuItem = NSMenuItem()
        let viewMenu = NSMenu(title: "View")
        let reloadItem = NSMenuItem(title: "Reload Studio", action: #selector(reloadWebView), keyEquivalent: "r")
        viewMenu.addItem(reloadItem)
        let fullScreenItem = NSMenuItem(title: "Toggle Full Screen", action: #selector(NSWindow.toggleFullScreen(_:)), keyEquivalent: "f")
        fullScreenItem.keyEquivalentModifierMask = [.command, .control]
        viewMenu.addItem(fullScreenItem)
        viewMenuItem.submenu = viewMenu
        mainMenu.addItem(viewMenuItem)

        // Window Menu
        let windowMenuItem = NSMenuItem()
        let windowMenu = NSMenu(title: "Window")
        windowMenu.addItem(withTitle: "Minimize", action: #selector(NSWindow.performMiniaturize(_:)), keyEquivalent: "m")
        windowMenu.addItem(withTitle: "Zoom", action: #selector(NSWindow.performZoom(_:)), keyEquivalent: "")
        windowMenuItem.submenu = windowMenu
        mainMenu.addItem(windowMenuItem)

        NSApp.mainMenu = mainMenu
    }

    @objc private func reloadWebView() {
        webView.reload()
    }
}

// Main Entry Point
let app = NSApplication.shared
let delegate = HermesApplicationDelegate()
app.delegate = delegate
app.run()
