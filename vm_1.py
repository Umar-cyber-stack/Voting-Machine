import sqlite3
from tkinter import *
from tkinter import messagebox, ttk
import time
from tkinter import font as tkfont
import datetime
import random # <--- NEW: Import random for balloon animations

# --- Import matplotlib for graphing ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# --- Database setup ---
conn = sqlite3.connect("voting.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    username TEXT PRIMARY KEY,
    password TEXT
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS voters (
    username TEXT PRIMARY KEY,
    password TEXT,
    birth_year INTEGER,
    voted INTEGER DEFAULT 0
)""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    party_name TEXT PRIMARY KEY,
    leader_name TEXT,
    password TEXT,
    votes INTEGER DEFAULT 0
)""")

# --- Election State Table ---
cursor.execute("""
CREATE TABLE IF NOT EXISTS election_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'Pending', -- 'Pending', 'Active', 'Closed'
    start_time TEXT,
    end_time TEXT
)""")

# --- Ensure there's always one row in election_state ---
cursor.execute("INSERT OR IGNORE INTO election_state (id, status) VALUES (1, 'Pending')")
conn.commit()

# --- Color Scheme ---
BG_COLOR = "#2c3e50"    # Dark blue-gray
FG_COLOR = "#ecf0f1"    # Light gray
ACCENT_COLOR = "#3498db"    # Bright blue
BUTTON_COLOR = "#2980b9"    # Slightly darker blue
HOVER_COLOR = "#1abc9c"    # Teal
ERROR_COLOR = "#e74c3c"    # Red
SUCCESS_COLOR = "#2ecc71"    # Green
TEXT_COLOR = "#2c3e50"    # Dark blue-gray

# --- Tkinter setup ---
root = Tk()
root.geometry("600x650") 
root.title("Voting System")
root.configure(bg=BG_COLOR)

# Custom fonts
title_font = tkfont.Font(family="Helvetica", size=18, weight="bold")
label_font = tkfont.Font(family="Helvetica", size=12)
button_font = tkfont.Font(family="Helvetica", size=10, weight="bold")

# --- Global variable for the status bar label ---
status_bar_label = None

# --- Global flag to control balloon animation ---
_last_election_state_for_balloons = None 

def clear_window():
    """Clears all widgets from the root window, except the status bar."""
    global status_bar_label
    # Destroy all widgets except the status_bar_label if it exists
    for widget in root.winfo_children():
        if widget is not status_bar_label:
            widget.destroy()
    root.configure(bg=BG_COLOR)

def fade_in(widget, duration=300):
    """Gradually fades in a widget."""
    widget.attributes('-alpha', 0)
    widget.update()
    
    for i in range(0, 101, 5):
        alpha = i/100
        widget.attributes('-alpha', alpha)
        widget.update()
        time.sleep(duration/1000/20)

def create_button(parent, text, command, width=20, bg_override=None, activebg_override=None):
    """Creates a styled button with hover effects and optional color overrides."""
    btn_bg = bg_override if bg_override else BUTTON_COLOR
    btn_activebg = activebg_override if activebg_override else HOVER_COLOR

    btn = Button(parent, text=text, command=command, 
                 bg=btn_bg, fg=FG_COLOR, 
                 activebackground=btn_activebg, activeforeground=FG_COLOR,
                 font=button_font, width=width, relief="raised", bd=2)
    
    def on_enter(e):
        e.widget['background'] = btn_activebg
    def on_leave(e):
        e.widget['background'] = btn_bg
    
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    
    return btn

def create_entry(parent, show=None):
    """Creates a styled entry widget."""
    entry = Entry(parent, show=show, bg=FG_COLOR, fg=TEXT_COLOR, 
                  font=label_font, relief="solid", bd=2)
    return entry

def create_label(parent, text, font=None):
    """Creates a styled label widget."""
    if font is None:
        font = label_font
    return Label(parent, text=text, bg=BG_COLOR, fg=FG_COLOR, font=font)

def animate_label(label, colors, duration=500):
    """Animates a label's foreground color."""
    def change_color(index=0):
        if label.winfo_exists():
            label.config(fg=colors[index])
            root.after(duration, change_color, (index + 1) % len(colors))
    change_color()

# --- Election State Management Functions ---
def get_election_state():
    cursor.execute("SELECT status, start_time, end_time FROM election_state WHERE id=1")
    return cursor.fetchone()

def set_election_status(new_status):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_msg = ""
    
    if new_status == 'Active':
        cursor.execute("UPDATE election_state SET status=?, start_time=?, end_time=NULL WHERE id=1", (new_status, current_time))
        status_msg = "Election has started and is now Active!"
    elif new_status == 'Closed':
        cursor.execute("UPDATE election_state SET status=?, end_time=? WHERE id=1", (new_status, current_time))
        status_msg = "Election has ended and is now Closed!"
    elif new_status == 'Pending':
        cursor.execute("UPDATE election_state SET status=?, start_time=NULL, end_time=NULL WHERE id=1", (new_status,))
        status_msg = "Election has been set to Pending!"
    
    conn.commit()
    messagebox.showinfo("Election Status", status_msg)
    update_status_bar() # Update the status bar immediately after changing status
    # If the user is currently on the admin dashboard, refresh it to reflect the change
    if root.winfo_children() and isinstance(root.winfo_children()[-1], Frame) and \
       any(widget.cget("text") == "Admin Dashboard" for widget in root.winfo_children() if isinstance(widget, Label)):
        admin_dashboard() 

