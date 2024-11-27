import curses
from src.models.schedule import ClassSchedule
from src.ui.terminal import TerminalUI
from src.ui.menu_handlers import MenuHandlers

def main(stdscr):
    ui = TerminalUI(stdscr)
    schedule = ClassSchedule()
    menu_handlers = MenuHandlers(ui, schedule)

    try:
        menu_handlers.show_startup_sequence()
        
        while True:
            if not menu_handlers.handle_main_menu():
                break
    except KeyboardInterrupt:
        pass

    menu_handlers.show_shutdown_sequence()

def run():
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    run()
