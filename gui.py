import streamlit as st
import pandas as pd
import mysql.connector
import hashlib
from datetime import datetime
import time 

def get_connection():
    """Establish connection to MySQL."""
    # !!! IMPORTANT: Replace with your MySQL credentials !!!
    return mysql.connector.connect(
        host="localhost",
        user="root",              # Your MySQL username (e.g: 'root')
        password="passkey123",     # Your MySQL password
        database="bookyourshow_db" # Your database name
    )


def hash_password(password):
    """Hashes a password for storing."""
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_password(hashed_password, user_password):
    """Checks a user's password against the stored hash."""
    return hashlib.sha256(str.encode(user_password)).hexdigest()


st.set_page_config(
    page_title="BookYourShow",
    page_icon="🎟️",
    layout="wide"
)


if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.session_state.role = None
    st.session_state.page = "home" # home, movie_details, seat_selection, payment, confirmation, profile, admin
    st.session_state.selected_movie_id = None
    st.session_state.selected_show_id = None
    st.session_state.selected_show_price = None
    st.session_state.selected_seats = []
    st.session_state.booking_id = None
    st.session_state.selected_theater_name = None
    st.session_state.selected_show_time = None
    st.session_state.selected_movie_title = None
    st.session_state.error_message = None
    
    st.session_state.pending_booking_price = 0
    st.session_state.pending_booking_seats = []
    
    st.session_state.movie_count = 0