# --- NEW: Function to create and update the persistent status bar ---
def update_status_bar():
    """Updates the content and color of the global status bar label."""
    global status_bar_label
    
    # Create the label if it doesn't exist
    if status_bar_label is None or not status_bar_label.winfo_exists():
        status_bar_label = Label(root, text="", anchor="w", font=("Helvetica", 10, "bold"), padx=10, pady=5)
        # --- CORRECTED LINE BELOW: Removed 'before' argument for initial pack ---
        status_bar_label.pack(side="top", fill="x") 
        
    election_status, start_time, end_time = get_election_state()
    
    status_text = f"Election Status: {election_status}"
    status_color = FG_COLOR # Default color
    status_bg = "#34495e" # Darker background for status bar

    if election_status == 'Active':
        status_text += f" (Started: {start_time})"
        status_color = SUCCESS_COLOR
    elif election_status == 'Closed':
        status_text += f" (Ended: {end_time})"
        status_color = ERROR_COLOR
    else: # Pending
        status_color = ACCENT_COLOR
        status_text += " (Admin must start the election)" # Hint for admin
    
    status_bar_label.config(text=status_text, fg=status_color, bg=status_bg)
    status_bar_label.lift() # Ensure it's always on top

# --- Admin Registration ---
def admin_register_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Admin Registration", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Username").pack()
    username_entry = create_entry(frame)
    username_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)

    def register():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please fill all fields")
            return
        cursor.execute("SELECT * FROM admin WHERE username=?", (username,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Username already exists")
        else:
            cursor.execute("INSERT INTO admin (username, password) VALUES (?, ?)", (username, password))
            conn.commit()
            messagebox.showinfo("Success", "Admin registered successfully!")
            admin_login_screen()

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Register", register).pack(pady=5)
    create_button(btn_frame, "Back to Login", admin_login_screen).pack(pady=5)

# --- Admin Login ---
def admin_login_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Admin Login", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Username").pack()
    username_entry = create_entry(frame)
    username_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)

    def login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        cursor.execute("SELECT * FROM admin WHERE username=? AND password=?", (username, password))
        if cursor.fetchone():
            welcome_label = create_label(root, f"Welcome, {username}!", title_font)
            welcome_label.pack(pady=20)
            animate_label(welcome_label, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR])
            root.after(1500, admin_dashboard)
        else:
            error_label = create_label(root, "Invalid admin credentials", label_font)
            error_label.pack(pady=10)
            error_label.config(fg=ERROR_COLOR)
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None)

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Admin", admin_register_screen).pack(pady=5)
    create_button(root, "Back to Main Menu", main_menu).pack(pady=10)

# --- Voter Registration ---
def voter_register_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Voter Registration", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Username").pack()
    username_entry = create_entry(frame)
    username_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)
    
    create_label(frame, "Birth Year (YYYY)").pack()
    birth_year_entry = create_entry(frame)
    birth_year_entry.pack(pady=5)

    def register():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        birth_year = birth_year_entry.get().strip()
        if not username or not password or not birth_year:
            messagebox.showerror("Error", "Please fill all fields")
            return
        try:
            birth_year_int = int(birth_year)
            current_year = datetime.datetime.now().year # Dynamically get current year
            age = current_year - birth_year_int
            if age < 18:
                messagebox.showerror("Error", "You must be at least 18 years old to register")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid birth year. Please enter a 4-digit year.")
            return
        
        cursor.execute("SELECT * FROM voters WHERE username=?", (username,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Username already exists")
        else:
            cursor.execute("INSERT INTO voters (username, password, birth_year) VALUES (?, ?, ?)",
                           (username, password, birth_year_int))
            conn.commit()
            
            success_label = create_label(root, "Voter registered successfully!", label_font)
            success_label.pack(pady=10)
            success_label.config(fg=SUCCESS_COLOR)
            root.after(1500, voter_login_screen)

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Register", register).pack(pady=5)
    create_button(btn_frame, "Back to Voter Login", voter_login_screen).pack(pady=5)

# --- Voter Login ---
def voter_login_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Voter Login", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Username").pack()
    username_entry = create_entry(frame)
    username_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)

    def login():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        cursor.execute("SELECT voted FROM voters WHERE username=? AND password=?", (username, password))
        result = cursor.fetchone()
        if result is None:
            error_label = create_label(root, "Invalid credentials", label_font)
            error_label.pack(pady=10)
            error_label.config(fg=ERROR_COLOR)
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None)
        else:
            voted = result[0]
            welcome_label = create_label(root, f"Welcome, {username}!", title_font)
            welcome_label.pack(pady=20)
            animate_label(welcome_label, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR])
            root.after(1500, lambda: voter_dashboard(username, voted))

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Voter", voter_register_screen).pack(pady=5)
    create_button(root, "Back to Main Menu", main_menu).pack(pady=10)

