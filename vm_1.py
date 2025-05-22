import sqlite3
from tkinter import *
from tkinter import messagebox, ttk
import time
from tkinter import font as tkfont
import datetime
import random
import string

# --- Import matplotlib for graphing ---
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Set Matplotlib backend explicitly for better Tkinter integration
# 'TkAgg' is generally the recommended backend for Tkinter.
try:
    plt.switch_backend('TkAgg')
except ImportError:
    messagebox.showerror("Error", "TkAgg backend for Matplotlib not found. Please ensure it's installed or check your Matplotlib configuration.")
    # Fallback or exit if essential


# --- Database setup ---
conn = sqlite3.connect("voting.db")
cursor = conn.cursor()

# Create tables if they don't exist
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS election_state (
    id INTEGER PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'Pending', -- 'Pending', 'Active', 'Closed'
    start_time TEXT,
    end_time TEXT
)""")

# --- Database Schema Migration: Add results_released column if it doesn't exist ---
try:
    cursor.execute("SELECT results_released FROM election_state LIMIT 1")
except sqlite3.OperationalError:
    # Column does not exist, add it
    cursor.execute("ALTER TABLE election_state ADD COLUMN results_released INTEGER DEFAULT 0")
    conn.commit()
    print("Added 'results_released' column to 'election_state' table.")

# --- Ensure there's always one row in election_state ---
# If the table is empty, insert the default row.
# Otherwise, we assume the row already exists.
cursor.execute("INSERT OR IGNORE INTO election_state (id, status, results_released) VALUES (1, 'Pending', 0)")
conn.commit()


# --- Color Scheme ---
BG_COLOR = "#2c3e50"     # Dark blue-gray
FG_COLOR = "#ecf0f1"     # Light gray
ACCENT_COLOR = "#3498db" # Bright blue
BUTTON_COLOR = "#2980b9" # Slightly darker blue
HOVER_COLOR = "#1abc9c"  # Teal
ERROR_COLOR = "#e74c3c"  # Red
SUCCESS_COLOR = "#2ecc71" # Green
TEXT_COLOR = "#2c3e50"   # Dark blue-gray

# --- Tkinter setup ---
root = Tk()
root.geometry("800x700") # Increased size for better layout
root.title("Advanced Voting System")
root.configure(bg=BG_COLOR)

# Custom fonts
title_font = tkfont.Font(family="Helvetica", size=20, weight="bold")
subtitle_font = tkfont.Font(family="Helvetica", size=14, weight="bold")
label_font = tkfont.Font(family="Helvetica", size=12)
button_font = tkfont.Font(family="Helvetica", size=11, weight="bold")
status_font = tkfont.Font(family="Helvetica", size=10, weight="bold")

# --- Global variable for the status bar label ---
status_bar_label = None

# --- Global flag to control balloon animation ---
_last_election_state_for_balloons = None

# --- Global reference for results window (for balloon animation) ---
results_top_window = None

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
    try:
        # Check if the widget exists before trying to configure its attributes
        if not widget.winfo_exists():
            return

        widget.attributes('-alpha', 0)
        widget.update_idletasks() # Use update_idletasks for smoother animation updates

        for i in range(0, 101, 5):
            if not widget.winfo_exists(): # Check again within the loop
                return
            alpha = i/100
            widget.attributes('-alpha', alpha)
            widget.update_idletasks()
            time.sleep(duration/1000/20)
    except TclError:
        # Widget might have been destroyed before animation completes
        pass

def create_button(parent, text, command, width=20, bg_override=None, activebg_override=None, font_override=None):
    """Creates a styled button with hover effects and optional color overrides."""
    btn_bg = bg_override if bg_override else BUTTON_COLOR
    btn_activebg = activebg_override if activebg_override else HOVER_COLOR
    btn_font = font_override if font_override else button_font

    btn = Button(parent, text=text, command=command,
                 bg=btn_bg, fg=FG_COLOR,
                 activebackground=btn_activebg, activeforeground=FG_COLOR,
                 font=btn_font, width=width, relief="raised", bd=2)

    def on_enter(e):
        if e.widget['state'] == NORMAL: # Only change color if button is active
            e.widget['background'] = btn_activebg
    def on_leave(e):
        if e.widget['state'] == NORMAL: # Only change color if button is active
            e.widget['background'] = btn_bg

    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)

    return btn

def create_entry(parent, show=None, width=30):
    """Creates a styled entry widget."""
    entry = Entry(parent, show=show, bg=FG_COLOR, fg=TEXT_COLOR,
                  font=label_font, relief="solid", bd=2, width=width)
    return entry

def create_label(parent, text, font=None, fg=FG_COLOR, bg=BG_COLOR):
    """Creates a styled label widget."""
    if font is None:
        font = label_font
    return Label(parent, text=text, bg=bg, fg=fg, font=font)

def animate_label(label, colors, duration=500):
    """Animates a label's foreground color."""
    def change_color(index=0):
        if label.winfo_exists(): # Check if label still exists
            label.config(fg=colors[index])
            # Use root.after for recurring animations
            root.after(duration, change_color, (index + 1) % len(colors))
    change_color()

# --- Election State Management Functions ---
def get_election_state():
    """Retrieves current election status, start and end times, and results released status."""
    cursor.execute("SELECT status, start_time, end_time, results_released FROM election_state WHERE id=1")
    return cursor.fetchone()

