import curses
import threading
import datastream
import time
import os
## import socket ## To connect to our data source, may be unnecessary with datastream.py :)

## Class to handle drawing / updating displayed
## text in a separate thread. This should allow
## for smoother, more efficent prettiness.

class draw_thread(threading.Thread):
    def __init__(self):
        super(draw_thread, self).__init__()
        
        ## TODO: set custom color pairs
        # self.colors = { 

        #             }
        self.columns =  ( 'is_active', 'user', 'n_procs', 'cpu', 'mem', 'top_proc' )
        self.col_text = ( 'Active?', 'User', '#Procs', 'CPU (%)', 'Mem (%)', 'Top Proc' )

        self.sort_col = 3 ## Default to cpu index
        self.interval = 100 ## Update rate in MS. use curses.napms!
        self.active_only = False ## Whether to show only "active" cgroups or all
        self.exit_chr = False
        self.input_chrs = { ord('q'): 'self.exit_chr=True',
                            ord('u'): 'self.sort_col=1',
                            ord('c'): 'self.sort_col=3',
                            ord('m'): 'self.sort_col=4',
                            ord('r'): 'self.refresh_data()'
                        }
        self.dimensions = tuple() ## ( height, width )
        self.last_dim = (999999, 999999)
        self.col_width = 0
        self.last_state = 3 ## (0: normal output, 1: help output, 2: error output)
        self.state = 0 ## ditto. these are used to track whether we need to clear the whole window
        self.header = None
        self.body = None

    def draw_header(self, scr):
        scr.move(0,0)
        scr.addnstr(0,0, "CGrouPynator" + (" " * (self.dimensions[1] - 12) ), self.dimensions[1], curses.A_REVERSE)



        
    def run(self):
        if os.path.exists('tmplog'):
            os.remove('tmplog')
        screen = curses.initscr()
        self.dimensions = screen.getmaxyx()
        self.header = curses.newwin(8, self.dimensions[1], 0, 0)
        self.body = curses.newwin(self.dimensions[0] - 8, self.dimensions[1], 9, 0)
        try:
            self.exit_chr = False
            in_chr = None
            
            screen.nodelay(True)
            screen.keypad(1)
            curses.typeahead(-1)
            curses.start_color()
            curses.use_default_colors()

            while not self.exit_chr:
                self.dimensions = screen.getmaxyx()

                
                if self.dimensions[0] < 14 or self.dimensions[1] < 30:
                    self.state = 2
                    #if not all( self.dimensions[i] == self.last_dim[i] for i in (0,1)):
                    if self.state != self.last_state:
                        screen.clear()
                        
                        screen.move(0,0)
                        screen.addnstr(0,0,"Screen too small!",self.dimensions[1])
                        screen.refresh()
                        self.last_dim = self.dimensions
                    
                        self.last_state = 2
                    
                        
                    curses.napms(self.interval)
                    self.last_state = 2
                    continue
               
                else:
                    self.state = 0
                    if self.state != self.last_state:
                        screen.clear()
                    self.draw_header(screen)
                    input_loc = self.dimensions[1] - 2 
                    # if in_chr:
                    #     screen.addstr(1, input_loc, chr(in_chr))
                    if in_chr in self.input_chrs.keys():
                        print(self.input_chrs[in_chr])
                        exec( self.input_chrs[in_chr])
                        in_chr = ""
                    
                    screen.move(6,0)
                    self.col_width = int(self.dimensions[1] / 6)
                    insert_pos = 0
                    for i in range(0, len(self.col_text)):
                        writebuf = self.col_text[i] + (" " * (self.col_width - len(self.col_text[i]))) 
        
                        if i == self.sort_col:
                            screen.addnstr(6, insert_pos, writebuf, self.col_width)
                        else:
                            screen.addnstr(6, insert_pos, writebuf, self.col_width, curses.A_REVERSE)
                        insert_pos += self.col_width
                    
                    screen.move(self.dimensions[0] - 1,input_loc)
                    in_chr = screen.getch(self.dimensions[0] - 1,input_loc)
                    screen.refresh()
                    self.last_dim = self.dimensions
                    self.last_state = self.state
                    curses.napms(self.interval)
            fobj.close()
            curses.endwin()
        except Exception as e:
            screen.addstr(2,1, "FAILURE")
            time.sleep(1)
            curses.endwin()
            print(e)
    