# --- Candidate Registration ---
def candidate_register_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Candidate Registration", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Party Name").pack()
    party_entry = create_entry(frame)
    party_entry.pack(pady=5)
    
    create_label(frame, "Leader Name").pack()
    leader_entry = create_entry(frame)
    leader_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)

    def register():
        party = party_entry.get().strip()
        leader = leader_entry.get().strip()
        password = password_entry.get().strip()
        if not party or not leader or not password:
            messagebox.showerror("Error", "Please fill all fields")
            return
        cursor.execute("SELECT * FROM candidates WHERE party_name=?", (party,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Party already exists")
        else:
            cursor.execute("INSERT INTO candidates (party_name, leader_name, password) VALUES (?, ?, ?)",
                           (party, leader, password))
            conn.commit()
            
            success_label = create_label(root, "Candidate registered successfully!", title_font)
            success_label.pack(pady=20)
            animate_label(success_label, [SUCCESS_COLOR, HOVER_COLOR, ACCENT_COLOR])
            root.after(1500, candidate_login_screen)

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Register", register).pack(pady=5)
    create_button(btn_frame, "Back to Candidate Login", candidate_login_screen).pack(pady=5)

# --- Candidate Login ---
def candidate_login_screen():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Candidate Login", title_font)
    title.pack(pady=20)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    create_label(frame, "Party Name").pack()
    party_entry = create_entry(frame)
    party_entry.pack(pady=5)
    
    create_label(frame, "Password").pack()
    password_entry = create_entry(frame, show="*")
    password_entry.pack(pady=5)

    def login():
        party = party_entry.get().strip()
        password = password_entry.get().strip()
        cursor.execute("SELECT * FROM candidates WHERE party_name=? AND password=?", (party, password))
        if cursor.fetchone():
            welcome_label = create_label(root, f"Welcome, {party}!", title_font)
            welcome_label.pack(pady=20)
            animate_label(welcome_label, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR])
            root.after(1500, main_menu) # Candidates don't have a specific dashboard, so back to main menu
        else:
            error_label = create_label(root, "Invalid credentials", label_font)
            error_label.pack(pady=10)
            error_label.config(fg=ERROR_COLOR)
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None)

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Candidate", candidate_register_screen).pack(pady=5)
    create_button(root, "Back to Main Menu", main_menu).pack(pady=10)

# --- Voting screen ---
def voter_dashboard(username, voted):
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, f"Voter: {username}", title_font)
    title.pack(pady=20)
    
    election_status, start_time, end_time = get_election_state()
    
    # --- Enhanced Voter Dashboard Messages based on Election Status ---
    if election_status == 'Pending':
        create_label(root, "Election has not started yet.", label_font).pack(pady=5)
        create_label(root, "Please wait for the Admin to start the election.", label_font).pack(pady=5)
        create_button(root, "Logout", main_menu).pack(pady=20)
        return
    elif election_status == 'Closed':
        create_label(root, "The election has ended. No more votes can be cast.", label_font).pack(pady=5)
        if end_time:
            create_label(root, f"Election ended on: {end_time}", label_font).pack(pady=5)
        create_button(root, "Logout", main_menu).pack(pady=20)
        return
    
    # Only proceed if election_status is 'Active'
    if voted:
        create_label(root, "You have already voted.", label_font).pack()
        create_button(root, "Logout", main_menu).pack(pady=20)
        return

    cursor.execute("SELECT party_name, leader_name FROM candidates")
    candidates = cursor.fetchall()
    if not candidates:
        create_label(root, "No candidates available yet.", label_font).pack()
        create_button(root, "Logout", main_menu).pack(pady=20)
        return

    selected_party = StringVar()
    # Check if there are candidates before setting a default selection
    if candidates:
        selected_party.set(candidates[0][0]) # Set a default selection
    else:
        # Handle case where no candidates exist
        create_label(root, "No candidates registered to vote for.", label_font).pack(pady=10)
        create_button(root, "Logout", main_menu).pack(pady=20)
        return # Exit the function if no candidates

    create_label(root, "Select a Candidate to Vote:", label_font).pack(pady=10)
    
    frame = Frame(root, bg=BG_COLOR)
    frame.pack(pady=10)
    
    for party, leader in candidates:
        rb = Radiobutton(frame, text=f"{party} - Leader: {leader}", 
                         variable=selected_party, value=party,
                         bg=BG_COLOR, fg=FG_COLOR, selectcolor=BG_COLOR,
                         activebackground=BG_COLOR, activeforeground=HOVER_COLOR,
                         font=label_font)
        rb.pack(anchor="w", pady=2)

    def submit_vote():
        party = selected_party.get()
        # Double-check if already voted for safety AND election status
        election_status_check, _, _ = get_election_state()
        if election_status_check != 'Active':
             messagebox.showerror("Error", "Voting is no longer active.")
             voter_dashboard(username, True) # Force refresh to reflect new status
             return

        cursor.execute("SELECT voted FROM voters WHERE username=?", (username,))
        if cursor.fetchone()[0]:
            messagebox.showerror("Error", "You have already voted.")
            voter_dashboard(username, True)
            return

        cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE party_name=?", (party,))
        cursor.execute("UPDATE voters SET voted=1 WHERE username=?", (username,))
        conn.commit()
        
        success_frame = Frame(root, bg=BG_COLOR)
        success_frame.pack(pady=20)
        
        # Simple animation for vote submission
        for i in range(1, 4):
            dots = "." * i
            success_label = create_label(success_frame, f"Voting for {party}{dots}", label_font)
            success_label.pack()
            root.update()
            time.sleep(0.3)
            if success_label.winfo_exists():
                success_label.destroy()
        
        final_label = create_label(success_frame, f"You voted for {party}!", label_font)
        final_label.pack()
        final_label.config(fg=SUCCESS_COLOR)
        root.after(1500, lambda: voter_dashboard(username, True))

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Submit Vote", submit_vote).pack(pady=5)
    create_button(btn_frame, "Logout", main_menu).pack(pady=5)