def set_election_status(new_status, start_time=None, end_time=None):
    """
    Sets the election status and updates start/end times.
    start_time and end_time should be datetime objects or None.
    """
    current_time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_msg = ""

    if new_status == 'Active':
        start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else current_time_str
        cursor.execute("UPDATE election_state SET status=?, start_time=?, end_time=NULL, results_released=0 WHERE id=1", (new_status, start_time_str))
        status_msg = "Election has started and is now Active!"
    elif new_status == 'Closed':
        end_time_str = end_time.strftime("%Y-%m-%d %H:%M:%S") if end_time else current_time_str
        cursor.execute("UPDATE election_state SET status=?, end_time=? WHERE id=1", (new_status, end_time_str))
        status_msg = "Election has ended and is now Closed!"
    elif new_status == 'Pending':
        cursor.execute("UPDATE election_state SET status=?, start_time=NULL, end_time=NULL, results_released=0 WHERE id=1", (new_status,))
        status_msg = "Election has been set to Pending!"

    conn.commit()
    messagebox.showinfo("Election Status", status_msg)
    update_status_bar() # Update the status bar immediately after changing status
    # If the user is currently on the admin dashboard, refresh it to reflect the change
    if admin_dashboard_visible():
        admin_dashboard()

def admin_dashboard_visible():
    """Checks if the admin dashboard is currently displayed."""
    # A more robust check might involve checking for a specific frame or a unique label
    # that only appears on the admin dashboard.
    for widget in root.winfo_children():
        if isinstance(widget, Label) and widget.cget("text") == "Admin Dashboard":
            return True
    return False

def update_status_bar():
    """Updates the content and color of the global status bar label."""
    global status_bar_label

    if status_bar_label is None or not status_bar_label.winfo_exists():
        status_bar_label = Label(root, text="", anchor="w", font=status_font, padx=10, pady=5)
        status_bar_label.pack(side="top", fill="x")

    election_status, start_time, end_time, results_released = get_election_state()

    status_text = f"Election Status: {election_status}"
    status_color = FG_COLOR
    status_bg = "#34495e"

    if election_status == 'Active':
        status_text += f" (Started: {start_time or 'N/A'})" # Handle potential None for start_time
        status_color = SUCCESS_COLOR
    elif election_status == 'Closed':
        status_text += f" (Ended: {end_time or 'N/A'})" # Handle potential None for end_time
        status_color = ERROR_COLOR
    else: # Pending
        status_color = ACCENT_COLOR
        status_text += " (Admin must start the election)"
    
    if results_released:
        status_text += " | Results: Released"
    else:
        status_text += " | Results: Not Released"

    status_bar_label.config(text=status_text, fg=status_color, bg=status_bg)
    status_bar_label.lift()

# --- Admin Registration ---
def admin_register_screen():
    clear_window()
    update_status_bar()
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
    update_status_bar()
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
            # Clear previous error label if it exists
            for widget in root.winfo_children():
                if isinstance(widget, Label) and "Invalid" in widget.cget("text"):
                    widget.destroy()

            # Ensure the welcome_label is created in the current clear_window context
            welcome_label = create_label(root, f"Welcome, {username}!", title_font)
            welcome_label.pack(pady=20)
            animate_label(welcome_label, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR])
            root.after(1500, admin_dashboard)
        else:
            error_label = create_label(root, "Invalid admin credentials", label_font, fg=ERROR_COLOR)
            error_label.pack(pady=10)
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None)
    
    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)

    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Admin", admin_register_screen).pack(pady=5)
    create_button(root, "Back to Main Menu", main_menu).pack(pady=10)

# --- Admin Dashboard ---
def admin_dashboard():
    clear_window()
    update_status_bar()
    title = create_label(root, "Admin Dashboard", title_font)
    title.pack(pady=20)

    # Frame for organizing buttons
    button_frame = Frame(root, bg=BG_COLOR)
    button_frame.pack(pady=20)

    create_button(button_frame, "Manage Voters", manage_users_page, width=25).pack(pady=10)
    create_button(button_frame, "Manage Candidates", manage_candidates_page, width=25).pack(pady=10)
    create_button(button_frame, "Manage Elections", manage_election_page, width=25).pack(pady=10)
    create_button(button_frame, "View Live Results", lambda: display_results(True), width=25).pack(pady=10)
    create_button(button_frame, "Logout", main_menu, width=25, bg_override=ERROR_COLOR).pack(pady=10)

