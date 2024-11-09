from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.serving import WSGIRequestHandler
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
import csv
import io 
from io import StringIO
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from io import BytesIO
from flask import send_file

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database connection handling
def get_db():
    connection = sqlite3.connect("ship_port_management.db")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()

    # Enable foreign key support
    cursor.execute("PRAGMA foreign_keys = ON")

    # Create tables
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Ships (
        ship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ship_name TEXT NOT NULL,
        capacity INTEGER,
        type TEXT,
        captain_id INTEGER,
        FOREIGN KEY (captain_id) REFERENCES Captains(captain_id) ON DELETE CASCADE ON UPDATE NO ACTION
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Captains (
        captain_id INTEGER PRIMARY KEY AUTOINCREMENT,
        captain_name TEXT NOT NULL,
        experience INTEGER,
        contact TEXT
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Ports (
        port_id INTEGER PRIMARY KEY AUTOINCREMENT,
        port_name TEXT NOT NULL,
        location TEXT,
        capacity INTEGER
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Cargo (
        cargo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        description text,
        weight INTEGER,
        port_id INTEGER,
        FOREIGN KEY (port_id) REFERENCES Ports(port_id) ON DELETE CASCADE ON UPDATE NO ACTION
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Reserve_Port (
        reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ship_id INTEGER,
        port_id INTEGER,
        arrival_date DATE,
        departure_date DATE,
        FOREIGN KEY (ship_id) REFERENCES Ships(ship_id) ON DELETE CASCADE ON UPDATE NO ACTION,
        FOREIGN KEY (port_id) REFERENCES Ports(port_id) ON DELETE CASCADE ON UPDATE NO ACTION
    )''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Ship_Cargo (
        ship_cargo_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ship_id INTEGER,
        cargo_id INTEGER,
        FOREIGN KEY (ship_id) REFERENCES Ships(ship_id) ON DELETE CASCADE ON UPDATE NO ACTION,
        FOREIGN KEY (cargo_id) REFERENCES Cargo(cargo_id) ON DELETE CASCADE ON UPDATE NO ACTION
    )''')

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (                         
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,                         
        password TEXT,                         
        email TEXT UNIQUE)""")   
            
    connection.commit()
    return connection, cursor

# Authentication Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('login'))  # Redirect to login if not logged in
        return f(*args, **kwargs)
    return decorated_function

# Get search criteria based on table
@app.route('/get_criteria/<table>')
@login_required
def get_criteria(table):
    criteria = []
    
    if table == 'ships':
        criteria = ['ship_id','ship_name', 'capacity', 'type', 'captain_id']
    elif table == 'captains':
        criteria = ['captain_id','captain_name', 'experience', 'contact']
    elif table == 'ports':
        criteria = ['port_id','port_name', 'location', 'capacity']
    elif table == 'cargo':
        criteria = ['cargo_id','description', 'weight', 'port_id']
    elif table == 'reserve_port':
        criteria = ['reservation_id','ship_id', 'port_id', 'arrival_date', 'departure_date']
    elif table == 'ship_cargo':
        criteria = ['ship_cargo_id','ship_id', 'cargo_id']
    
    return jsonify(criteria)

@app.route('/search', methods=['GET','POST'])
@login_required
def search():
    table = request.form.get('table')
    criteria = request.form.get('criteria')
    search_term = request.form.get('search_term')

    # Check if all fields are filled in
    if table and criteria and search_term:
        results = get_search_results(table, criteria, search_term)  # Query your database
        if results:
            # Extract column names from the first row if available
            columns = results[0].keys() if isinstance(results[0], sqlite3.Row) else []
            return render_template('search.html', results=results, columns=columns)
        else:
            flash('No results found for the given search.', 'warning')
    else:
        flash('Please fill in all the fields.', 'danger')
    
    return render_template('search.html', results=None, columns=None)

def get_search_results(table, criteria, search_term):
    connection, cursor = get_db()

    # Dynamically build the query
    query = f"SELECT * FROM {table} WHERE {criteria} LIKE ?"
    cursor.execute(query, (f'%{search_term}%',))
    
    # Fetch all results
    results = cursor.fetchall()

    # Return the results
    return results


# Routes for Ship Management
# Route for Adding Ship
@app.route('/add_ship', methods=['POST'])
@login_required
def add_ship():
    connection, cursor = get_db()
    
    name = request.form['name']
    capacity = request.form['capacity']
    ship_type = request.form['type']
    captain_id = request.form['captain_id']
    
    cursor.execute("INSERT INTO Ships (ship_name, capacity, type, captain_id) VALUES (?, ?, ?, ?)",
                   (name, capacity, ship_type, captain_id))
    connection.commit()
    connection.close()
    flash("Ship added successfully!", "success")
    return redirect(url_for('list_ships'))

# Route to list ships
@app.route('/list_ships')
@login_required
def list_ships():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Ships")
    ships = cursor.fetchall()
    cursor.execute("SELECT * FROM Captains")
    captains = cursor.fetchall()
    connection.close()
    return render_template('ships.html', ships=ships, captains=captains)

@app.route('/display_ships')
@login_required
def display_ships():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Ships")
    ships = cursor.fetchall()
    cursor.execute("SELECT * FROM Captains")
    captains = cursor.fetchall()
    connection.close()
    return render_template('displayShips.html', ships=ships, captains=captains)

# Route for Deleting Ship
@app.route('/delete_ship/<int:ship_id>', methods=['POST'])
@login_required
def delete_ship(ship_id):
    connection, cursor = get_db()
    cursor.execute("DELETE FROM Ships WHERE ship_id = ?", (ship_id,))
    connection.commit()
    connection.close()
    flash("Ship deleted successfully!", "success")
    return redirect(url_for('list_ships'))

# Route for Updating Ship
@app.route('/update_ship/<int:ship_id>', methods=['POST'])
@login_required
def update_ship(ship_id):
    connection, cursor = get_db()
    name = request.form['name']
    capacity = request.form['capacity']
    ship_type = request.form['type']
    captain_id = request.form['captain_id']
    
    cursor.execute("""UPDATE Ships 
                      SET ship_name=?, capacity=?, type=?, captain_id=?
                      WHERE ship_id=?""", 
                   (name, capacity, ship_type, captain_id ,ship_id))
    connection.commit()
    connection.close()
    flash("Ship updated successfully!", "success")
    return redirect(url_for('list_ships'))

# Routes for Captain Management
@app.route('/add_captain', methods=['POST'])
@login_required
def add_captain():
    connection, cursor = get_db()
    
    name = request.form['name']
    experience = request.form['experience']
    contact = request.form['contact']
    
    cursor.execute("INSERT INTO Captains (captain_name, experience, contact) VALUES (?, ?, ?)", 
                   (name, experience, contact))
    connection.commit()
    connection.close()
    flash("Captain added successfully!", "success")
    return redirect(url_for('list_captains'))

@app.route('/list_captains')
@login_required
def list_captains():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Captains")
    captains = cursor.fetchall()
    connection.close()
    return render_template('captains.html', captains=captains)

@app.route('/display_captains')
@login_required
def display_captains():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Captains")
    captains = cursor.fetchall()
    connection.close()
    return render_template('displayCaptains.html', captains=captains)

@app.route('/delete_captain/<int:captain_id>', methods=['POST'])
@login_required
def delete_captain(captain_id):
    connection, cursor = get_db()
    cursor.execute("DELETE FROM Captains WHERE captain_id = ?", (captain_id,))
    connection.commit()
    connection.close()
    flash("Captain deleted successfully!", "success")
    return redirect(url_for('list_captains'))

@app.route('/update_captain/<int:captain_id>', methods=['POST'])
@login_required
def update_captain(captain_id):
    connection, cursor = get_db()
    name = request.form['name']
    experience = request.form['experience']
    contact = request.form['contact']
    
    cursor.execute("""UPDATE Captains 
                      SET captain_name=?, experience=?, contact=? 
                      WHERE captain_id=?""", 
                   (name, experience, contact, captain_id))
    connection.commit()
    connection.close()
    flash("Captain updated successfully!", "success")
    return redirect(url_for('list_captains'))

@app.route('/search_captains', methods=['GET'])
@login_required
def search_captains():
    search_query = request.args.get('search', '').strip()

    connection, cursor = get_db()

    # If the search query is not empty, search for captains based on the query
    if search_query:
        cursor.execute("""
            SELECT * FROM Captains
            WHERE captain_name LIKE ? OR experience LIKE ? OR contact LIKE ?
        """, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
    else:
        # If no search query, show all captains
        cursor.execute("SELECT * FROM Captains")
    
    captains = cursor.fetchall()
    connection.close()

    return render_template('displayCaptains.html', captains=captains)

# Routes for Port Management
@app.route('/add_port', methods=['POST'])
@login_required
def add_port():
    connection, cursor = get_db()
    
    name = request.form['name']
    location = request.form['location']
    capacity = request.form['capacity']
    
    cursor.execute("INSERT INTO Ports (port_name, location, capacity) VALUES (?, ?, ?)", 
                   (name, location, capacity))
    connection.commit()
    connection.close()
    flash("Port added successfully!", "success")
    return redirect(url_for('list_ports'))

@app.route('/list_ports')
@login_required
def list_ports():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Ports")
    ports = cursor.fetchall()
    connection.close()
    return render_template('ports.html', ports=ports)

@app.route('/display_ports')
@login_required
def display_ports():
    connection, cursor = get_db()
    cursor.execute("SELECT * FROM Ports")
    ports = cursor.fetchall()
    connection.close()
    return render_template('displayPorts.html', ports=ports)

@app.route('/delete_port/<int:port_id>', methods=['POST'])
@login_required
def delete_port(port_id):
    connection, cursor = get_db()
    cursor.execute("DELETE FROM Ports WHERE port_id = ?", (port_id,))
    connection.commit()
    connection.close()
    flash("Port deleted successfully!", "success")
    return redirect(url_for('list_ports'))

@app.route('/update_port/<int:port_id>', methods=['POST'])
@login_required
def update_port(port_id):
    connection, cursor = get_db()
    name = request.form['name']
    location = request.form['location']
    capacity = request.form['capacity']
    
    cursor.execute("""UPDATE Ports 
                      SET port_name=?, location=?, capacity=? 
                      WHERE port_id=?""", 
                   (name, location, capacity, port_id))
    connection.commit()
    connection.close()
    flash("Port updated successfully!", "success")
    return redirect(url_for('list_ports'))

@app.route('/reserve_port', methods=['GET', 'POST'])
@login_required
def reserve_port():
    connection, cursor = get_db()

    if request.method == 'POST':
        ship_id = request.form['ship_id']
        port_id = request.form['port_id']
        arrival_date = request.form['arrival_date']
        departure_date = request.form['departure_date']
        
        try:
            cursor.execute("""
                INSERT INTO Reserve_Port (ship_id, port_id, arrival_date, departure_date)
                VALUES (?, ?, ?, ?)
            """, (ship_id, port_id, arrival_date, departure_date))
            connection.commit()
            flash("Port reservation successful!", "success")
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", "danger")
        finally:
            connection.close()

        return redirect(url_for('list_reservations'))

    # Fetch available ships and ports for the dropdowns
    cursor.execute("SELECT ship_id, ship_name FROM Ships")
    ships = cursor.fetchall()
    cursor.execute("SELECT port_id, port_name FROM Ports")
    ports = cursor.fetchall()
    connection.close()

    return render_template('reserve_port.html', ships=ships, ports=ports)

@app.route('/list_reservations')
@login_required
def list_reservations():
    connection, cursor = get_db()
    cursor.execute("""
        SELECT rp.reservation_id, s.ship_name, p.port_name, rp.arrival_date, rp.departure_date
        FROM Reserve_Port rp
        JOIN Ships s ON rp.ship_id = s.ship_id
        JOIN Ports p ON rp.port_id = p.port_id
    """)
    reservations = cursor.fetchall()
    connection.close()
    return render_template('reserve_port.html', reservations=reservations)

@app.route('/display_reservations')
@login_required
def display_reservations():
    # Get database connection and cursor
    connection, cursor = get_db()

    # Query to fetch reservation details along with ship and port names
    cursor.execute("""
        SELECT rp.reservation_id, s.ship_name, p.port_name, rp.arrival_date, rp.departure_date, rp.ship_id, rp.port_id
        FROM Reserve_Port rp
        JOIN Ships s ON rp.ship_id = s.ship_id
        JOIN Ports p ON rp.port_id = p.port_id
    """)
    reservations = cursor.fetchall()

    # Optionally, fetch all ships and ports if needed for further use
    cursor.execute("SELECT ship_id, ship_name FROM Ships")
    ships = cursor.fetchall()

    cursor.execute("SELECT port_id, port_name FROM Ports")
    ports = cursor.fetchall()

    # Close connection
    connection.close()

    # Render the template and pass the data
    return render_template('displayReservation.html', reservations=reservations, ships=ships, ports=ports)

@app.route('/update_reservation/<int:reservation_id>', methods=['GET', 'POST'])
@login_required
def update_reservation(reservation_id):
    connection, cursor = get_db()

    # Fetch the current reservation details
    cursor.execute("""
        SELECT rp.reservation_id, rp.ship_id, rp.port_id, rp.arrival_date, rp.departure_date,
               s.ship_name, p.port_name
        FROM Reserve_Port rp
        JOIN Ships s ON rp.ship_id = s.ship_id
        JOIN Ports p ON rp.port_id = p.port_id
        WHERE rp.reservation_id = ?
    """, (reservation_id,))
    reservation = cursor.fetchone()

    if not reservation:
        flash("Reservation not found!", "danger")
        return redirect(url_for('list_reservations'))

    if request.method == 'POST':
        # Get updated details from the form (only the dates)
        arrival_date = request.form['arrival_date']
        departure_date = request.form['departure_date']

        try:
            # Update only the arrival_date and departure_date in the database
            cursor.execute("""
                UPDATE Reserve_Port
                SET arrival_date = ?, departure_date = ?
                WHERE reservation_id = ?
            """, (arrival_date, departure_date, reservation_id))
            connection.commit()
            flash("Reservation updated successfully!", "success")
        except sqlite3.Error as e:
            flash(f"An error occurred: {e}", "danger")
        finally:
            connection.close()

        return redirect(url_for('list_reservations'))

    # Fetch available ships and ports for the dropdowns (for display only, not for updates)
    cursor.execute("SELECT ship_id, ship_name FROM Ships")
    ships = cursor.fetchall()
    cursor.execute("SELECT port_id, port_name FROM Ports")
    ports = cursor.fetchall()
    connection.close()

    return render_template('reserve_port.html', reservation=reservation, ships=ships, ports=ports)

@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def delete_reservation(reservation_id):
    connection, cursor = get_db()

    try:
        # Delete the reservation from the Reserve_Port table
        cursor.execute("""
            DELETE FROM Reserve_Port WHERE reservation_id = ?
        """, (reservation_id,))
        connection.commit()
        flash("Reservation deleted successfully!", "success")
    except sqlite3.Error as e:
        flash(f"An error occurred: {e}", "danger")
    finally:
        connection.close()

    return redirect(url_for('list_reservations'))


@app.route('/ship_cargo', methods=['GET', 'POST'])
@login_required
def ship_cargo():
    connection, cursor = get_db()

    if request.method == 'POST':
        # Retrieve form data for adding cargo
        description = request.form['description']
        weight = request.form['weight']
        ship_id = request.form['ship_id']
        port_id = request.form['port_id']  # Assuming port_id is included in the form

        # Insert the cargo into the Cargo table first
        cursor.execute('''
            INSERT INTO Cargo (description, weight, port_id)
            VALUES (?, ?, ?)
        ''', (description, weight, port_id))
        
        connection.commit()
        
        # Fetch the generated cargo_id
        cargo_id = cursor.lastrowid
        
        # Insert the cargo and ship details into the Ship_Cargo table
        cursor.execute('''
            INSERT INTO Ship_Cargo (ship_id, cargo_id)
            VALUES (?, ?)
        ''', (ship_id, cargo_id))
        
        connection.commit()
        connection.close()

        flash("Cargo assigned to ship successfully!", "success")
        return redirect(url_for('ship_cargo'))

    # Fetch ships, ports, and the current list of assigned cargos
    ships = cursor.execute('SELECT * FROM Ships').fetchall()
    ports = cursor.execute('SELECT * FROM Ports').fetchall()
    ship_cargo = cursor.execute('''
        SELECT s.ship_name AS ship_name, c.description AS description, c.weight, sc.ship_cargo_id, p.port_name AS port_name
        FROM Ship_Cargo sc
        JOIN Ships s ON s.ship_id = sc.ship_id
        JOIN Cargo c ON c.cargo_id = sc.cargo_id
        JOIN Ports p ON p.port_id = c.port_id
    ''').fetchall()

    connection.close()
    return render_template('ship_cargo.html', ships=ships, ship_cargo=ship_cargo, ports=ports)

@app.route('/display_cargo')
@login_required
def display_cargo():
    connection, cursor = get_db()
    cursor.execute("""
        SELECT c.cargo_id, c.description, c.weight, sc.ship_id, s.ship_name, c.port_id, p.port_name
        FROM Cargo c
        LEFT JOIN Ship_Cargo sc ON c.cargo_id = sc.cargo_id
        LEFT JOIN Ships s ON sc.ship_id = s.ship_id
        LEFT JOIN Ports p ON c.port_id = p.port_id
    """)
    cargo_data = cursor.fetchall()
    connection.close()
    return render_template('displayCargo.html', cargo_data=cargo_data)

@app.route('/update_ship_cargo/<int:id>', methods=['GET', 'POST'])
@login_required
def update_ship_cargo(id):
    connection, cursor = get_db()

    if request.method == 'POST':
        # Retrieve form data for updating cargo
        description = request.form['description']
        weight = request.form['weight']
        ship_id = request.form['ship_id']
        port_id = request.form['port_id']

        if not description or not weight or not ship_id or not port_id:
            flash("Please provide all fields", "danger")
            return redirect(url_for('update_ship_cargo', id=id))

        # Update the Cargo table
        cursor.execute('''
            UPDATE Cargo
            SET description = ?, weight = ?, port_id = ?
            WHERE cargo_id = (SELECT cargo_id FROM Ship_Cargo WHERE ship_cargo_id = ?)
        ''', (description, weight, port_id, id))

        # Update the Ship_Cargo table with the new ship_id
        cursor.execute('''
            UPDATE Ship_Cargo
            SET ship_id = ?
            WHERE ship_cargo_id = ?
        ''', (ship_id, id))

        connection.commit()
        connection.close()

        flash("Cargo information updated successfully!", "success")
        return redirect(url_for('ship_cargo'))

    # Fetch the current cargo and ship details for the form
    ship_cargo = cursor.execute('SELECT * FROM Ship_Cargo WHERE ship_cargo_id = ?', (id,)).fetchone()
    ships = cursor.execute('SELECT * FROM Ships').fetchall()
    ports = cursor.execute('SELECT * FROM Ports').fetchall()
    cargo = cursor.execute('SELECT * FROM Cargo WHERE cargo_id = ?', (ship_cargo['cargo_id'],)).fetchone()

    connection.close()
    return render_template('update_ship_cargo.html', ship_cargo=ship_cargo, ships=ships, ports=ports, cargo=cargo)

@app.route('/delete_ship_cargo/<int:id>', methods=['POST'])
@login_required
def delete_ship_cargo(id):
    connection, cursor = get_db()

    # Delete the ship cargo record from the Ship_Cargo table
    cursor.execute('DELETE FROM Ship_Cargo WHERE ship_cargo_id = ?', (id,))
    connection.commit()
    
    # Delete orphaned cargo records from the Cargo table
    cursor.execute('DELETE FROM Cargo WHERE cargo_id NOT IN (SELECT cargo_id FROM Ship_Cargo)')
    connection.commit()

    connection.close()
    flash("Cargo record deleted successfully!", "danger")
    return redirect(url_for('ship_cargo'))

@app.route('/signup', methods=['GET', 'POST'])  # Allow GET requests for the signup form
def signup():
    if request.method == 'POST':
        connection, cursor = get_db()

        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        email = request.form['email']
        
        # Simple validation (optional)
        if not username or not password or not email:
            flash("Please fill out all fields.", "danger")
            return redirect(url_for('signup'))  # Redirect back to the signup page

        try:
            cursor.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)", 
                           (username, password, email))
            connection.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for('login'))  # Redirect to the login page after successful signup
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")
            return redirect(url_for('signup'))  # Redirect back to the signup page if an error occurs
        finally:
            connection.close()

    return render_template('signup.html')  # Render the signup page for GET requests

# Route for login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection, cursor = get_db()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['username'] = username  # Store the username in the session
            flash("Logged in successfully!", "success")
            return redirect(url_for('home'))  # Redirect to home or another page after login
        else:
            flash("Invalid credentials, please try again.", "danger")
            return redirect(url_for('login'))  # Stay on the login page if login fails

    return render_template('login.html')  # Render the login template on GET request

@app.route('/logout')
@login_required
def logout():
    session.pop('username', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))

# Home Route
@app.route('/')
@login_required
def home():
    return render_template('base.html')

# Ships Route
@app.route('/ships')
@login_required
def ships():
    return render_template('ships.html')

# Captain Route
@app.route('/captains')
@login_required
def captains():
    return render_template('captains.html')

# Ports Route
@app.route('/ports')
@login_required
def ports():
    return render_template('ports.html')

# Reserve Port Route
@app.route('/reserve')
@login_required
def reserve():
    return render_template('reserve_port.html')

# Cargo Route
@app.route('/ship_cargo')
@login_required
def cargo():
    return render_template('ship_cargo.html')

#Display Route
@app.route('/display')
@login_required
def display():
    return render_template('display.html')


#Search Route
@app.route('/search_route')
@login_required
def search_route():
    return render_template('search.html')


@app.route('/report')
@login_required
def report():
    return render_template('report.html')


import csv
from io import BytesIO, StringIO
from flask import send_file, render_template
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Helper function to generate PDF for a given table data
def generate_pdf(data, title, headers, fields, y_position=730):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    
    c.drawString(100, y_position, title)
    y_position -= 20
    
    # Table headers
    header_text = " | ".join(headers)
    c.drawString(100, y_position, header_text)
    y_position -= 20
    
    # Table rows
    for row in data:
        row_text = " | ".join(str(row[field]) for field in fields)
        c.drawString(100, y_position, row_text)
        y_position -= 20
    
    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

from io import BytesIO, TextIOWrapper


def generate_csv(data, filename, headers, fields):
    # Create a BytesIO buffer
    output = BytesIO()
    
    # Wrap the BytesIO buffer in a TextIOWrapper to handle text data
    text_output = TextIOWrapper(output, encoding='utf-8', newline='')
    
    # Create a CSV writer object
    writer = csv.DictWriter(text_output, fieldnames=fields)
    
    # Write headers
    writer.writeheader()
    
    # Write data
    for row in data:
        # Filter row to only include keys that are in fieldnames
        filtered_row = {key: row[key] for key in fields if key in row}
        writer.writerow(filtered_row)
    
    # Seek to the beginning of the BytesIO object
    text_output.seek(0)
    output.seek(0)
    
    # Return the CSV as a downloadable file
    return send_file(output, as_attachment=True, download_name=filename, mimetype='text/csv')

# Generate Ships PDF and CSV Report
@app.route('/generate_ships_report_pdf')
@login_required
def generate_ships_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ships')
    ships_data = cursor.fetchall()
    
    headers = ["Ship ID", "Ship Name", "Capacity", "Type","Captain ID"]
    fields = ['ship_id', 'ship_name', 'capacity', 'type', "captain_id"]
    pdf_buffer = generate_pdf(ships_data, "Ships Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="ships_report.pdf", mimetype="application/pdf")

@app.route('/generate_ships_report_csv')
@login_required
def generate_ships_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ships')
    ships_data = cursor.fetchall()
    
    headers = ["Ship ID", "Ship Name", "Capacity", "Type","Captain ID"]
    fields = ['ship_id', 'ship_name', 'capacity', 'type', "captain_id"]
    
    return generate_csv(ships_data, "ships_report.csv", headers, fields)

# Generate Captains PDF and CSV Report
@app.route('/generate_captains_report_pdf')
@login_required
def generate_captains_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Captains')
    captains_data = cursor.fetchall()
    
    headers = ["Captain ID", "Name", "Experience", "Contact"]
    fields = ['captain_id', 'captain_name', 'experience', 'contact']
    pdf_buffer = generate_pdf(captains_data, "Captains Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="captains_report.pdf", mimetype="application/pdf")

@app.route('/generate_captains_report_csv')
@login_required
def generate_captains_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Captains')
    captains_data = cursor.fetchall()
    
    headers = ["Captain ID", "Name", "Experience", "Contact"]
    fields = ['captain_id', 'captain_name', 'experience', 'contact']
    
    return generate_csv(captains_data, "captains_report.csv", headers, fields)

# Generate Ports PDF and CSV Report
@app.route('/generate_ports_report_pdf')
@login_required
def generate_ports_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ports')
    ports_data = cursor.fetchall()
    
    headers = ["Port ID", "Port Name", "Location", "Capacity"]
    fields = ['port_id', 'port_name', 'location', 'capacity']
    pdf_buffer = generate_pdf(ports_data, "Ports Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="ports_report.pdf", mimetype="application/pdf")

@app.route('/generate_ports_report_csv')
@login_required
def generate_ports_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ports')
    ports_data = cursor.fetchall()
    
    headers = ["Port ID", "Port Name", "Location", "Capacity"]
    fields = ['port_id', 'port_name', 'location', 'capacity']
    
    return generate_csv(ports_data, "ports_report.csv", headers, fields)

# Generate Cargo PDF and CSV Report
@app.route('/generate_cargo_report_pdf')
@login_required
def generate_cargo_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Cargo')
    cargo_data = cursor.fetchall()
    
    headers = ["Cargo ID", "Cargo Type", "Weight", "Ship ID"]
    fields = ['cargo_id', 'cargo_type', 'weight', 'ship_id']
    pdf_buffer = generate_pdf(cargo_data, "Cargo Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="cargo_report.pdf", mimetype="application/pdf")

@app.route('/generate_cargo_report_csv')
@login_required
def generate_cargo_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Cargo')
    cargo_data = cursor.fetchall()
    
    headers = ["Cargo ID", "Cargo Type", "Weight", "Ship ID"]
    fields = ['cargo_id', 'cargo_type', 'weight', 'ship_id']
    
    return generate_csv(cargo_data, "cargo_report.csv", headers, fields)

# Generate Reserve Ports PDF and CSV Report
@app.route('/generate_reserve_ports_report_pdf')
@login_required
def generate_reserve_ports_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Reserve_Port')
    reserve_ports_data = cursor.fetchall()
    
    headers = ["Reserve ID", "Port ID", "Ship ID", "Arrival Date","Departure Date"]
    fields = ['reserve_id', 'port_id', 'ship_id', 'arrival_date', 'departure_date']
    pdf_buffer = generate_pdf(reserve_ports_data, "Reserve Ports Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="reserve_ports_report.pdf", mimetype="application/pdf")

@app.route('/generate_reserve_ports_report_csv')
@login_required
def generate_reserve_ports_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Reserve_Port')
    reserve_ports_data = cursor.fetchall()
    
    headers = ["Reserve ID", "Port ID", "Ship ID", "Arrival Date","Departure Date"]
    fields = ['reserve_id', 'port_id', 'ship_id', 'arrival_date', 'departure_date']
    
    return generate_csv(reserve_ports_data, "reserve_ports_report.csv", headers, fields)

# Generate Ship Cargo PDF and CSV Report
@app.route('/generate_ship_cargo_report_pdf')
@login_required
def generate_ship_cargo_report_pdf():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ship_Cargo')
    ship_cargo_data = cursor.fetchall()
    
    headers = ["Ship_Cargo_id","Ship ID", "Cargo ID"]
    fields = ['ship_cargo_id','ship_id', 'cargo_id']
    pdf_buffer = generate_pdf(ship_cargo_data, "Ship Cargo Report", headers, fields)
    
    return send_file(pdf_buffer, as_attachment=True, download_name="ship_cargo_report.pdf", mimetype="application/pdf")

@app.route('/generate_ship_cargo_report_csv')
@login_required
def generate_ship_cargo_report_csv():
    connection, cursor = get_db()
    cursor.execute('SELECT * FROM Ship_Cargo')
    ship_cargo_data = cursor.fetchall()
    
    headers = ["Ship_Cargo_id","Ship ID", "Cargo ID"]
    fields = ['ship_cargo_id','ship_id', 'cargo_id']
    
    return generate_csv(ship_cargo_data, "ship_cargo_report.csv", headers, fields)

# Helper function to generate PDF for a given table data
def generate_pdf(data, title, headers, fields, y_position=730):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    
    c.drawString(100, y_position, title)
    y_position -= 20
    
    # Table headers
    header_text = " | ".join(headers)
    c.drawString(100, y_position, header_text)
    y_position -= 20
    
    # Table rows
    for row in data:
        row_text = " | ".join(str(row[field]) for field in fields)
        c.drawString(100, y_position, row_text)
        y_position -= 20
    
    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# Helper function to generate CSV for a given table data
def generate_csv(data, headers, fields):
    output = BytesIO()
    text_output = TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.DictWriter(text_output, fieldnames=fields)
    writer.writeheader()
    
    for row in data:
        filtered_row = {key: row[key] for key in fields if key in row}
        writer.writerow(filtered_row)
    
    text_output.seek(0)
    output.seek(0)
    return output

# Individual table report generators
def fetch_table_data(table_name, fields):
    connection, cursor = get_db()
    cursor.execute(f'SELECT {", ".join(fields)} FROM {table_name}')
    data = cursor.fetchall()
    connection.close()
    return data

@app.route('/generate_combined_report_pdf')
@login_required
def generate_combined_report_pdf():
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    y_position = 730

    # List of tables with respective headers and fields
    reports = [
        ("Ships", ["Ship ID", "Ship Name", "Capacity", "Type", "Captain ID"],
         ['ship_id', 'ship_name', 'capacity', 'type', 'captain_id']),
        ("Captains", ["Captain ID", "Name", "Experience", "Contact"],
         ['captain_id', 'captain_name', 'experience', 'contact']),
        ("Ports", ["Port ID", "Port Name", "Location", "Capacity"],
         ['port_id', 'port_name', 'location', 'capacity']),
        ("Cargo", ["Cargo ID", "Cargo Description", "Weight", "Port ID"],
         ['cargo_id', 'description', 'weight', 'port_id']),
        ("Reserve_Port", ["Reserve ID", "Port ID", "Ship ID", "Arrival Date", "Departure Date"],
         ['reservation_id', 'port_id', 'ship_id', 'arrival_date', 'departure_date']),
        ("Ship_Cargo", ["Ship_Cargo ID", "Ship ID", "Cargo ID"],
         ['ship_cargo_id', 'ship_id', 'cargo_id']),
    ]

    for title, headers, fields in reports:
        data = fetch_table_data(title.replace(" ", "_"), fields)
        c.drawString(100, y_position, f"{title} Report")
        y_position -= 20
        
        header_text = " | ".join(headers)
        c.drawString(100, y_position, header_text)
        y_position -= 20
        
        for row in data:
            row_text = " | ".join(str(row[field]) for field in fields)
            c.drawString(100, y_position, row_text)
            y_position -= 20
            if y_position < 40:
                c.showPage()
                y_position = 730

        y_position -= 40  # Add space between tables
    c.save()
    pdf_buffer.seek(0)
    return send_file(pdf_buffer, as_attachment=True, download_name="combined_report.pdf", mimetype="application/pdf")


@app.route('/generate_combined_report_csv')
@login_required
def generate_combined_report_csv():
    output = BytesIO()
    text_output = TextIOWrapper(output, encoding='utf-8', newline='')
    writer = csv.writer(text_output)

    # List of tables with respective headers and fields
    reports = [
        ("Ships", ["Ship ID", "Ship Name", "Capacity", "Type", "Captain ID"],
         ['ship_id', 'ship_name', 'capacity', 'type', 'captain_id']),
        ("Captains", ["Captain ID", "Name", "Experience", "Contact"],
         ['captain_id', 'captain_name', 'experience', 'contact']),
        ("Ports", ["Port ID", "Port Name", "Location", "Capacity"],
         ['port_id', 'port_name', 'location', 'capacity']),
        ("Cargo", ["Cargo ID", "Cargo Description", "Weight", "Port ID"],
         ['cargo_id', 'description', 'weight', 'port_id']),
        ("Reserve_Port", ["Reserve ID", "Port ID", "Ship ID", "Arrival Date", "Departure Date"],
         ['reservation_id', 'port_id', 'ship_id', 'arrival_date', 'departure_date']),
        ("Ship_Cargo", ["Ship_Cargo ID", "Ship ID", "Cargo ID"],
         ['ship_cargo_id', 'ship_id', 'cargo_id']),
    ]

    for title, headers, fields in reports:
        writer.writerow([title])  # Table title as a row
        writer.writerow(headers)  # Header row

        data = fetch_table_data(title.replace(" ", "_"), fields)
        for row in data:
            writer.writerow([row[field] for field in fields])
        
        writer.writerow([])  # Blank row between tables

    text_output.seek(0)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name="combined_report.csv", mimetype="text/csv")



if __name__ == '__main__':
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(debug=True)