def view_voters():
    top = Toplevel(root)
    top.title("Voter List")
    top.geometry("600x400") 
    top.configure(bg=BG_COLOR)
    
    style = ttk.Style()
    style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR)
    style.configure("Treeview.Heading", background=BUTTON_COLOR, foreground=FG_COLOR, font=button_font)
    style.map("Treeview", background=[('selected', HOVER_COLOR)])
    
    tree = ttk.Treeview(top, columns=("Username", "Password", "Birth Year", "Voted"), show='headings')
    tree.heading("Username", text="Username")
    tree.heading("Password", text="Password")
    tree.heading("Birth Year", text="Birth Year")
    tree.heading("Voted", text="Voted")
    
    tree.column("Username", width=150, anchor="center")
    tree.column("Password", width=150, anchor="center")
    tree.column("Birth Year", width=100, anchor="center")
    tree.column("Voted", width=80, anchor="center")
    
    tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

    cursor.execute("SELECT username, password, birth_year, voted FROM voters")
    for row in cursor.fetchall():
        tree.insert("", END, values=row)
    
    create_button(top, "Back", top.destroy, width=15).pack(pady=10)

def view_candidates():
    top = Toplevel(root)
    top.title("Candidates List")
    top.geometry("600x400")
    top.configure(bg=BG_COLOR)
    
    style = ttk.Style()
    style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR)
    style.configure("Treeview.Heading", background=BUTTON_COLOR, foreground=FG_COLOR, font=button_font)
    style.map("Treeview", background=[('selected', HOVER_COLOR)])
    
    tree = ttk.Treeview(top, columns=("Party Name", "Leader Name", "Password", "Votes"), show='headings')
    tree.heading("Party Name", text="Party Name")
    tree.heading("Leader Name", text="Leader Name")
    tree.heading("Password", text="Password")
    tree.heading("Votes", text="Votes")

    tree.column("Party Name", width=150, anchor="center")
    tree.column("Leader Name", width=150, anchor="center")
    tree.column("Password", width=100, anchor="center")
    tree.column("Votes", width=80, anchor="center")
    
    tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

    cursor.execute("SELECT party_name, leader_name, password, votes FROM candidates")
    for row in cursor.fetchall():
        tree.insert("", END, values=row)
    
    create_button(top, "Back", top.destroy, width=15).pack(pady=10)

