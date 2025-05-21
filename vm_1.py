import sqlite3
from tkinter import *
from tkinter import messagebox, ttk
import time
from tkinter import font as tkfont

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

conn.commit()

# --- Color Scheme ---
BG_COLOR = "#2c3e50"  # Dark blue-gray
FG_COLOR = "#ecf0f1"  # Light gray
ACCENT_COLOR = "#3498db"  # Bright blue
BUTTON_COLOR = "#2980b9"  # Slightly darker blue
HOVER_COLOR = "#1abc9c"  # Teal
ERROR_COLOR = "#e74c3c"  # Red
SUCCESS_COLOR = "#2ecc71"  # Green
TEXT_COLOR = "#2c3e50"  # Dark blue-gray

# --- Tkinter setup ---
root = Tk()
root.geometry("600x550")
root.title("Voting System")
root.configure(bg=BG_COLOR)

# Custom fonts
title_font = tkfont.Font(family="Helvetica", size=18, weight="bold")
label_font = tkfont.Font(family="Helvetica", size=12)
button_font = tkfont.Font(family="Helvetica", size=10, weight="bold")

def clear_window():
    """Clears all widgets from the root window."""
    for widget in root.winfo_children():
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
        time.sleep(duration/1000/20) # Adjusted sleep for smoother animation

def create_button(parent, text, command, width=20):
    """Creates a styled button with hover effects."""
    btn = Button(parent, text=text, command=command, 
                 bg=BUTTON_COLOR, fg=FG_COLOR, 
                 activebackground=HOVER_COLOR, activeforeground=FG_COLOR,
                 font=button_font, width=width, relief="raised", bd=2)
    
    # Add hover effect
    def on_enter(e):
        e.widget['background'] = HOVER_COLOR
    def on_leave(e):
        e.widget['background'] = BUTTON_COLOR
    
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
        if label.winfo_exists(): # Check if label still exists
            label.config(fg=colors[index])
            root.after(duration, change_color, (index + 1) % len(colors))
    change_color()

# --- Admin Registration ---
def admin_register_screen():
    clear_window()
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
            root.after(2000, lambda: error_label.destroy() if error_label.winfo_exists() else None) # Use destroy for cleanup

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Login", login).pack(pady=5)
    create_button(btn_frame, "Register as Admin", admin_register_screen).pack(pady=5)

# --- Voter Registration ---
def voter_register_screen():
    clear_window()
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
            # Current year for age calculation (assuming 2025 as per original logic)
            current_year = 2025 
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
    title = create_label(root, f"Voter: {username}", title_font)
    title.pack(pady=20)
    
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
    selected_party.set(candidates[0][0]) # Set a default selection

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
        # Double-check if already voted for safety
        cursor.execute("SELECT voted FROM voters WHERE username=?", (username,))
        if cursor.fetchone()[0]:
            messagebox.showerror("Error", "You have already voted.")
            voter_dashboard(username, True)
            return

        cursor.execute("UPDATE candidates SET votes = votes + 1 WHERE party_name=?", (party,))
        cursor.execute("UPDATE voters SET voted=1 WHERE username=?", (username,))
        conn.commit()
        
        # Animated success message
        success_frame = Frame(root, bg=BG_COLOR)
        success_frame.pack(pady=20)
        
        temp_labels = []
        for i in range(1, 4):
            dots = "." * i
            success_label = create_label(success_frame, f"You voted for {party}{dots}", label_font)
            success_label.pack()
            temp_labels.append(success_label)
            root.update()
            time.sleep(0.3)
            if success_label.winfo_exists(): # Check before destroying
                success_label.destroy()
        
        final_label = create_label(success_frame, f"You voted for {party}!", label_font)
        final_label.pack()
        final_label.config(fg=SUCCESS_COLOR)
        root.after(1500, lambda: voter_dashboard(username, True))

    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Submit Vote", submit_vote).pack(pady=5)
    create_button(btn_frame, "Logout", main_menu).pack(pady=5)

