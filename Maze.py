import tkinter as tk
import random
import serial                          # pyserial: reads the Pico over USB
from serial.tools import list_ports
 
#Maze configuration
COLS, ROWS = 15, 15        # Maze size
CELL = 60                  # Size of each cell
NUM_GOALS = 5              # how many fish to collect
REVEAL_RADIUS = 0          # How many cells away walls become visible
 
#Pico connection
PICO_PORT = None           # None = find the Pico automatically. Or type it, e.g. "COM5"
BAUD = 115200
POLL_MS = 20               # How often the game checks for button presses
 
#Total size of the drawing area
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL
 
 
#Looks through the USB ports for a Raspberry Pi Pico (its USB vendor ID is 0x2E8A)
def find_pico():
    if PICO_PORT:
        return PICO_PORT
    for p in list_ports.comports():
        if p.vid == 0x2E8A:
            return p.device
    return None
 
 
# Maze generation using recursive backtracker (checks if all cells are accesible)
def make_maze(cols, rows):
    # Each cell is written as column and row and has a wall in each direction
    walls = {(c, r): {"N": True, "S": True, "E": True, "W": True}
             for c in range(cols) for r in range(rows)}
 
    #If a wall opens up the opposite side of the cell adjacent to that direction needs to open
    #allowing the maze to be open
    opposite = {"N": "S", "S": "N", "E": "W", "W": "E"}
 
    #The start cell is the top left cornerof the maze
    start = (0, 0)
    #Inverts the coordinates of the maze
    step = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
    #The set of cells that the algorith passed through (The bulldozer destroying the walls)
    visited = {start}
    #List remembering the path the bulldozer walked through
    stack = [start]
 
    #Keep making the trail until it gets back again to the beginning
    while stack:
        #[-1] Indicates where the bulldozer is now
        c, r = stack[-1]
 
        #List of the 4 possible directions it can make a path
        options = []
        for d, (dc, dr) in step.items():
            #The neighbors cell from the rows and columns in direction 'd'
            n = (c + dc, r + dr)
            #The neighbor cell must be inside the specified maze dimension AND not already visited
            if n in walls and n not in visited:
                options.append((d, n))
 
        if options:
            #Picks a random direction to go
            d, n = random.choice(options)
            walls[(c, r)][d] = False          # Reveals the walls
            walls[n][opposite[d]] = False     # from both sides
            visited.add(n)      #Mark the new cell as visited
            stack.append(n)     #Move the bulldozer there
        else:
            stack.pop()
    return walls
 
 