# --- NEW: Balloon Animation Function ---
def launch_balloons(winner_name):
    """Creates a Toplevel window with animated balloons."""
    global _last_election_state_for_balloons
    
    # Safety check: Don't launch if the results window isn't even open or the flag prevents it
    if not results_top_window or not results_top_window.winfo_exists() or _last_election_state_for_balloons == 'Closed_Winner_Launched':
        return

    _last_election_state_for_balloons = 'Closed_Winner_Launched' # Set flag to indicate balloons launched

    balloon_window = Toplevel(root)
    balloon_window.title("Celebration!")
    # Make it slightly transparent and always on top
    balloon_window.attributes('-alpha', 0.8)
    balloon_window.attributes('-topmost', True) # Keep it above other windows
    
    # Position and size relative to the results window
    if results_top_window and results_top_window.winfo_exists():
        balloon_window.geometry(f"{results_top_window.winfo_width()}x{results_top_window.winfo_height()}+{results_top_window.winfo_x()}+{results_top_window.winfo_y()}")
    else: # Fallback to root window if results window not available (shouldn't happen with current call logic)
         root.update_idletasks() # Ensure root geometry is calculated
         balloon_window.geometry(f"{root.winfo_width()}x{root.winfo_height()}+{root.winfo_x()}+{root.winfo_y()}")

    balloon_window.overrideredirect(True) # Remove window decorations for a cleaner look

    canvas = Canvas(balloon_window, bg='SystemTransparent', highlightthickness=0) 
    # Attempt to make background truly transparent (OS dependent)
    try:
        canvas.attributes('-transparentcolor', canvas.cget('bg')) # Make 'SystemTransparent' color transparent
    except TclError:
        # Fallback if transparentcolor is not supported (e.g., some Linux/older Tk)
        canvas.config(bg=BG_COLOR) # Use a solid, matching background
    canvas.pack(fill=BOTH, expand=True)

    # Need to update canvas dimensions after packing for accurate random positions
    canvas.update_idletasks() 
    canvas_width = canvas.winfo_width()
    canvas_height = canvas.winfo_height()

    balloons = []
    num_balloons = 25 # Number of balloons
    balloon_colors = ["#ff6b6b", "#4ecdc4", "#45b7d1", "#feca57", "#ff9ff3", "#0be881", "#ff00e8", "#00d4ff"] # Vibrant colors

    for _ in range(num_balloons):
        x_start = random.randint(0, canvas_width - 50) # Initial x-position, leaving space for size
        y_start = canvas_height + random.randint(50, 150) # Start below the screen
        size = random.randint(25, 50) # Balloon size
        color = random.choice(balloon_colors)

        # Draw balloon body
        balloon_body = canvas.create_oval(x_start, y_start, x_start + size, y_start + size, fill=color, outline=color)
        
        # Draw balloon string
        string_x = x_start + size / 2
        string_y1 = y_start + size - 5 # Start string slightly inside balloon
        string_y2 = y_start + size + 10
        balloon_string = canvas.create_line(string_x, string_y1, string_x, string_y2, fill="gray", width=1)
        
        balloons.append({"body": balloon_body, "string": balloon_string, "y_speed": random.uniform(1.5, 4)}) # Speed

    def animate_balloons():
        if not balloon_window.winfo_exists():
            return # Stop animation if window is closed

        # Iterate over a copy of the list because we might remove items
        for balloon in list(balloons): 
            canvas.move(balloon["body"], 0, -balloon["y_speed"])
            canvas.move(balloon["string"], 0, -balloon["y_speed"])
            
            x1, y1, x2, y2 = canvas.coords(balloon["body"])
            if y2 < -50: # If balloon goes well off screen
                canvas.delete(balloon["body"])
                canvas.delete(balloon["string"])
                balloons.remove(balloon)

        if balloons:
            root.after(50, animate_balloons) # Continue animation every 50ms
        else:
            balloon_window.destroy() # Destroy window when all balloons are gone

    animate_balloons() # Start the animation
    # Set a general timeout for the balloon window to ensure it eventually closes
    root.after(10000, lambda: balloon_window.destroy() if balloon_window.winfo_exists() else None) # Close after 10 seconds

# --- Live Result Update Logic ---
results_canvas_widget = None
results_toolbar_frame = None
results_top_window = None # To hold a reference to the Toplevel window