# --- Admin Dashboard ---
def admin_dashboard():
    clear_window()
    title = create_label(root, "Admin Dashboard", title_font)
    title.pack(pady=20)

    def view_voters():
        top = Toplevel(root)
        top.title("Voter List")
        top.geometry("600x400") # Added geometry for consistent sizing
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
        
        # Adjust column widths
        tree.column("Username", width=150, anchor="center")
        tree.column("Password", width=150, anchor="center")
        tree.column("Birth Year", width=100, anchor="center")
        tree.column("Voted", width=80, anchor="center")
        
        tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        cursor.execute("SELECT username, password, birth_year, voted FROM voters")
        for row in cursor.fetchall():
            tree.insert("", END, values=row)

    def view_candidates():
        top = Toplevel(root)
        top.title("Candidates List")
        top.geometry("600x400") # Added geometry
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

        # Adjust column widths
        tree.column("Party Name", width=150, anchor="center")
        tree.column("Leader Name", width=150, anchor="center")
        tree.column("Password", width=100, anchor="center")
        tree.column("Votes", width=80, anchor="center")
        
        tree.pack(fill=BOTH, expand=True, padx=10, pady=10)

        cursor.execute("SELECT party_name, leader_name, password, votes FROM candidates")
        for row in cursor.fetchall():
            tree.insert("", END, values=row)

    def show_results():
        top = Toplevel(root)
        top.title("Election Results")
        top.geometry("400x300") # Added geometry
        top.configure(bg=BG_COLOR)

        cursor.execute("SELECT party_name, votes FROM candidates")
        results = cursor.fetchall()
        if not results:
            create_label(top, "No votes cast yet.", label_font).pack(pady=20)
            return

        total_votes = sum(votes for _, votes in results)
        if total_votes == 0:
            create_label(top, "No votes cast yet.", label_font).pack(pady=20)
            return

        max_votes = -1
        if results: # Ensure results is not empty before finding max
            max_votes = max(votes for _, votes in results)
        
        winners = [party for party, votes in results if votes == max_votes and max_votes > 0] # Ensure winners only if votes > 0

        frame = Frame(top, bg=BG_COLOR)
        frame.pack(pady=20)
        
        for party, votes in results:
            percentage = (votes / total_votes) * 100 if total_votes > 0 else 0
            party_label = create_label(frame, f"{party}: {votes} votes ({percentage:.2f}%)", label_font)
            party_label.pack(anchor="w")
            if votes == max_votes and max_votes > 0:
                party_label.config(fg=SUCCESS_COLOR)

        if winners:
            if len(winners) == 1:
                winner_text = f"Winner: {winners[0]} with {max_votes} votes!"
            else:
                winner_text = f"Tie between: {', '.join(winners)} with {max_votes} votes!"
            winner_label = create_label(top, winner_text, title_font)
            winner_label.pack(pady=20)
            animate_label(winner_label, [SUCCESS_COLOR, HOVER_COLOR, ACCENT_COLOR])
        else:
            create_label(top, "No clear winner yet.", title_font).pack(pady=20)


    def reset_votes():
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to reset ALL votes? This action cannot be undone.")
        if confirm:
            cursor.execute("UPDATE candidates SET votes = 0")
            cursor.execute("UPDATE voters SET voted = 0")
            conn.commit()
            
            reset_label = create_label(root, "All votes have been reset", label_font)
            reset_label.pack(pady=10)
            reset_label.config(fg=SUCCESS_COLOR)
            root.after(2000, lambda: reset_label.destroy() if reset_label.winfo_exists() else None)

    def view_all_credentials():
        top = Toplevel(root)
        top.title("All User Credentials")
        top.geometry("700x500") # Added geometry
        top.configure(bg=BG_COLOR)
        
        style = ttk.Style()
        style.configure("Treeview", background=FG_COLOR, foreground=TEXT_COLOR, fieldbackground=FG_COLOR)
        style.configure("Treeview.Heading", background=BUTTON_COLOR, foreground=FG_COLOR, font=button_font)
        style.map("Treeview", background=[('selected', HOVER_COLOR)])
        
        notebook = ttk.Notebook(top)
        notebook.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Admin tab
        admin_frame = Frame(notebook, bg=BG_COLOR)
        notebook.add(admin_frame, text="Admins")
        admin_tree = ttk.Treeview(admin_frame, columns=("Username", "Password"), show='headings')
        admin_tree.heading("Username", text="Username")
        admin_tree.heading("Password", text="Password")
        admin_tree.pack(fill=BOTH, expand=True, padx=5, pady=5)
        cursor.execute("SELECT username, password FROM admin")
        for row in cursor.fetchall():
            admin_tree.insert("", END, values=row)
        
        # Voters tab
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
        
        # Candidates tab
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

    # Main buttons frame
    main_frame = Frame(root, bg=BG_COLOR)
    main_frame.pack(pady=20)
    
    # First row of buttons
    frame1 = Frame(main_frame, bg=BG_COLOR)
    frame1.pack(pady=5)
    create_button(frame1, "View Voters", view_voters, width=25).pack(side=LEFT, padx=5)
    create_button(frame1, "View Candidates", view_candidates, width=25).pack(side=LEFT, padx=5)
    
    # Second row of buttons
    frame2 = Frame(main_frame, bg=BG_COLOR)
    frame2.pack(pady=5)
    create_button(frame2, "Show Results", show_results, width=25).pack(side=LEFT, padx=5)
    create_button(frame2, "Reset All Votes", reset_votes, width=25).pack(side=LEFT, padx=5)
    
    # Third row of buttons
    frame3 = Frame(main_frame, bg=BG_COLOR)
    frame3.pack(pady=5)
    create_button(frame3, "View All Credentials", view_all_credentials, width=25).pack(side=LEFT, padx=5)
    create_button(frame3, "Logout", main_menu, width=25).pack(side=LEFT, padx=5)

# --- Main Menu ---
def main_menu():
    clear_window()
    title = create_label(root, "Welcome to Voting System", title_font)
    title.pack(pady=30)
    
    # Animate the title
    animate_label(title, [ACCENT_COLOR, HOVER_COLOR, SUCCESS_COLOR, FG_COLOR])
    
    # Main buttons
    btn_frame = Frame(root, bg=BG_COLOR)
    btn_frame.pack(pady=20)
    
    create_button(btn_frame, "Admin Login", admin_login_screen, width=25).pack(pady=10)
    create_button(btn_frame, "Voter Login", voter_login_screen, width=25).pack(pady=10)
    create_button(btn_frame, "Candidate Login", candidate_login_screen, width=25).pack(pady=10)
    
    # Exit button with different color
    exit_btn = create_button(root, "Exit", root.destroy, width=25)
    exit_btn.config(bg=ERROR_COLOR, activebackground="#c0392b")
    exit_btn.pack(pady=20)

# Start with fade in effect
root.attributes('-alpha', 0)
root.update()
fade_in(root)

main_menu()
root.mainloop()

# Close the database connection when the application exits
conn.close()