# ---------- The game ----------
class MazeGame:
 
    #__init__ runs once by itself when the game is created
    #Builds the window of the game
    def __init__(self, root):
        self.root = root
        root.title("Maze Explorer")
 
        #Sets the font of the texts displayed
        self.info = tk.Label(root, font=("Arial", 16))
        #Displays it in the window
        self.info.pack(pady=5)
 
        #The background of the window
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
        self.canvas.pack()
 
        #Button creating a new maze when clicked, works as repetition
        tk.Button(root, text="New Maze", command=self.new_game).pack(pady=5)
 
        #Small line of text showing if the Pico controller is connected
        self.status = tk.Label(root, font=("Arial", 10), fg="gray")
        self.status.pack()
 
        #Connect to the Pico (the 4 buttons replace the keyboard arrows)
        self.pico = None        # The USB connection, None while not connected
        self.buffer = ""        # Letters received from the Pico that are not processed yet
        self.retry = 0          # Counts the checks between reconnection attempts
        self.connect_pico()
 
        #Start the game
        self.new_game()
 
        #Start checking for button presses
        self.poll_pico()
 
    #Tries to open the USB connection to the Pico
    def connect_pico(self):
        port = find_pico()
        if port is None:
            self.status.config(text="Controller not found - plug in the Pico")
            return
        try:
            self.pico = serial.Serial(port, BAUD, timeout=0)
            self.status.config(text=f"Controller connected ({port})")
        except (serial.SerialException, OSError):
            self.pico = None
            self.status.config(text=f"Could not open {port} - is Thonny still connected to the Pico?")
 
    #Runs over and over: reads the letters (N, S, W, E) the Pico sends when a button is pressed
    def poll_pico(self):
        if self.pico is None:
            #Not connected: try again about once per second
            self.retry += 1
            if self.retry >= 1000 // POLL_MS:
                self.retry = 0
                self.connect_pico()
        else:
            try:
                #Grab everything that arrived since the last check
                data = self.pico.read(self.pico.in_waiting)
                self.buffer += data.decode(errors="ignore")
                #Each press arrives as one letter followed by a new line
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    direction = line.strip()
                    if direction in ("N", "S", "E", "W"):
                        self.move(direction)
            except (serial.SerialException, OSError):
                #The cable was unplugged
                self.pico = None
                self.status.config(text="Controller unplugged - reconnecting...")
        self.root.after(POLL_MS, self.poll_pico)    #Check again in 20ms
 
    #Creates a new game when the button "New Maze" is pressed
    def new_game(self):
        #Builds New Maze
        self.walls = make_maze(COLS, ROWS)
        self.player = (0, 0)
        # pick random goal cells (not the starting cell)
        cells = [(c, r) for c in range(COLS) for r in range(ROWS) if (c, r) != (0, 0)]
        self.goals = set(random.sample(cells, NUM_GOALS))
 
        self.collected = 0           #Preys reached
        self.seen_cells = set()      # cells whose walls have been revealed
        self.won = False             # Becomes true when all prey's are collected
 
        self.reveal()   #Reveals the area of the starting point
        self.draw()     #Draws everything on the screen
 
    # Marks nearby cells and reveals them so the walls can be drawn and stays on until a new game starts
    def reveal(self):
        pc, pr = self.player
        for dc in range(-REVEAL_RADIUS, REVEAL_RADIUS + 1):
            for dr in range(-REVEAL_RADIUS, REVEAL_RADIUS + 1):
                cell = (pc + dc, pr + dr)
 
                #Makes sure that it is inside the maze
                if cell in self.walls:
                    self.seen_cells.add(cell)   #Remembers which cells have been revealed
 
    #Moves the player one cell if there is no wall in that direction
    def move(self, direction):
        if self.won:
            return
        step = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}[direction]
        c, r = self.player
        if not self.walls[(c, r)][direction]:
            self.player = (c + step[0], r + step[1])
            if self.player in self.goals:
                self.goals.remove(self.player)
                self.collected += 1
                if self.collected == NUM_GOALS:
                    self.won = True
            self.reveal()
        self.draw()
 
    #Draws everything by erasing the canvas and redrawing it again
    def draw(self):
        cv = self.canvas
        cv.delete("all")    #Wipe everything
 
        # Walls (only the ones in revealed cells)
        for (c, r) in self.seen_cells:
 
            x, y = c * CELL, r * CELL
            w = self.walls[(c, r)]
 
            #for each wall that is discovered, draw a line along the edge
            if w["N"]: cv.create_line(x, y, x + CELL, y, fill="white", width=3)
            if w["S"]: cv.create_line(x, y + CELL, x + CELL, y + CELL, fill="white", width=3)
            if w["W"]: cv.create_line(x, y, x, y + CELL, fill="white", width=3)
            if w["E"]: cv.create_line(x + CELL, y, x + CELL, y + CELL, fill="white", width=3)
 
        # Fish (always visible so kids know what to look for)
        for (c, r) in self.goals:
            cx, cy = c * CELL + CELL // 2, r * CELL + CELL // 2
            cv.create_text(cx, cy, text="🐟", fill="gold", font=("Arial", 22))
 
        # Player
        pc, pr = self.player
        m = 8
        cv.create_oval(pc * CELL + m, pr * CELL + m,
                       (pc + 1) * CELL - m, (pr + 1) * CELL - m,
                       fill="deepskyblue", outline="")
 
        # Status text
        if self.won:
            self.info.config(text="🎉 You found all the fish! Great job! 🎉")
        else:
            self.info.config(text=f"Fish collected: {self.collected} / {NUM_GOALS}")
 
 
root = tk.Tk()  #Creates the game window
MazeGame(root)  #Initializes the game in the window
root.mainloop() #Keeps window and game running, allowing for inputs