def update_results_display(top_window, text_results_frame, canvas_widget, toolbar_frame, fig, ax):
    """
    Refreshes the text-based results and the matplotlib graph.
    This function will be called periodically.
    """
    global results_top_window, _last_election_state_for_balloons
    results_top_window = top_window # Ensure this is always the current Toplevel

    if not top_window.winfo_exists():
        plt.close(fig)
        return

    for widget in text_results_frame.winfo_children():
        widget.destroy()

    cursor.execute("SELECT party_name, votes FROM candidates")
    results = cursor.fetchall()

    create_label(text_results_frame, "Current Vote Counts (Live Update):", label_font).pack()
    
    total_votes = sum(votes for _, votes in results)
    
    current_election_status, _, _ = get_election_state() # Get current status
    
    if not results or total_votes == 0:
        create_label(text_results_frame, "No votes cast yet or no candidates.", label_font).pack(pady=5)
        ax.clear()
        ax.set_title("No Votes / No Candidates", color='white')
        canvas_widget.draw()
        
        # Reset balloon flag if election is not closed or no votes
        if current_election_status != 'Closed' or total_votes == 0:
            _last_election_state_for_balloons = None 
        
        top_window.after(3000, update_results_display, top_window, text_results_frame, canvas_widget, toolbar_frame, fig, ax)
        return

    max_votes = -1
    if results:
        max_votes = max(votes for _, votes in results)
    
    winners = []
    for party, votes in results:
        percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
        party_label = create_label(text_results_frame, f"{party}: {votes} votes ({percentage:.2f}%)", label_font)
        party_label.pack(anchor="w")
        if votes == max_votes and max_votes > 0:
            party_label.config(fg=SUCCESS_COLOR)
            winners.append(party)

    if winners:
        if len(winners) == 1:
            winner_text = f"Winner: {winners[0]} with {max_votes} votes!"
            # --- BALLOON LOGIC START ---
            if current_election_status == 'Closed' and _last_election_state_for_balloons != 'Closed_Winner_Launched':
                launch_balloons(winners[0])
                # _last_election_state_for_balloons is set inside launch_balloons
            # --- BALLOON LOGIC END ---
        else: # It's a tie
            winner_text = f"Tie between: {', '.join(winners)} with {max_votes} votes!"
            # Reset balloon flag if it's a tie, to prevent launching balloons for ties
            if current_election_status == 'Closed':
                _last_election_state_for_balloons = 'Closed_Tie' 
    
        winner_label = create_label(text_results_frame, winner_text, title_font)
        winner_label.pack(pady=10)
        animate_label(winner_label, [SUCCESS_COLOR, HOVER_COLOR, ACCENT_COLOR])
    else: # No clear winner (e.g., all votes are 0 and no max_votes > 0)
        create_label(text_results_frame, "No clear winner yet.", title_font).pack(pady=10)
        # Reset balloon flag if no clear winner
        if current_election_status == 'Closed':
            _last_election_state_for_balloons = 'Closed_NoWinner'

    # Reset balloon flag if election is active or pending
    if current_election_status == 'Active' or current_election_status == 'Pending':
        _last_election_state_for_balloons = current_election_status

    # --- Update Matplotlib Graph ---
    parties = [result[0] for result in results]
    votes = [result[1] for result in results]

    ax.clear()

    bars = ax.bar(parties, votes, color=ACCENT_COLOR)
    
    for bar in bars:
        yval = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, round(yval), ha='center', va='bottom', fontsize=9, color='white')

    ax.set_xlabel("Parties", color='white')
    ax.set_ylabel("Votes", color='white')
    ax.set_title("Live Election Results", color='white', fontsize=14)
    ax.tick_params(axis='x', colors='white')
    ax.tick_params(axis='y', colors='white')
    ax.set_facecolor(BG_COLOR)
    fig.patch.set_facecolor(BG_COLOR)
    ax.spines['bottom'].set_color('white')
    ax.spines['top'].set_color('white')
    ax.spines['right'].set_color('white')
    ax.spines['left'].set_color('white')

    plt.tight_layout()
    canvas_widget.draw()

    top_window.after(3000, update_results_display, top_window, text_results_frame, canvas_widget, toolbar_frame, fig, ax)

def show_results():
    global results_canvas_widget, results_toolbar_frame, results_top_window, _last_election_state_for_balloons

    top = Toplevel(root)
    results_top_window = top 
    top.title("Election Results")
    top.geometry("700x750") 
    top.configure(bg=BG_COLOR)
    
    text_results_frame = Frame(top, bg=BG_COLOR)
    text_results_frame.pack(pady=10, fill=X)

    fig, ax = plt.subplots(figsize=(6, 4), dpi=100) 
    
    canvas = FigureCanvasTkAgg(fig, master=top)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(side=TOP, fill=BOTH, expand=True, padx=10, pady=10)

    toolbar_frame = Frame(top, bg=BG_COLOR)
    toolbar_frame.pack(side=TOP, fill=X, padx=10)
    toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
    toolbar.update()
    
    update_results_display(top, text_results_frame, canvas_widget, toolbar_frame, fig, ax)

    # Use a lambda to ensure plt.close(fig) is called when the Toplevel window is closed
    top.protocol("WM_DELETE_WINDOW", lambda: [top.destroy(), plt.close(fig)])
    create_button(top, "Back", lambda: [top.destroy(), plt.close(fig)], width=15).pack(pady=10)


def reset_votes():
    confirm = messagebox.askyesno("Confirm Reset", "Are you sure you want to reset ALL votes? This action cannot be undone.")
    if confirm:
        try:
            cursor.execute("UPDATE candidates SET votes = 0")
            cursor.execute("UPDATE voters SET voted = 0")
            cursor.execute("UPDATE election_state SET status='Pending', start_time=NULL, end_time=NULL WHERE id=1")
            conn.commit()
            
            reset_label = create_label(root, "All votes have been reset and election set to Pending!", label_font)
            reset_label.pack(pady=10)
            reset_label.config(fg=SUCCESS_COLOR)
            root.after(2000, lambda: reset_label.destroy() if reset_label.winfo_exists() else None)
            update_status_bar() # Update the status bar immediately after reset
            admin_dashboard() # Refresh admin dashboard
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reset votes: {e}")

def remove_all_voters():
    confirm = messagebox.askyesno("Confirm Deletion",
                                  "Are you sure you want to remove ALL voter data? This action cannot be undone.")
    if confirm:
        try:
            cursor.execute("DELETE FROM voters")
            conn.commit()
            messagebox.showinfo("Success", "All voter data has been removed!")
            admin_dashboard()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove voter data: {e}")

def remove_all_candidates(): 
    confirm = messagebox.askyesno("Confirm Deletion",
                                  "Are you sure you want to remove ALL candidate data? This action cannot be undone.")
    if confirm:
        try:
            cursor.execute("DELETE FROM candidates")
            conn.commit()
            messagebox.showinfo("Success", "All candidate data has been removed!")
            admin_dashboard()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove candidate data: {e}")

