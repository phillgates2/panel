#!/usr/bin/env python3
"""
Enhanced Development Server
Provides improved hot reload and file watching for development
"""

import os
import time
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from werkzeug.serving import make_server


class ReloadHandler(FileSystemEventHandler):
    """File system event handler for hot reload"""

    def __init__(self, server, watch_paths: Set[str], ignore_patterns: Set[str] = None):
        self.server = server
        self.watch_paths = watch_paths
        self.ignore_patterns = ignore_patterns or {
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "node_modules",
        }
        self.last_reload = time.time()
        self.reload_delay = 1.0  # Minimum delay between reloads

    def should_ignore(self, path: str) -> bool:
        """Check if path should be ignored"""
        path_obj = Path(path)
        for pattern in self.ignore_patterns:
            if pattern in str(path_obj) or str(path_obj).endswith(pattern):
                return True
        return False

    def should_reload(self, path: str) -> bool:
        """Check if file change should trigger reload"""
        if self.should_ignore(path):
            return False

        # Only reload on Python files, templates, and config
        path_obj = Path(path)
        if path_obj.suffix in {".py", ".html", ".jinja2", ".cfg", ".ini"}:
            return True

        # Reload on config files
        if path_obj.name in {"config.py", "requirements.txt", "pyproject.toml"}:
            return True

        return False

    def on_modified(self, event):
        """Handle file modification"""
        if not event.is_directory and self.should_reload(event.src_path):
            current_time = time.time()
            if current_time - self.last_reload > self.reload_delay:
                print(f"\n?? File changed: {event.src_path}")
                print("?? Reloading server...")
                self.last_reload = current_time
                # Trigger server reload
                os._exit(3)  # Special exit code for reload


def create_development_server(app, host="127.0.0.1", port=8080, use_reloader=True):
    """Create development server with enhanced file watching"""

    if use_reloader:
        # Set up file watching
        watch_paths = {
            ".",  # Current directory
            "src",  # Source code
            "templates",  # Templates
            "static",  # Static files
        }

        # Create observer
        observer = Observer()
        server = make_server(host, port, app, threaded=True)

        handler = ReloadHandler(server, watch_paths)
        for path in watch_paths:
            if os.path.exists(path):
                observer.schedule(handler, path, recursive=True)

        # Start observer in background
        observer.start()

        try:
            print(f"?? Development server starting on http://{host}:{port}")
            print("?? File watching enabled - server will reload on changes")
            print("Press Ctrl+C to stop")

            server.serve_forever()
        except KeyboardInterrupt:
            print("\n?? Shutting down server...")
        except SystemExit as e:
            if e.code == 3:  # Reload signal
                print("?? Reload triggered, restarting...")
                observer.stop()
                observer.join()
                return True  # Signal to restart
            else:
                raise
        finally:
            observer.stop()
            observer.join()

    else:
        # Standard server without reloader
        server = make_server(host, port, app, threaded=True)
        try:
            print(f"?? Server starting on http://{host}:{port}")
            server.serve_forever()
        except KeyboardInterrupt:
            print("\n?? Shutting down server...")

    return False


def main():
    """Main development server entry point"""
    from app import create_app

    # Get configuration from environment
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "8080"))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() == "true"
    use_reloader = os.environ.get("FLASK_USE_RELOADER", "True").lower() == "true"

    # Create Flask app
    app = create_app()
    app.debug = debug

    # Enable development features
    if debug:
        print("?? Debug mode enabled")
        print("?? Hot reload enabled" if use_reloader else "?? Hot reload disabled")

    # Start server with reload loop
    while True:
        try:
            should_restart = create_development_server(
                app, host=host, port=port, use_reloader=use_reloader and debug
            )
            if not should_restart:
                break
        except Exception as e:
            print(f"? Server error: {e}")
            if debug:
                import traceback

                traceback.print_exc()
            break

    print("?? Server stopped")


if __name__ == "__main__":
    main()