def show_login_page():
    st.title("🎟️ BookYourShow")
    
    login_tab, register_tab = st.tabs(["Login", "Register"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login")
            
            if st.session_state.error_message:
                st.error(st.session_state.error_message)

            if login_button:
                st.session_state.error_message = None # Clear error
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor(dictionary=True)
                        
                        # BACKEND HOOK: Select user from `users` table
                        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
                        user_data = cursor.fetchone()
                        
                        if user_data:
                            if user_data['password'] == password: 
                                st.session_state.logged_in = True
                                st.session_state.user_id = user_data['user_id']
                                st.session_state.user_name = user_data['name']
                                st.session_state.role = user_data['role']
                                st.session_state.page = "home"
                                
                                cursor.execute("SELECT COUNT(*) FROM movies WHERE release_date <= CURDATE()")
                                st.session_state.movie_count = cursor.fetchone()['COUNT(*)']
                                
                                st.rerun() # Rerun the script to show the home page
                            else:
                                st.session_state.error_message = "Incorrect password."
                                st.rerun()
                        else:
                            st.session_state.error_message = "No user found with this email."
                            st.rerun()

                        cursor.close()
                        conn.close()

                    except mysql.connector.Error as err:
                        st.error(f"Database Error: {err.msg}")

    with register_tab:
        with st.form("register_form"):
            name = st.text_input("Full Name")
            reg_email = st.text_input("Email (for registration)")
            
            reg_password = st.text_input("Password (for registration)", type="password")
            register_button = st.form_submit_button("Register")
            
            if register_button:
                if not name or not reg_email or not reg_password:
                    st.error("Please fill out all fields.")
                else:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        
                        cursor.execute(
                            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, 'customer')",
                            (name, reg_email, reg_password)
                        )
                        conn.commit()
                        st.success("Registration successful! Please log in.")
                        
                        cursor.close()
                        conn.close()

                    except mysql.connector.Error as err:
                        if err.errno == 1062: # Duplicate entry
                            st.error("An account with this email already exists.")
                        else:
                            st.error(f"Database Error: {err.msg}")



def show_home_page():

    try:
        conn_check = get_connection()
        cursor_check = conn_check.cursor(dictionary=True)
        cursor_check.execute("SELECT COUNT(*) FROM movies WHERE release_date <= CURDATE()")
        current_movie_count = cursor_check.fetchone()['COUNT(*)']
        cursor_check.close()
        conn_check.close()

        if 'movie_count' not in st.session_state:
            st.session_state.movie_count = current_movie_count
        
        if current_movie_count > st.session_state.movie_count:
            st.toast("New movie added! The page is auto-refreshing...", icon="🎉")
            st.session_state.movie_count = current_movie_count
    
    except mysql.connector.Error as err:
        pass # Silently fail check if DB has issue
    title_col, button_col = st.columns([0.6, 0.4]) 

    with title_col:
        st.title(f"Welcome, {st.session_state.user_name}!")

    with button_col:
        if st.session_state.role == 'admin':
    
            b_cols = st.columns(3) 
            with b_cols[0]:
                if st.button("Profile", use_container_width=True):
                    st.session_state.page = "profile"
                    st.rerun()
            with b_cols[1]:
                if st.button("Admin Panel", use_container_width=True):
                    st.session_state.page = "admin"
                    st.rerun()
            with b_cols[2]:
                if st.button("Logout", use_container_width=True):
                    for key in st.session_state.keys():
                        del st.session_state[key]
                    st.rerun()
        else:
            b_cols = st.columns([0.5, 0.25, 0.25]) 
            with b_cols[1]:
                if st.button("Profile", use_container_width=True):
                    st.session_state.page = "profile"
                    st.rerun()
            with b_cols[2]:
                if st.button("Logout", use_container_width=True):
                    for key in st.session_state.keys():
                        del st.session_state[key]
                    st.rerun()

    st.header("🎬 Recommended Movies")

    try:
        conn = get_connection()
        
        query = "SELECT * FROM movies WHERE release_date <= CURDATE()"
        df_movies = pd.read_sql(query, conn)
        conn.close()
        
        if df_movies.empty:
            st.warning("No movies are currently showing.")
            return

        # Display movies in a grid
        num_cols = 5
        cols = st.columns(num_cols)
        
        for index, movie in df_movies.iterrows():
            with cols[index % num_cols]:
                st.image(f"https://placehold.co/300x450/606060/FFF?text={movie['title'].replace(' ', '+')}", use_container_width=True)
                
                with st.container(height=150): 
                    st.subheader(movie['title'])
                    st.write(f"**Genre:** {movie['genre']}")
                    st.write(f"**Rating:** {movie['rating']} ⭐")

                
                if st.button("Book Now", key=f"movie_{movie['movie_id']}"):
                    st.session_state.selected_movie_id = movie['movie_id']
                    st.session_state.selected_movie_title = movie['title']
                    st.session_state.page = "movie_details"
                    st.rerun()

        time.sleep(5)
        st.rerun()

    except mysql.connector.Error as err:
        st.error(f"Database Error: {err.msg}")


def show_movie_details_page():
    if st.button("← Back to Movies"):
        st.session_state.page = "home"
        st.session_state.selected_movie_id = None
        st.rerun()
        
    try:
        conn = get_connection()
        
        # BACKEND HOOK: Get selected movie's details
        movie_query = "SELECT * FROM movies WHERE movie_id = %s"
        df_movie = pd.read_sql(movie_query, conn, params=(st.session_state.selected_movie_id,))
        
        if df_movie.empty:
            st.error("Movie not found.")
            st.session_state.page = "home"
            st.rerun()
            return
            
        movie = df_movie.iloc[0]
        st.title(movie['title'])
        st.image(f"https://placehold.co/600x400/606060/FFF?text={movie['title'].replace(' ', '+')}", use_container_width=True)
        st.write(f"**Genre:** {movie['genre']} | **Duration:** {movie['duration']} min | **Rating:** {movie['rating']} ⭐")
        st.write(f"**Release Date:** {movie['release_date']}")
        
        st.header("Showtimes")
        
        # BACKEND HOOK: Get all shows for this movie, joining with theaters and screens
        shows_query = """
            SELECT 
                t.name AS theater_name,
                t.location,
                sc.screen_name,
                s.show_id,
                s.show_time,
                s.price
            FROM shows s
            JOIN screens sc ON s.screen_id = sc.screen_id
            JOIN theaters t ON sc.theater_id = t.theater_id
            WHERE s.movie_id = %s AND s.show_time > NOW()
            ORDER BY t.name, s.show_time;
        """
        df_shows = pd.read_sql(shows_query, conn, params=(st.session_state.selected_movie_id,))
        conn.close()

        if df_shows.empty:
            st.warning("No available shows for this movie.")
            return

        # Group shows by theater
        theaters = df_shows['theater_name'].unique()
        for theater in theaters:
            st.subheader(theater)
            st.write(f"📍 {df_shows[df_shows['theater_name'] == theater].iloc[0]['location']}")
            
            theater_shows = df_shows[df_shows['theater_name'] == theater]
            
            # Show showtimes in columns
            num_cols = 4
            cols = st.columns(num_cols)
            for index, show in theater_shows.iterrows():
                with cols[index % num_cols]:
                    if st.button(f"{show['show_time'].strftime('%I:%M %p')}", key=f"show_{show['show_id']}"):
                        st.session_state.selected_show_id = show['show_id']
                        st.session_state.selected_show_price = float(show['price'])
                        st.session_state.selected_theater_name = show['theater_name']
                        st.session_state.selected_show_time = show['show_time']
                        st.session_state.page = "seat_selection"
                        # Reset seats from previous selection
                        st.session_state.selected_seats = [] 
                        st.session_state.pending_booking_seats = []
                        st.session_state.pending_booking_price = 0
                        st.rerun()
                        
    except mysql.connector.Error as err:
        st.error(f"Database Error: {err.msg}")

def show_seat_selection_page():
    if st.button("← Back to Showtimes"):
        st.session_state.page = "movie_details"
        st.session_state.selected_show_id = None
        st.rerun()

    st.title("Select Your Seats")
    st.info(f"**Movie:** {st.session_state.selected_movie_title} | **Theater:** {st.session_state.selected_theater_name} | **Time:** {st.session_state.selected_show_time.strftime('%I:%M %p')}")

    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # BACKEND HOOK: Get total seats for this screen
        cursor.execute("""
            SELECT s.total_seats 
            FROM screens s
            JOIN shows sh ON sh.screen_id = s.screen_id
            WHERE sh.show_id = %s
        """, (st.session_state.selected_show_id,))
        total_seats_result = cursor.fetchone()
        
        if not total_seats_result:
            st.error("Show/Screen data not found.")
            conn.close()
            return
            
        total_seats = total_seats_result[0]
        
        # BACKEND HOOK: Get already booked seats (from `booking_details`)
        cursor.execute("""
            SELECT bd.seat_number
            FROM booking_details bd
            JOIN bookings b ON bd.booking_id = b.booking_id
            WHERE b.show_id = %s AND b.status = 'confirmed'
        """, (st.session_state.selected_show_id,))
        
        occupied_seats = [row[0] for row in cursor.fetchall()]
        conn.close()

        st.markdown('<div style="background-color: #333; color: white; padding: 10px; text-align: center; border-radius: 5px;">SCREEN</div>', unsafe_allow_html=True)
        st.write("")

        seats_per_row = 10
        rows = (total_seats + seats_per_row - 1) // seats_per_row
        
        if 'selected_seats' not in st.session_state:
            st.session_state.selected_seats = []

        for r in range(rows):
            cols = st.columns(seats_per_row)
            for c in range(seats_per_row):
                seat_num = (r * seats_per_row) + c + 1
                if seat_num > total_seats:
                    continue
                    
                seat_id = f"{chr(65+r)}{c+1}" 
                
                with cols[c]:
                    is_occupied = seat_id in occupied_seats
                    is_selected = seat_id in st.session_state.selected_seats
                    
                    if is_occupied:
                        st.button(f"❌ {seat_id}", disabled=True, key=f"seat_{seat_id}")
                    elif is_selected:
                        if st.button(f"✅ {seat_id}", key=f"seat_{seat_id}"):
                            st.session_state.selected_seats.remove(seat_id)
                            st.rerun()
                    else:
                        if st.button(seat_id, key=f"seat_{seat_id}"):
                            st.session_state.selected_seats.append(seat_id)
                            st.rerun()

        if st.session_state.selected_seats:
            num_seats = len(st.session_state.selected_seats)
            price_per_seat = st.session_state.selected_show_price
            total_price = num_seats * price_per_seat
            
            st.subheader("Booking Summary")
            st.write(f"**Seats:** {', '.join(st.session_state.selected_seats)}")
            st.write(f"**Total Price:** ${total_price:.2f} ({num_seats} x ${price_per_seat:.2f})")
            
            # --- Go to Payment Page ---
            if st.button("Confirm Booking"):
                # Store details for payment page
                st.session_state.pending_booking_price = total_price
                st.session_state.pending_booking_seats = st.session_state.selected_seats.copy()
                
                st.session_state.page = "payment"
                st.rerun()

    except mysql.connector.Error as err:
        st.error(f"Database Error: {err.msg}")


def show_payment_page():
    if st.button("← Back to Seat Selection"):
        st.session_state.page = "seat_selection"
        # Clear pending state
        st.session_state.pending_booking_price = 0
        st.session_state.pending_booking_seats = []
        st.rerun()

    st.title("Complete Your Booking")

    st.subheader("Order Summary")
    st.info(f"""
        **Movie:** {st.session_state.selected_movie_title}
        **Theater:** {st.session_state.selected_theater_name}
        **Showtime:** {st.session_state.selected_show_time.strftime('%Y-%m-%d, %I:%M %p')}
        **Seats:** {', '.join(st.session_state.pending_booking_seats)}
        **Total Amount:** ${st.session_state.pending_booking_price:.2f}
    """)

    st.subheader("Select Payment Method")
    payment_mode = st.radio("Payment Mode", ["Online", "Offline"], horizontal=True)

    if st.button("Complete Booking"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            conn.start_transaction()
            
            total_price = st.session_state.pending_booking_price
            
            # 1. INSERT into `bookings` table
            # NOTE: Your `calculate_booking_amount` trigger MUST be removed for this to work.
            cursor.execute(
                """
                INSERT INTO bookings (user_id, show_id, total_amount, status)
                VALUES (%s, %s, %s, 'confirmed')
                """,
                (st.session_state.user_id, st.session_state.selected_show_id, total_price)
            )
            booking_id = cursor.lastrowid
            st.session_state.booking_id = booking_id
            
            # 2. INSERT into `booking_details` (one for each seat)
            # THIS WILL FIRE YOUR `prevent_overbooking` TRIGGER!
            seat_data = [(booking_id, seat) for seat in st.session_state.pending_booking_seats]
            cursor.executemany(
                """
                INSERT INTO booking_details (booking_id, seat_number)
                VALUES (%s, %s)
                """,
                seat_data
            )
            
            # 3. INSERT into `payments`
            # THIS WILL FIRE YOUR `update_booking_status_after_payment` TRIGGER
            cursor.execute(
                """
                INSERT INTO payments (booking_id, amount, payment_mode, payment_status)
                VALUES (%s, %s, %s, 'success')
                """,
                (booking_id, total_price, payment_mode.lower()) # Use selected payment mode
            )
            
            # If all successful, commit the transaction
            conn.commit()
            
            # Clear pending state
            st.session_state.pending_booking_price = 0
            st.session_state.pending_booking_seats = []
            
            st.session_state.page = "confirmation"
            st.rerun()

        except mysql.connector.Error as err:
            conn.rollback() 
            # This will show the "No seats available!" error from your trigger
            st.error(f"BOOKING FAILED: {err.msg}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()


def show_confirmation_page():
    st.title("✅ Booking Confirmed!")
    st.balloons()
    
    st.subheader("Your Booking Details")
    st.info(f"""
        **Booking ID:** {st.session_state.booking_id}
        **Movie:** {st.session_state.selected_movie_title}
        **Theater:** {st.session_state.selected_theater_name}
        **Showtime:** {st.session_state.selected_show_time.strftime('%Y-%m-%d, %I:%M %p')}
        **Seats:** {', '.join(st.session_state.selected_seats)}
        **Total Amount:** ${len(st.session_state.selected_seats) * st.session_state.selected_show_price:.2f}
        **Status:** Confirmed
    """)
    
    if st.button("Book Another Ticket"):
        # Reset for a new booking
        st.session_state.page = "home"
        st.session_state.selected_movie_id = None
        st.session_state.selected_show_id = None
        st.session_state.selected_seats = []
        st.session_state.booking_id = None
        st.rerun()
    
    st.divider()
    
    st.subheader("Cancel Booking")
    st.warning("This action cannot be undone.")
    if st.button("Cancel This Booking"):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            
            # BACKEND HOOK: Call your `cancel_booking` procedure
            # This will also fire your `log_booking_cancellation` trigger!
            cursor.execute("CALL cancel_booking(%s)", (st.session_state.booking_id,))
            conn.commit()
            
            st.success("Your booking has been cancelled.")
            st.info("The page will reset.")
            
            # Reset
            st.session_state.page = "home"
            st.session_state.selected_movie_id = None
            st.session_state.selected_show_id = None
            st.session_state.selected_seats = []
            st.session_state.booking_id = None
            st.rerun()

        except mysql.connector.Error as err:
            st.error(f"Error during cancellation: {err.msg}")
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()


def show_profile_page():
    if st.button("← Back to Movies"):
        st.session_state.page = "home"
        st.rerun()
        
    st.title(f"Profile: {st.session_state.user_name}")
    
    # --- Flag for 0 amount warning ---
    show_zero_amount_warning = False
    
    try:
        conn = get_connection()
        
        # 1. Get User Details
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT email FROM users WHERE user_id = %s", (st.session_state.user_id,))
        user_details = cursor.fetchone()
        
        if user_details:
            st.subheader("Your Details")
            st.write(f"**Name:** {st.session_state.user_name}")
            st.write(f"**Email:** {user_details['email']}")
        
        cursor.close()
        
        # 2. Get User Bookings
        st.header("My Bookings")
        booking_query = """
            SELECT 
                b.booking_id, 
                m.title AS Movie, 
                t.name AS Theater,
                s.show_time AS Showtime, 
                b.total_amount AS Amount, 
                b.status AS Status
            FROM bookings b
            JOIN shows s ON b.show_id = s.show_id
            JOIN movies m ON s.movie_id = m.movie_id
            JOIN screens sc ON s.screen_id = sc.screen_id
            JOIN theaters t ON sc.theater_id = t.theater_id
            WHERE b.user_id = %s
            ORDER BY s.show_time DESC;
        """
        df_bookings = pd.read_sql(booking_query, conn, params=(st.session_state.user_id,))
        
        if not df_bookings.empty:
            
            for index, booking in df_bookings.iterrows():
                header = f"{booking['Movie']} at {booking['Theater']} ({booking['Showtime'].strftime('%d %b %Y, %I:%M %p')})"
                
                with st.expander(header):
                    st.write(f"**Booking ID:** {booking['booking_id']}")
                    st.write(f"**Status:** {booking['Status'].capitalize()}")
                    st.write(f"**Total Amount:** ${booking['Amount']:.2f}")
                    
                    if booking['Amount'] == 0:
                        show_zero_amount_warning = True

                    cursor = conn.cursor()
                    cursor.execute("SELECT seat_number FROM booking_details WHERE booking_id = %s", (booking['booking_id'],))
                    seats = [row[0] for row in cursor.fetchall()]
                    if seats:
                        st.write(f"**Seats:** {', '.join(seats)}")
                    
                    cursor.execute("SELECT payment_mode, payment_status, payment_date FROM payments WHERE booking_id = %s", (booking['booking_id'],))
                    payment = cursor.fetchone() # Assuming one payment per booking
                    if payment:
                        st.write(f"**Payment Mode:** {payment[0].capitalize()}")
                        st.write(f"**Payment Status:** {payment[1].capitalize()}")
                        st.write(f"**Payment Date:** {payment[2].strftime('%Y-%m-%d, %I:%M %p')}")
                    
                    cursor.close()
                    
                    st.divider()
                    
                    is_future_booking = booking['Showtime'] > datetime.now()
                    
                    if booking['Status'] == 'confirmed' and is_future_booking:
                        if st.button("Cancel This Booking", key=f"cancel_{booking['booking_id']}"):
                            try:
                                # Re-open connection for the transaction
                                conn_cancel = get_connection()
                                cursor_cancel = conn_cancel.cursor()
                                cursor_cancel.execute("CALL cancel_booking(%s)", (booking['booking_id'],))
                                conn_cancel.commit()
                                cursor_cancel.close()
                                conn_cancel.close()
                                st.success(f"Booking {booking['booking_id']} cancelled.")
                                st.rerun() # Refresh the page to show new status
                            except mysql.connector.Error as err:
                                st.error(f"Cancellation Error: {err.msg}")
                                
                    elif booking['Status'] == 'cancelled':
                        st.info("This booking is already cancelled.")
                    elif not is_future_booking:
                        st.info("This show has already passed.")

        else:
            st.info("You have no booking history.")
        
        if show_zero_amount_warning:
            st.warning("⚠️ **Found bookings with $0 amount!**\n\nThis is likely due to your `calculate_booking_amount` database trigger. This trigger's logic is flawed and sets the price to 0.\n\n**To fix this, please run this command in your MySQL database:**\n`DROP TRIGGER IF EXISTS calculate_booking_amount;`")
        
        if conn.is_connected():
            conn.close()

    except mysql.connector.Error as err:
        st.error(f"Database Error: {err.msg}")
        if 'conn' in locals() and conn.is_connected():
            conn.close()


def show_admin_panel():
    if st.button("← Back to Movies"):
        st.session_state.page = "home"
        st.rerun()

    st.title("Admin Panel: Activity Logs")
    st.warning("You are in the admin panel. All user activity is logged here.")

    try:
        conn = get_connection()
        
        # Query to get all logs, joining with users table to get names
        log_query = """
            SELECT 
                a.log_id,
                a.log_timestamp,
                a.activity_type,
                u.name AS user_name,
                u.email AS user_email,
                a.booking_id,
                a.details
            FROM activity_log a
            LEFT JOIN users u ON a.user_id = u.user_id
            ORDER BY a.log_timestamp DESC;
        """
        df_logs = pd.read_sql(log_query, conn)
        conn.close()

        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No activity has been logged yet.")

    except mysql.connector.Error as err:
        st.error(f"Database Error: {err.msg}")
        if 'conn' in locals() and conn.is_connected():
            conn.close()


if not st.session_state.logged_in:
    show_login_page()
else:
    if st.session_state.page == "home":
        show_home_page()
    elif st.session_state.page == "movie_details":
        show_movie_details_page()
    elif st.session_state.page == "seat_selection":
        show_seat_selection_page()
    elif st.session_state.page == "payment":
        show_payment_page()
    elif st.session_state.page == "confirmation":
        show_confirmation_page()
    elif st.session_state.page == "profile":
        show_profile_page()
    elif st.session_state.page == "admin":
        if st.session_state.role == 'admin':
            show_admin_panel()
        else:
            st.error("You do not have permission to view this page.")
            st.session_state.page = "home"
            st.rerun()
    else:
        st.session_state.page = "home"
        st.rerun()