def remove_specific_voter():
    top = Toplevel(root)
    top.title("Remove Specific Voter")
    top.geometry("400x200")
    top.configure(bg=BG_COLOR)

    create_label(top, "Enter Voter Username to Remove:", label_font).pack(pady=10)
    voter_username_entry = create_entry(top)
    voter_username_entry.pack(pady=5)

    def confirm_remove():
        username_to_remove = voter_username_entry.get().strip()
        if not username_to_remove:
            messagebox.showerror("Error", "Please enter a username.", parent=top)
            return

        cursor.execute("SELECT username FROM voters WHERE username=?", (username_to_remove,))
        if cursor.fetchone() is None:
            messagebox.showerror("Error", f"Voter '{username_to_remove}' not found.", parent=top)
            return

        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to remove voter '{username_to_remove}'? This cannot be undone.", parent=top)
        if confirm:
            try:
                cursor.execute("DELETE FROM voters WHERE username=?", (username_to_remove,))
                conn.commit()
                messagebox.showinfo("Success", f"Voter '{username_to_remove}' removed successfully!", parent=top)
                top.destroy()
                admin_dashboard()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove voter: {e}", parent=top)

    create_button(top, "Remove Voter", confirm_remove, width=15, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(pady=10)
    create_button(top, "Cancel", top.destroy, width=15).pack(pady=5)

def remove_specific_candidate():
    top = Toplevel(root)
    top.title("Remove Specific Candidate")
    top.geometry("400x200")
    top.configure(bg=BG_COLOR)

    create_label(top, "Enter Candidate Party Name to Remove:", label_font).pack(pady=10)
    candidate_party_entry = create_entry(top)
    candidate_party_entry.pack(pady=5)

    def confirm_remove():
        party_to_remove = candidate_party_entry.get().strip()
        if not party_to_remove:
            messagebox.showerror("Error", "Please enter a party name.", parent=top)
            return

        cursor.execute("SELECT party_name FROM candidates WHERE party_name=?", (party_to_remove,))
        if cursor.fetchone() is None:
            messagebox.showerror("Error", f"Candidate party '{party_to_remove}' not found.", parent=top)
            return

        confirm = messagebox.askyesno("Confirm Deletion",
                                      f"Are you sure you want to remove candidate party '{party_to_remove}'? This cannot be undone.", parent=top)
        if confirm:
            try:
                cursor.execute("DELETE FROM candidates WHERE party_name=?", (party_to_remove,))
                conn.commit()
                messagebox.showinfo("Success", f"Candidate '{party_to_remove}' removed successfully!", parent=top)
                top.destroy()
                admin_dashboard()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove candidate: {e}", parent=top)

    create_button(top, "Remove Candidate", confirm_remove, width=15, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(pady=10)
    create_button(top, "Cancel", top.destroy, width=15).pack(pady=5)

def view_all_credentials():
    top = Toplevel(root)
    top.title("All User Credentials")
    top.geometry("700x500")
    top.configure(bg=BG_COLOR)
    
    style = ttk.Style()
    style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR)
    style.configure("Treeview.Heading", background=BUTTON_COLOR, foreground=FG_COLOR, font=button_font)
    style.map("Treeview", background=[('selected', HOVER_COLOR)])
    
    notebook = ttk.Notebook(top)
    notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
    
    admin_frame = Frame(notebook, bg=BG_COLOR)
    notebook.add(admin_frame, text="Admins")
    admin_tree = ttk.Treeview(admin_frame, columns=("Username", "Password"), show='headings')
    admin_tree.heading("Username", text="Username")
    admin_tree.heading("Password", text="Password")
    admin_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
    cursor.execute("SELECT username, password FROM admin")
    for row in cursor.fetchall():
        admin_tree.insert("", END, values=row)
    
    voter_frame = Frame(notebook, bg=BG_COLOR)
    notebook.add(voter_frame, text="Voters")
    voter_tree = ttk.Treeview(voter_frame, columns=("Username", "Password", "Birth Year"), show='headings')
    voter_tree.heading("Username", text="Username")
    voter_tree.heading("Password", text="Password")
    voter_tree.heading("Birth Year", text="Birth Year")
    voter_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
    cursor.execute("SELECT username, password, birth_year FROM voters")
    for row in cursor.fetchall():
        voter_tree.insert("", END, values=row)
    
    candidate_frame = Frame(notebook, bg=BG_COLOR)
    notebook.add(candidate_frame, text="Candidates")
    candidate_tree = ttk.Treeview(candidate_frame, columns=("Party", "Leader", "Password"), show='headings')
    candidate_tree.heading("Party", text="Party")
    candidate_tree.heading("Leader", text="Leader")
    candidate_tree.heading("Password", text="Password")
    candidate_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
    cursor.execute("SELECT party_name, leader_name, password FROM candidates")
    for row in cursor.fetchall():
        candidate_tree.insert("", END, values=row)
    
    create_button(top, "Back", top.destroy, width=15).pack(pady=10)

# --- Admin Dashboard (Main Function) ---
def admin_dashboard():
    clear_window()
    update_status_bar() # Update status bar on this screen

    title = create_label(root, "Admin Dashboard", title_font)
    title.pack(pady=20)

    # --- Display Current Election Status ---
    election_status, start_time, end_time = get_election_state()
    status_text_display = f"Current Election Status: {election_status}"
    if start_time:
        status_text_display += f" (Started: {start_time})"
    if end_time:
        status_text_display += f" (Ended: {end_time})"

    status_label_dashboard = create_label(root, status_text_display, label_font)
    status_label_dashboard.pack(pady=5)
    if election_status == 'Active':
        status_label_dashboard.config(fg=SUCCESS_COLOR)
    elif election_status == 'Pending':
        status_label_dashboard.config(fg=ACCENT_COLOR)
    else: # Closed
        status_label_dashboard.config(fg=ERROR_COLOR)


    main_frame = Frame(root, bg=BG_COLOR)
    main_frame.pack(pady=20)
    
    # --- Election Control Buttons ---
    frame_election_control = Frame(main_frame, bg=BG_COLOR)
    frame_election_control.pack(pady=10)
    
    create_button(frame_election_control, "Start Election", lambda: set_election_status('Active'), 
                  width=25, bg_override=SUCCESS_COLOR, activebg_override="#27ae60").pack(side=LEFT, padx=5)
    create_button(frame_election_control, "End Election", lambda: set_election_status('Closed'), 
                  width=25, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(side=LEFT, padx=5)
    
    create_button(frame_election_control, "Reset Election to Pending", lambda: set_election_status('Pending'),
                  width=35, bg_override="#f39c12", activebg_override="#e67e22").pack(pady=5)


    # View Data Buttons
    frame_view = Frame(main_frame, bg=BG_COLOR)
    frame_view.pack(pady=5)
    create_button(frame_view, "View Voters", view_voters, width=25).pack(side=LEFT, padx=5)
    create_button(frame_view, "View Candidates", view_candidates, width=25).pack(side=LEFT, padx=5)
    
    # Results & All Credentials
    frame_info = Frame(main_frame, bg=BG_COLOR)
    frame_info.pack(pady=5)
    create_button(frame_info, "Show Results", show_results, width=25).pack(side=LEFT, padx=5)
    create_button(frame_info, "View All Credentials", view_all_credentials, width=25).pack(side=LEFT, padx=5)

    # Reset All & Remove All Data Buttons (Warning Colors)
    frame_reset_remove_all = Frame(main_frame, bg=BG_COLOR)
    frame_reset_remove_all.pack(pady=15)
    create_button(frame_reset_remove_all, "Reset All Votes", reset_votes, width=25, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(side=LEFT, padx=5)
    create_button(frame_reset_remove_all, "Remove All Voters", remove_all_voters, width=25, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(side=LEFT, padx=5)
    
    frame_remove_all_cand = Frame(main_frame, bg=BG_COLOR)
    frame_remove_all_cand.pack(pady=5)
    create_button(frame_remove_all_cand, "Remove All Candidates", remove_all_candidates, width=25, bg_override=ERROR_COLOR, activebg_override="#c0392b").pack(side=TOP, padx=5)

    # Remove Specific Data Buttons (Orange Color for "specific" removals)
    frame_remove_specific = Frame(main_frame, bg=BG_COLOR)
    frame_remove_specific.pack(pady=15)
    create_button(frame_remove_specific, "Remove Specific Voter", remove_specific_voter, width=25, bg_override="#e67e22", activebg_override="#d35400").pack(side=LEFT, padx=5)
    create_button(frame_remove_specific, "Remove Specific Candidate", remove_specific_candidate, width=25, bg_override="#e67e22", activebg_override="#d35400").pack(side=LEFT, padx=5)

    # Logout Button
    create_button(root, "Logout", main_menu, width=25).pack(pady=20)


# --- Main Menu ---
def main_menu():
    clear_window()
    update_status_bar() # Update status bar on this screen
    title = create_label(root, "Welcome to Voting System", title_font)
    title.pack(pady=30)
    
    animate_label(title, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR, FG_COLOR])
    
    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Admin Login", admin_login_screen, width=25).pack(pady=10)
    create_button(btn_frame, "Voter Login", voter_login_screen, width=25).pack(pady=10)
    create_button(btn_frame, "Candidate Login", candidate_login_screen, width=25).pack(pady=10)
    
    exit_btn = create_button(root, "Exit", root.destroy, width=25, bg_override=ERROR_COLOR, activebg_override="#c0392b")
    exit_btn.pack(pady=20)

# Start with fade in effect
root.attributes('-alpha', 0)
root.update()
fade_in(root)

# Initial call to set up the status bar and display the main menu
update_status_bar()
main_menu()
root.mainloop()

conn.close()
