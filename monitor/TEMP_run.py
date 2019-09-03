import curses
import display
import time
thread = display.draw_thread()
print("Starting Curses in 3...")
time.sleep(3)
thread.run()

# input_chrs = { 'q': 'self.exit_chr = True',
#                 'm': 'self.sort_col = "mem"',
#                 'c': 'self.sort_col = "cpu"',
#                 'u': 'self.sort_col = "user"',
#                 'r': 'self.refresh_data()'
#             }

# interval = 250

# def run(screen):
#     ## TODO: TAKE THIS OUT BEFORE RUNNING
#     ## JUST HERE TO MAKE AUTOCOMPLETE EASIER
#     # screen = curses.initscr()
#     ########################################
#     exit_chr = False
#     in_chr = ""
#     screen.nodelay(True)
#     screen.keypad(1)

#     while not exit_chr:
#         screen.refresh()
#         if in_chr in input_chrs.keys():
#             eval( input_chrs[in_chr])
#         else:
#             continue
#         input_loc = 16
#         screen.move(1,1)
#         screen.addstr(1,1, "Doin' thangs")
#         screen.move(1,input_loc)
#         in_chr = screen.getch(1,input_loc)
        
#         curses.napms(interval)

#     curses.endwin()

# curses.wrapper(run)