# --- Admin: Manage Voters Page ---
def manage_users_page():
    clear_window()
    update_status_bar()
    create_label(root, "Manage Voters", title_font).pack(pady=20)

    # Frame for input fields
    input_frame = Frame(root, bg=BG_COLOR)
    input_frame.pack(pady=10)

    create_label(input_frame, "Username:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    username_entry = create_entry(input_frame)
    username_entry.grid(row=0, column=1, padx=5, pady=5)

    create_label(input_frame, "Password:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    password_entry = create_entry(input_frame, show="*")
    password_entry.grid(row=1, column=1, padx=5, pady=5)

    create_label(input_frame, "Birth Year:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    birth_year_entry = create_entry(input_frame)
    birth_year_entry.grid(row=2, column=1, padx=5, pady=5)

    # Treeview for displaying voters
    style = ttk.Style()
    style.theme_use("clam") # A modern theme
    style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR, font=label_font)
    style.configure("Treeview.Heading", background=ACCENT_COLOR, foreground="white", font=button_font)
    style.map("Treeview", background=[('selected', HOVER_COLOR)])

    tree_frame = Frame(root, bg=BG_COLOR)
    tree_frame.pack(pady=10, fill="both", expand=True, padx=20)

    tree = ttk.Treeview(tree_frame, columns=("Username", "Password", "Birth Year", "Voted"), show='headings')
    tree.heading("Username", text="Username")
    tree.heading("Password", text="Password")
    tree.heading("Birth Year", text="Birth Year")
    tree.heading("Voted", text="Voted")

    tree.column("Username", width=150, anchor="center")
    tree.column("Password", width=150, anchor="center")
    tree.column("Birth Year", width=100, anchor="center")
    tree.column("Voted", width=80, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    def load_voters():
        for item in tree.get_children():
            tree.delete(item)
        cursor.execute("SELECT username, password, birth_year, voted FROM voters")
        for row in cursor.fetchall():
            tree.insert("", END, values=row)

    def add_voter():
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        birth_year = birth_year_entry.get().strip()
        if not username or not password or not birth_year:
            messagebox.showerror("Error", "Please fill all fields for voter.")
            return
        try:
            birth_year_int = int(birth_year)
            if len(str(birth_year_int)) != 4: # Ensure 4 digits after conversion
                messagebox.showerror("Error", "Birth year must be a 4-digit number.")
                return
            current_year = datetime.datetime.now().year
            if current_year - birth_year_int < 18:
                messagebox.showerror("Error", "Voter must be at least 18 years old.")
                return
            if birth_year_int > current_year:
                messagebox.showerror("Error", "Birth year cannot be in the future.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid birth year. Please enter a 4-digit number.")
            return

        try:
            cursor.execute("INSERT INTO voters (username, password, birth_year) VALUES (?, ?, ?)",
                           (username, password, birth_year_int))
            conn.commit()
            messagebox.showinfo("Success", "Voter added successfully!")
            load_voters()
            username_entry.delete(0, END)
            password_entry.delete(0, END)
            birth_year_entry.delete(0, END)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists.")

    def update_voter():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a voter to update.")
            return

        old_username = tree.item(selected_item)['values'][0]
        username = username_entry.get().strip()
        password = password_entry.get().strip()
        birth_year = birth_year_entry.get().strip()

        if not username or not password or not birth_year:
            messagebox.showerror("Error", "Please fill all fields to update.")
            return

        try:
            birth_year_int = int(birth_year)
            if len(str(birth_year_int)) != 4:
                messagebox.showerror("Error", "Birth year must be a 4-digit number.")
                return
            current_year = datetime.datetime.now().year
            if current_year - birth_year_int < 18:
                messagebox.showerror("Error", "Voter must be at least 18 years old.")
                return
            if birth_year_int > current_year:
                messagebox.showerror("Error", "Birth year cannot be in the future.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid birth year. Please enter a 4-digit number.")
            return

        try:
            # Check if the new username already exists and is not the old username
            if username != old_username:
                cursor.execute("SELECT * FROM voters WHERE username=?", (username,))
                if cursor.fetchone():
                    messagebox.showerror("Error", "New username already exists.")
                    return

            cursor.execute("UPDATE voters SET username=?, password=?, birth_year=? WHERE username=?",
                           (username, password, birth_year_int, old_username))
            conn.commit()
            messagebox.showinfo("Success", "Voter updated successfully!")
            load_voters()
        except sqlite3.IntegrityError:
            # This should ideally be caught by the explicit check above, but as a fallback
            messagebox.showerror("Error", "Database error during update. New username might conflict.")

    def delete_voter():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a voter to delete.")
            return

        username = tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete voter: {username}?"):
            cursor.execute("DELETE FROM voters WHERE username=?", (username,))
            conn.commit()
            messagebox.showinfo("Success", "Voter deleted successfully!")
            load_voters()
            # Clear input fields after deletion
            username_entry.delete(0, END)
            password_entry.delete(0, END)
            birth_year_entry.delete(0, END)

    def select_voter_item(event):
        selected_item = tree.focus()
        if selected_item:
            values = tree.item(selected_item)['values']
            username_entry.delete(0, END)
            username_entry.insert(0, values[0])
            password_entry.delete(0, END)
            password_entry.insert(0, values[1])
            birth_year_entry.delete(0, END)
            birth_year_entry.insert(0, values[2])

    tree.bind("<<TreeviewSelect>>", select_voter_item)

    # Button frame for actions
    action_btn_frame = Frame(root, bg=BG_COLOR)
    action_btn_frame.pack(pady=10)

    create_button(action_btn_frame, "Add Voter", add_voter, width=15).grid(row=0, column=0, padx=5)
    create_button(action_btn_frame, "Update Voter", update_voter, width=15).grid(row=0, column=1, padx=5)
    create_button(action_btn_frame, "Delete Voter", delete_voter, width=15, bg_override=ERROR_COLOR).grid(row=0, column=2, padx=5)

    create_button(root, "Back to Admin Dashboard", admin_dashboard, width=25).pack(pady=10)

    load_voters() # Load initial data

# --- Admin: Manage Candidates Page ---
def manage_candidates_page():
    clear_window()
    update_status_bar()
    create_label(root, "Manage Candidates", title_font).pack(pady=20)

    # Frame for input fields
    input_frame = Frame(root, bg=BG_COLOR)
    input_frame.pack(pady=10)

    create_label(input_frame, "Party Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
    party_entry = create_entry(input_frame)
    party_entry.grid(row=0, column=1, padx=5, pady=5)

    create_label(input_frame, "Leader Name:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
    leader_entry = create_entry(input_frame)
    leader_entry.grid(row=1, column=1, padx=5, pady=5)

    create_label(input_frame, "Password:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
    password_entry = create_entry(input_frame, show="*")
    password_entry.grid(row=2, column=1, padx=5, pady=5)

    # Treeview for displaying candidates
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR, font=label_font)
    style.configure("Treeview.Heading", background=ACCENT_COLOR, foreground="white", font=button_font)
    style.map("Treeview", background=[('selected', HOVER_COLOR)])

    tree_frame = Frame(root, bg=BG_COLOR)
    tree_frame.pack(pady=10, fill="both", expand=True, padx=20)

    tree = ttk.Treeview(tree_frame, columns=("Party Name", "Leader Name", "Password", "Votes"), show='headings')
    tree.heading("Party Name", text="Party Name")
    tree.heading("Leader Name", text="Leader Name")
    tree.heading("Password", text="Password")
    tree.heading("Votes", text="Votes")

    tree.column("Party Name", width=150, anchor="center")
    tree.column("Leader Name", width=150, anchor="center")
    tree.column("Password", width=100, anchor="center")
    tree.column("Votes", width=80, anchor="center")

    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    def load_candidates():
        for item in tree.get_children():
            tree.delete(item)
        cursor.execute("SELECT party_name, leader_name, password, votes FROM candidates")
        for row in cursor.fetchall():
            tree.insert("", END, values=row)

    def add_candidate():
        party = party_entry.get().strip()
        leader = leader_entry.get().strip()
        password = password_entry.get().strip()
        if not party or not leader or not password:
            messagebox.showerror("Error", "Please fill all fields for candidate.")
            return

        try:
            cursor.execute("INSERT INTO candidates (party_name, leader_name, password) VALUES (?, ?, ?)",
                           (party, leader, password))
            conn.commit()
            messagebox.showinfo("Success", "Candidate added successfully!")
            load_candidates()
            party_entry.delete(0, END)
            leader_entry.delete(0, END)
            password_entry.delete(0, END)
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Party name already exists.")

    def update_candidate():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a candidate to update.")
            return

        old_party_name = tree.item(selected_item)['values'][0]
        party = party_entry.get().strip()
        leader = leader_entry.get().strip()
        password = password_entry.get().strip()

        if not party or not leader or not password:
            messagebox.showerror("Error", "Please fill all fields to update.")
            return

        try:
            # Check if the new party name already exists and is not the old party name
            if party != old_party_name:
                cursor.execute("SELECT * FROM candidates WHERE party_name=?", (party,))
                if cursor.fetchone():
                    messagebox.showerror("Error", "New party name already exists.")
                    return

            cursor.execute("UPDATE candidates SET party_name=?, leader_name=?, password=? WHERE party_name=?",
                           (party, leader, password, old_party_name))
            conn.commit()
            messagebox.showinfo("Success", "Candidate updated successfully!")
            load_candidates()
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Database error during update. New party name might conflict.")

    def delete_candidate():
        selected_item = tree.focus()
        if not selected_item:
            messagebox.showerror("Error", "Please select a candidate to delete.")
            return

        party = tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete candidate: {party}?"):
            cursor.execute("DELETE FROM candidates WHERE party_name=?", (party,))
            conn.commit()
            messagebox.showinfo("Success", "Candidate deleted successfully!")
            load_candidates()
            # Clear input fields after deletion
            party_entry.delete(0, END)
            leader_entry.delete(0, END)
            password_entry.delete(0, END)

    def select_candidate_item(event):
        selected_item = tree.focus()
        if selected_item:
            values = tree.item(selected_item)['values']
            party_entry.delete(0, END)
            party_entry.insert(0, values[0])
            leader_entry.delete(0, END)
            leader_entry.insert(0, values[1])
            password_entry.delete(0, END)
            password_entry.insert(0, values[2])

    tree.bind("<<TreeviewSelect>>", select_candidate_item)

    # Button frame for actions
    action_btn_frame = Frame(root, bg=BG_COLOR)
    action_btn_frame.pack(pady=10)

    create_button(action_btn_frame, "Add Candidate", add_candidate, width=15).grid(row=0, column=0, padx=5)
    create_button(action_btn_frame, "Update Candidate", update_candidate, width=15).grid(row=0, column=1, padx=5)
    create_button(action_btn_frame, "Delete Candidate", delete_candidate, width=15, bg_override=ERROR_COLOR).grid(row=0, column=2, padx=5)

    create_button(root, "Back to Admin Dashboard", admin_dashboard, width=25).pack(pady=10)

    load_candidates() # Load initial data

# --- Admin: Manage Election Page ---
def manage_election_page():
    clear_window()
    update_status_bar()
    create_label(root, "Manage Elections", title_font).pack(pady=20)

    current_status, start_time_str, end_time_str, results_released_status = get_election_state()

    status_frame = Frame(root, bg=BG_COLOR)
    status_frame.pack(pady=10)

    create_label(status_frame, f"Current Election Status: ", subtitle_font).grid(row=0, column=0, padx=5, pady=5, sticky="w")
    status_label = create_label(status_frame, current_status, subtitle_font, fg=ACCENT_COLOR)
    status_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")

    if start_time_str:
        create_label(status_frame, f"Start Time: {start_time_str}", label_font).grid(row=1, column=0, columnspan=2, sticky="w", padx=5)
    if end_time_str:
        create_label(status_frame, f"End Time: {end_time_str}", label_font).grid(row=2, column=0, columnspan=2, sticky="w", padx=5)
    
    # Results released status
    results_status_text = "Released" if results_released_status else "Not Released"
    results_status_color = SUCCESS_COLOR if results_released_status else ERROR_COLOR
    create_label(status_frame, f"Results Status: ", label_font).grid(row=3, column=0, padx=5, pady=5, sticky="w")
    create_label(status_frame, results_status_text, label_font, fg=results_status_color).grid(row=3, column=1, padx=5, pady=5, sticky="w")


    # Date and Time input for setting election period
    datetime_frame = Frame(root, bg=BG_COLOR, bd=2, relief="groove", padx=10, pady=10)
    datetime_frame.pack(pady=20)

    create_label(datetime_frame, "Set Election Period (Optional for Active/Closed):", subtitle_font).grid(row=0, column=0, columnspan=4, pady=10)

    create_label(datetime_frame, "Start Date (YYYY-MM-DD):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
    start_date_entry = create_entry(datetime_frame, width=20)
    start_date_entry.grid(row=1, column=1, padx=5, pady=2, sticky="w")

    create_label(datetime_frame, "Start Time (HH:MM:SS):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
    start_time_entry = create_entry(datetime_frame, width=20)
    start_time_entry.grid(row=2, column=1, padx=5, pady=2, sticky="w")

    create_label(datetime_frame, "End Date (YYYY-MM-DD):").grid(row=1, column=2, padx=5, pady=2, sticky="w")
    end_date_entry = create_entry(datetime_frame, width=20)
    end_date_entry.grid(row=1, column=3, padx=5, pady=2, sticky="w")

    create_label(datetime_frame, "End Time (HH:MM:SS):").grid(row=2, column=2, padx=5, pady=2, sticky="w")
    end_time_entry = create_entry(datetime_frame, width=20)
    end_time_entry.grid(row=2, column=3, padx=5, pady=2, sticky="w")

    def validate_datetime(date_str, time_str):
        if not date_str and not time_str:
            return None # Allow empty for optional fields
        if not date_str or not time_str:
            messagebox.showerror("Error", "Both date and time must be provided if setting a period.")
            return False
        try:
            dt_str = f"{date_str} {time_str}"
            return datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            messagebox.showerror("Error", "Invalid date or time format. Use YYYY-MM-DD and HH:MM:SS.")
            return False

    def start_election_action():
        start_dt = validate_datetime(start_date_entry.get().strip(), start_time_entry.get().strip())
        if start_dt is False: return

        if start_dt and start_dt < datetime.datetime.now():
            if not messagebox.askyesno("Warning", "Start time is in the past. Continuing will start the election immediately. Continue?"):
                return

        set_election_status('Active', start_time=start_dt)
        # manage_election_page() # Refresh page is handled by set_election_status

    def end_election_action():
        end_dt = validate_datetime(end_date_entry.get().strip(), end_time_entry.get().strip())
        if end_dt is False: return

        # Ensure that an election was actually started before closing it
        current_status, _, _, _ = get_election_state()
        if current_status == 'Pending':
            messagebox.showerror("Error", "Election has not been started yet. Cannot close.")
            return
        
        if end_dt and end_dt < datetime.datetime.now():
            if not messagebox.askyesno("Warning", "End time is in the past. Continuing will close the election immediately. Continue?"):
                return

        set_election_status('Closed', end_time=end_dt)
        # manage_election_page() # Refresh page is handled by set_election_status

    def reset_election_action():
        if messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the election? This will clear all votes and set status to Pending."):
            cursor.execute("UPDATE election_state SET status='Pending', start_time=NULL, end_time=NULL, results_released=0 WHERE id=1")
            cursor.execute("UPDATE candidates SET votes=0")
            cursor.execute("UPDATE voters SET voted=0")
            conn.commit()
            messagebox.showinfo("Success", "Election reset to Pending. All votes cleared.")
            manage_election_page() # Refresh page

    def release_results_action():
        current_status, _, _, results_released_val = get_election_state()
        if current_status != 'Closed':
            messagebox.showerror("Error", "Results can only be released when the election is Closed.")
            return
        if results_released_val == 1:
            messagebox.showinfo("Info", "Results are already released.")
            return

        if messagebox.askyesno("Confirm Release", "Are you sure you want to release the election results?"):
            cursor.execute("UPDATE election_state SET results_released=1 WHERE id=1")
            conn.commit()
            messagebox.showinfo("Success", "Election results have been released!")
            update_status_bar()
            manage_election_page() # Refresh page

    action_btn_frame = Frame(root, bg=BG_COLOR)
    action_btn_frame.pack(pady=20)

    create_button(action_btn_frame, "Start Election", start_election_action, width=20, bg_override=SUCCESS_COLOR).grid(row=0, column=0, padx=5)
    create_button(action_btn_frame, "End Election", end_election_action, width=20, bg_override=ERROR_COLOR).grid(row=0, column=1, padx=5)
    create_button(action_btn_frame, "Reset Election", reset_election_action, width=20, bg_override=BUTTON_COLOR).grid(row=0, column=2, padx=5)
    
    # New button for releasing results
    release_btn = create_button(action_btn_frame, "Release Results", release_results_action, width=20, bg_override="#8e44ad") # Purple color
    release_btn.grid(row=1, column=1, padx=5, pady=10)
    if results_released_status == 1:
        release_btn.config(state=DISABLED, text="Results Released")


    create_button(root, "Back to Admin Dashboard", admin_dashboard, width=25).pack(pady=20)

# --- Voter Registration ---
def voter_register_screen():
    clear_window()
    update_status_bar()
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
            if len(str(birth_year_int)) != 4: # Ensure 4 digits after conversion
                messagebox.showerror("Error", "Birth year must be a 4-digit number.")
                return
            current_year = datetime.datetime.now().year
            age = current_year - birth_year_int
            if age < 18:
                messagebox.showerror("Error", "You must be at least 18 years old to register.")
                return
            if birth_year_int > current_year:
                messagebox.showerror("Error", "Birth year cannot be in the future.")
                return
        except ValueError:
            messagebox.showerror("Error", "Invalid birth year. Please enter a 4-digit year.")
            return

        cursor.execute("SELECT * FROM voters WHERE username=?", (username,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Username already exists.")
        else:
            cursor.execute("INSERT INTO voters (username, password, birth_year) VALUES (?, ?, ?)",
                           (username, password, birth_year_int))
            conn.commit()

            success_label = create_label(root, "Voter registered successfully!", label_font, fg=SUCCESS_COLOR)
            success_label.pack(pady=10)
            root.after(1500, voter_login_screen)

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)

    create_button(btn_frame, "Register", register).pack(pady=5)
    create_button(btn_frame, "Back to Voter Login", voter_login_screen).pack(pady=5)

# --- Voter Login ---
def voter_login_screen():
    clear_window()
    update_status_bar()
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
        cursor.execute("SELECT * FROM voters WHERE username=? AND password=?", (username, password))
        voter_data = cursor.fetchone()

        if voter_data:
            # Clear previous error label if it exists
            for widget in root.winfo_children():
                if isinstance(widget, Label) and "Invalid" in widget.cget("text"):
                    widget.destroy()

            # Ensure welcome_label is created in the current clear_window context
            welcome_label = create_label(root, f"Welcome, {username}!", title_font)
            welcome_label.pack(pady=20)
            animate_label(welcome_label, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR])
            root.after(1500, lambda: voter_dashboard(username))
        else:
            error_label = create_label(root, "Invalid voter credentials", label_font, fg=ERROR_COLOR)
            error_label.pack(pady=10)
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None)
    
    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)

    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Voter", voter_register_screen).pack(pady=5)
    create_button(root, "Back to Main Menu", main_menu).pack(pady=10)

# --- Voter Dashboard ---
def voter_dashboard(username):
    clear_window()
    update_status_bar()
    create_label(root, f"Voter Dashboard - {username}", title_font).pack(pady=20)

    election_status, _, _, results_released = get_election_state()
    
    # Check if voter has already voted
    cursor.execute("SELECT voted FROM voters WHERE username=?", (username,))
    has_voted = cursor.fetchone()
    has_voted = has_voted[0] if has_voted else 0 # Default to 0 if voter_data somehow None

    status_label = create_label(root, f"Election is currently: {election_status}", subtitle_font)
    status_label.pack(pady=10)

    if election_status == 'Active' and not has_voted:
        create_button(root, "Cast Your Vote", lambda: cast_vote_screen(username)).pack(pady=10)
    elif has_voted:
        create_label(root, "You have already voted in this election. Thank you!", label_font, fg=ACCENT_COLOR).pack(pady=10)
    elif election_status == 'Closed':
        create_label(root, "The election has concluded. Voting is no longer possible.", label_font, fg=ERROR_COLOR).pack(pady=10)
        # REMOVED: create_button(root, "View Election Results", lambda: display_results(False)).pack(pady=10)
        # As per the requirement, voters cannot view results.
    else: # Pending
        create_label(root, "The election has not started yet. Please check back later.", label_font, fg=ERROR_COLOR).pack(pady=10)

    create_button(root, "Logout", main_menu).pack(pady=20)

# --- Voter: Cast Vote Screen ---
def cast_vote_screen(username):
    clear_window()
    update_status_bar()
    create_label(root, "Cast Your Vote", title_font).pack(pady=20)

    election_status, _, _, _ = get_election_state()
    if election_status != 'Active':
        messagebox.showerror("Election Status", "Voting is not currently active.")
        voter_dashboard(username)
        return
    
    cursor.execute("SELECT voted FROM voters WHERE username=?", (username,))
    voted_status = cursor.fetchone()
    if voted_status and voted_status[0] == 1:
        messagebox.showinfo("Already Voted", "You have already cast your vote.")
        voter_dashboard(username)
        return

    cursor.execute("SELECT party_name, leader_name FROM candidates")
    candidates = cursor.fetchall()

    if not candidates:
        create_label(root, "No candidates available for voting. Please contact the Admin.", label_font, fg=ERROR_COLOR).pack(pady=20)
        create_button(root, "Back to Dashboard", lambda: voter_dashboard(username)).pack(pady=10)
        return

    selected_candidate = StringVar(root)
    # Filter out "Select a candidate" if it's not a real candidate
    candidate_options = [f"{c[0]} ({c[1]})" for c in candidates]
    
    # Initialize with a placeholder that's not a real candidate
    placeholder_text = "Select a candidate"
    selected_candidate.set(placeholder_text) 
    
    # Prepend placeholder to options for OptionMenu if it's not already there
    if placeholder_text not in candidate_options:
        candidate_options.insert(0, placeholder_text)

    option_menu = ttk.OptionMenu(root, selected_candidate, selected_candidate.get(), *candidate_options)
    option_menu.config(width=40)
    option_menu.pack(pady=20)

    def submit_vote():
        chosen_option = selected_candidate.get()
        if chosen_option == placeholder_text:
            messagebox.showerror("Error", "Please select a candidate to vote for.")
            return
        
        # Extract party name from the chosen option
        party_name = chosen_option.split(" (")[0] # Assuming format "Party Name (Leader Name)"

        if messagebox.askyesno("Confirm Vote", f"Are you sure you want to vote for {party_name}? You cannot change your vote later."):
            cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE party_name=?", (party_name,))
            cursor.execute("UPDATE voters SET voted = 1 WHERE username=?", (username,))
            conn.commit()
            messagebox.showinfo("Vote Cast", f"Your vote for {party_name} has been recorded. Thank you for voting!")
            voter_dashboard(username)

    create_button(root, "Submit Vote", submit_vote).pack(pady=10)
    create_button(root, "Back to Dashboard", lambda: voter_dashboard(username)).pack(pady=10)

# --- Results Display ---
def display_results(is_admin_view):
    global results_top_window, _last_election_state_for_balloons
    
    election_status, _, _, results_released = get_election_state()

    # Crucial check: If not admin view and results are not released, prevent display
    if not is_admin_view and not results_released:
        messagebox.showinfo("Access Denied", "Election results are not publicly available at this time.")
        # Do not proceed with creating the results window
        return

    # Close any existing results window to prevent multiple instances
    if results_top_window and results_top_window.winfo_exists():
        results_top_window.destroy()
        results_top_window = None

    results_top_window = Toplevel(root)
    results_top_window.title("Election Results")
    results_top_window.geometry("700x600")
    results_top_window.configure(bg=BG_COLOR)
    results_top_window.transient(root) # Make it appear on top of the root window
    results_top_window.grab_set()      # Make it modal (user must interact with this window)

    # Override close button to release grab
    results_top_window.protocol("WM_DELETE_WINDOW", lambda: close_results_window(results_top_window))


    create_label(results_top_window, "Election Results", title_font).pack(pady=15)

    cursor.execute("SELECT party_name, votes FROM candidates ORDER BY votes DESC")
    all_results = cursor.fetchall()

    if not all_results:
        create_label(results_top_window, "No candidates or votes recorded yet.", label_font, fg=FG_COLOR).pack(pady=20)
        create_button(results_top_window, "Close", lambda: close_results_window(results_top_window)).pack(pady=10)
        return # Exit function, grab_release is handled by close_results_window

    total_votes = sum(vote for _, vote in all_results)

    if total_votes == 0:
        create_label(results_top_window, "No votes have been cast yet.", label_font, fg=FG_COLOR).pack(pady=20)
        create_button(results_top_window, "Close", lambda: close_results_window(results_top_window)).pack(pady=10)
        return # Exit function, grab_release is handled by close_results_window

    # Determine the winner(s)
    max_votes = 0
    winners = []
    if all_results:
        max_votes = all_results[0][1] # Since results are ordered descending, first element has max votes
        for party, votes in all_results:
            if votes == max_votes:
                winners.append(party)
            else:
                break # Since results are sorted descending, no need to check further

    # Display results table
    results_table_frame = Frame(results_top_window, bg=BG_COLOR)
    results_table_frame.pack(pady=10, padx=20, fill="x")

    create_label(results_table_frame, "Party Name", font=subtitle_font, bg=BG_COLOR, fg=ACCENT_COLOR).grid(row=0, column=0, padx=5, pady=2)
    create_label(results_table_frame, "Votes", font=subtitle_font, bg=BG_COLOR, fg=ACCENT_COLOR).grid(row=0, column=1, padx=5, pady=2)
    create_label(results_table_frame, "Percentage", font=subtitle_font, bg=BG_COLOR, fg=ACCENT_COLOR).grid(row=0, column=2, padx=5, pady=2)

    row_num = 1
    for party, votes in all_results:
        percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
        fg_color = SUCCESS_COLOR if party in winners and len(winners) == 1 else FG_COLOR
        if party in winners and len(winners) > 1: # Tie
            fg_color = HOVER_COLOR

        create_label(results_table_frame, party, font=label_font, bg=BG_COLOR, fg=fg_color).grid(row=row_num, column=0, padx=5, pady=1, sticky="w")
        create_label(results_table_frame, str(votes), font=label_font, bg=BG_COLOR, fg=fg_color).grid(row=row_num, column=1, padx=5, pady=1, sticky="e")
        create_label(results_table_frame, f"{percentage:.2f}%", font=label_font, bg=BG_COLOR, fg=fg_color).grid(row=row_num, column=2, padx=5, pady=1, sticky="e")
        row_num += 1

    # Winner Announcement and Animation (only if results are released for voters, or always for admin)
    # The condition `results_released or is_admin_view` is crucial here.
    # For a voter (not admin), `results_released` must be True.
    # For an admin, it can be True or False (they see live results).
    if results_released or is_admin_view:
        winner_text = ""
        winner_color = SUCCESS_COLOR
        if len(winners) == 1:
            winner_text = f"WINNER: {winners[0]} with {max_votes} votes!"
        elif len(winners) > 1:
            winner_text = f"IT'S A TIE! Winners: {', '.join(winners)} with {max_votes} votes each!"
            winner_color = HOVER_COLOR
        else: # No votes at all
            winner_text = "No winner determined yet (no votes)."
            winner_color = ACCENT_COLOR # A neutral color

        winner_label = create_label(results_top_window, winner_text, title_font, fg=winner_color)
        winner_label.pack(pady=20)
        animate_label(winner_label, [winner_color, FG_COLOR, winner_color]) # Simple pulse animation

        # Conditionally trigger balloon animation only when results are newly released and for admin
        # or if the election state changes to closed/results released for general view.
        current_election_state_tuple = get_election_state() # Get as tuple for comparison
        global _last_election_state_for_balloons
        
        # Trigger balloons if results are released AND we haven't shown them for THIS state before
        # OR if it's an admin live view and there are winners, and the state hasn't been shown
        if (results_released and _last_election_state_for_balloons != current_election_state_tuple) or \
           (is_admin_view and len(winners) > 0 and _last_election_state_for_balloons != current_election_state_tuple):
            
            _last_election_state_for_balloons = current_election_state_tuple
            if len(winners) > 0: # Only show balloons if there's at least one winner
                start_balloon_animation(results_top_window)


    # Matplotlib Graph
    if all_results and total_votes > 0: # Only create graph if there are votes
        parties = [res[0] for res in all_results]
        votes = [res[1] for res in all_results]

        # Clear previous plot to prevent memory leaks if opening results multiple times
        plt.close('all')
        fig, ax = plt.subplots(figsize=(6, 4), facecolor=BG_COLOR)
        
        # Assign colors to bars
        bar_colors = [SUCCESS_COLOR if p in winners and len(winners) == 1 else HOVER_COLOR if p in winners else ACCENT_COLOR for p in parties]
        ax.bar(parties, votes, color=bar_colors)

        ax.set_xlabel("Parties", color=FG_COLOR, fontdict={'fontsize': 10, 'fontweight': 'bold'})
        ax.set_ylabel("Votes", color=FG_COLOR, fontdict={'fontsize': 10, 'fontweight': 'bold'})
        ax.set_title("Election Results", color=FG_COLOR, fontdict={'fontsize': 14, 'fontweight': 'bold'})
        ax.tick_params(axis='x', colors=FG_COLOR, rotation=45, ha='right', labelsize=9)
        ax.tick_params(axis='y', colors=FG_COLOR, labelsize=9)
        ax.set_facecolor(BG_COLOR)
        fig.tight_layout() # Adjust layout to prevent labels from overlapping

        canvas = FigureCanvasTkAgg(fig, master=results_top_window)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(pady=10)

        # Optional: Add toolbar for matplotlib interactivity (zoom, pan, etc.)
        toolbar = NavigationToolbar2Tk(canvas, results_top_window)
        toolbar.update()
        canvas_widget.pack(side=TOP, fill=BOTH, expand=1)

    create_button(results_top_window, "Close", lambda: close_results_window(results_top_window)).pack(pady=20)
    # The grab_release is handled by close_results_window now

def close_results_window(window):
    """Helper function to close the results window and release grab."""
    global results_top_window
    if window.winfo_exists():
        window.grab_release()
        window.destroy()
    results_top_window = None # Clear global reference

# --- Balloon Animation (for winner display) ---
def start_balloon_animation(parent_window):
    # Ensure canvas is created only once per results window to avoid layering issues
    if not hasattr(parent_window, '_balloon_canvas'):
        canvas = Canvas(parent_window, width=parent_window.winfo_width(), height=200, bg=BG_COLOR, highlightthickness=0)
        canvas.pack(side=BOTTOM, fill=X)
        canvas.lower() # Place it behind other widgets initially
        parent_window._balloon_canvas = canvas # Store reference on the parent window

    canvas = parent_window._balloon_canvas
    # Clear existing balloons if any from previous animations
    canvas.delete("all")

    balloons = []
    colors = ["red", "blue", "green", "purple", "orange", "yellow", "cyan", "magenta"]
    max_balloons = 15 # A few more balloons for better effect

    for _ in range(max_balloons):
        x = random.randint(50, canvas.winfo_width() - 50) if canvas.winfo_width() > 100 else 50
        y = canvas.winfo_height() + random.randint(50, 200) # Start below the visible canvas area
        color = random.choice(colors)
        
        # Balloon oval coordinates
        oval_radius = random.randint(10, 20)
        oval_coords = (x - oval_radius, y - oval_radius * 2, x + oval_radius, y)
        balloon_id = canvas.create_oval(oval_coords, fill=color, outline=color, width=2)
        
        # String (line) coordinates
        line_length = random.randint(30, 50)
        line_id = canvas.create_line(x, y, x, y + line_length, fill="gray", width=2)
        balloons.append({'oval': balloon_id, 'line': line_id, 'speed': random.randint(2, 5)})

    def move_balloons():
        if not parent_window.winfo_exists() or not canvas.winfo_exists():
            return # Stop animation if window or canvas is closed

        for balloon in balloons:
            # Move balloon elements
            canvas.move(balloon['oval'], 0, -balloon['speed'])
            canvas.move(balloon['line'], 0, -balloon['speed'])
            
            x1, y1, x2, y2 = canvas.coords(balloon['oval'])
            # If balloon goes off-screen top, reset its position to bottom
            if y2 < -50: # Slightly off-screen for a smoother loop
                new_x = random.randint(50, canvas.winfo_width() - 50) if canvas.winfo_width() > 100 else 50
                new_y = canvas.winfo_height() + random.randint(50, 200)
                # Recalculate oval and line positions based on new_x, new_y, and existing radius/length
                oval_radius = (x2 - x1) / 2
                line_length = canvas.coords(balloon['line'])[3] - canvas.coords(balloon['line'])[1] # Get current line length
                
                canvas.coords(balloon['oval'], new_x - oval_radius, new_y - oval_radius * 2, new_x + oval_radius, new_y)
                canvas.coords(balloon['line'], new_x, new_y, new_x, new_y + line_length)
                
                # Assign a new random speed to vary the animation
                balloon['speed'] = random.randint(2, 5)
        
        parent_window.after(50, move_balloons) # Adjust speed of animation

    # Ensure the canvas dimensions are correct before starting
    parent_window.update_idletasks() # Update window geometry before getting canvas size
    canvas.config(width=parent_window.winfo_width(), height=200) # Reconfigure canvas if window size changed

    move_balloons()
    canvas.lift() # Bring canvas to the front once positioned (after other widgets)


# --- Main Menu ---
def main_menu():
    clear_window()
    update_status_bar() # Ensure status bar is present and updated
    title = create_label(root, "Welcome to the Advanced Voting System", title_font)
    title.pack(pady=40)

    button_frame = Frame(root, bg=BG_COLOR)
    button_frame.pack(pady=20)

    create_button(button_frame, "Admin Login", admin_login_screen).pack(pady=10)
    create_button(button_frame, "Voter Login", voter_login_screen).pack(pady=10)

# --- Initial setup ---
if __name__ == "__main__":
    # Ensure the database connection is closed when the app exits
    root.protocol("WM_DELETE_WINDOW", lambda: (conn.close(), root.destroy()))
    main_menu()
    root.mainloop()
