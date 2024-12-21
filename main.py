import curses
import signal
import sys
from src.ui.terminal import TerminalUI
from src.ui.menu_handlers import MenuHandlers

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    sys.exit(0)

def main(stdscr):
    signal.signal(signal.SIGINT, signal_handler)
    
    ui = TerminalUI(stdscr)
    menu_handlers = MenuHandlers(ui)

    try:
        menu_handlers.show_startup_sequence()
        
        running = True
        while running:
            if not menu_handlers.handle_main_menu():
                running = False

    except KeyboardInterrupt:
        pass
    except curses.error:
        pass
    finally:
        menu_handlers.show_shutdown_sequence()

def run():
    """
    Main entry point for the application.
    Wraps the main function in curses initialization.
    """
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        try:
            curses.endwin()
        except Exception:
            pass
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    run()
