import os
import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
# Production Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
# Fix for Heroku/Render Postgres URL starting with postgres://
database_url = os.environ.get('DATABASE_URL', 'sqlite:///wedding.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuration
DEBUG_MODE = os.environ.get('FLASK_ENV') == 'development'
TOTAL_SEATS = 120

# Admin Credentials (Load from Env or Default)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'password123')

# --- Models ---
class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.Integer, unique=True, nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    dietary_restrictions = db.Column(db.String(200))
    status = db.Column(db.String(20), default='PENDING') # PENDING, CONFIRMED, DECLINED
    email_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def display_seat_number(self):
        if self.seat_number is None:
            return "?"
        
        val = abs(self.seat_number)
        if val >= 1000:
            return val % 1000
        return val

    def to_dict(self):
        return {
            'id': self.id,
            'seat_number': self.display_seat_number, # Use display version
            'raw_seat_number': self.seat_number,
            'first_name': self.first_name,
            'surname': self.surname,
            'phone': self.phone,
            'email': self.email,
            'dietary_restrictions': self.dietary_restrictions,
            'status': self.status,
            'email_sent': self.email_sent
        }

# --- Helper Functions ---
def send_email(to_email, subject, body):
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')
    smtp_server = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('MAIL_PORT', 587))

    # Fallback to mock if credentials are missing (Local Dev)
    if not sender_email or not sender_password:
        print("----------------------------------------------------------------")
        print(f"[MOCK EMAIL] To: {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {body}")
        print("----------------------------------------------------------------")
        return True

    msg = MIMEMultipart()
    msg['From'] = f"Ndivhuwo & Mpho <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    
    # HTML Email Template
    html_body = f"""
    <html>
        <body style="font-family: 'Times New Roman', serif; color: #333; line-height: 1.6; background-color: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 40px; border: 1px solid #e0e0e0; text-align: center;">
                <h1 style="color: #c5a059; font-family: 'Great Vibes', cursive; font-size: 3em; margin-bottom: 10px;">Ndivhuwo & Mpho</h1>
                <p style="text-transform: uppercase; letter-spacing: 2px; font-size: 0.9em; color: #666; margin-bottom: 30px;">Wedding Celebration</p>
                <hr style="border: 0; border-top: 1px solid #c5a059; width: 50%; margin: 20px auto;">
                
                <div style="text-align: left; margin: 30px 0;">
                    {body}
                </div>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 0.9em;">
                    <p>We can't wait to celebrate with you!</p>
                    <p><strong>Date:</strong> 2nd May 2026<br>
                    <strong>Venue:</strong> 22 Denne Rd., Rand Collieries, Brakpan</p>
                </div>
            </div>
        </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Async Wrapper
import threading
def send_email_async(to_email, subject, body):
    thread = threading.Thread(target=send_email, args=(to_email, subject, body))
    thread.daemon = True
    thread.start()

# ... (Previous code remains) ...

def get_random_available_seat():
    # Get all seat numbers that are actively reserved (PENDING or CONFIRMED)
    # DECLINED seats are free.
    reserved_seats = [
        r.seat_number for r in Reservation.query.filter(
            Reservation.status.in_(['PENDING', 'CONFIRMED'])
        ).all()
    ]
    
    available_seats = [i for i in range(1, TOTAL_SEATS + 1) if i not in reserved_seats]
    
    if available_seats:
        return random.choice(available_seats)
    return None

# --- Routes ---

@app.route('/')
def index():
    # Only show PENDING and CONFIRMED as reserved on the grid
    reservations = Reservation.query.filter(Reservation.status.in_(['PENDING', 'CONFIRMED'])).all()
    reserved_seat_numbers = [r.seat_number for r in reservations]
    return render_template('index.html', reserved_seats=reserved_seat_numbers, total_seats=TOTAL_SEATS)

@app.route('/reserve', methods=['POST'])
def reserve():
    data = request.form
    requested_seat = data.get('seat_number')
    
    seat_number = None

    if requested_seat and requested_seat.strip():
        try:
            target_seat = int(requested_seat)
            # Check availability
            existing = Reservation.query.filter_by(seat_number=target_seat).filter(
                Reservation.status.in_(['PENDING', 'CONFIRMED'])
            ).first()
            
            if existing:
                return jsonify({'success': False, 'message': f'Seat #{target_seat} is no longer available.'}), 400
            
            if target_seat < 1 or target_seat > TOTAL_SEATS:
                 return jsonify({'success': False, 'message': 'Invalid seat number.'}), 400
                 
            seat_number = target_seat
        except ValueError:
             return jsonify({'success': False, 'message': 'Invalid seat number format.'}), 400
    else:
        # Check if the user mistakenly sent an empty seat request but intended to pick one?
        # No, the logic handles "no seat selected" -> "random".
        seat_number = get_random_available_seat()

    if not seat_number:
        return jsonify({'success': False, 'message': 'Sorry, no seats available.'}), 400
    new_reservation = Reservation(
        seat_number=seat_number,
        first_name=data['first_name'],
        surname=data['surname'],
        phone=data['phone'],
        email=data['email'],
        dietary_restrictions=data.get('dietary_restrictions', '')
    )
    
    try:
        db.session.add(new_reservation)
        db.session.commit()
        
        # Notify Admin (Async)
        send_email_async(
            "admin@wedding.com", 
            "New Reservation Received", 
            f"<p>New reservation from <strong>{data['first_name']} {data['surname']}</strong> for seat <strong>#{seat_number}</strong>.</p>"
        )
        
        return jsonify({'success': True, 'message': 'Reservation submitted! Waiting for confirmation.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'An error occurred. Please try again.'}), 500

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials')
    
    return render_template('admin.html', login=True)

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('admin'))
    
    pending_reservations = Reservation.query.filter_by(status='PENDING').all()
    confirmed_reservations = Reservation.query.filter_by(status='CONFIRMED').all()
    declined_reservations = Reservation.query.filter_by(status='DECLINED').all()
    
    return render_template('admin.html', 
                           login=False, 
                           reservations=pending_reservations,
                           confirmed=confirmed_reservations,
                           declined=declined_reservations)

@app.route('/admin/action/<int:id>/<action>')
def admin_action(id, action):
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    reservation = Reservation.query.get_or_404(id)
    
    if action == 'accept':
        # If it was previously declined, the seat_number might be negative (released).
        # We need to restore it to a positive number.
        if reservation.seat_number < 0:
            val = abs(reservation.seat_number)
            # Legacy format (-seat) vs New format (-(id*1000 + seat))
            # Assuming TOTAL_SEATS < 1000, legacy values are < 1000.
            if val >= 1000:
                original_seat = val % 1000
            else:
                original_seat = val
                
            # Check if this seat is now taken by someone else
            existing = Reservation.query.filter_by(seat_number=original_seat).filter(
                Reservation.status.in_(['PENDING', 'CONFIRMED'])
            ).first()
            
            if existing:
                return jsonify({'success': False, 'message': f'Original seat #{original_seat} is now taken. Cannot revert.'}), 400
            
            reservation.seat_number = original_seat
            
        reservation.status = 'CONFIRMED'
        # DO NOT send email automatically anymore
        db.session.commit()
            
        return jsonify({'success': True, 'message': 'Reservation accepted. Don\'t forget to send the email!'})
    
    elif action == 'decline':
        if reservation.email_sent:
             return jsonify({'success': False, 'message': 'Cannot decline/undo: Email already sent to guest.'}), 400

        # Works for both Pending and Confirmed.
        reservation.status = 'DECLINED'
        
        # Free the seat if it's currently positive
        if reservation.seat_number > 0:
            # Generate a UNIQUE negative number to avoid "IntegrityError: UNIQUE constraint failed"
            # formula: -1 * ((id * 1000) + seat_number)
            # This preserves the seat info (mod 1000) and ensures uniqueness (via id).
            reservation.seat_number = -1 * ((reservation.id * 1000) + reservation.seat_number)
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Reservation declined.'})
    
    elif action == 'send_email':
        if reservation.status == 'CONFIRMED':
            subject = "You're In! Wedding Confirmation"
            body = f"<p>Dear {reservation.first_name},</p><p>Your seat <strong>#{reservation.seat_number}</strong> for the wedding of Ndivhuwo & Mpho has been confirmed.</p>"
        elif reservation.status == 'DECLINED':
            subject = "Update on your Reservation Request - Ndivhuwo & Mpho"
            body = (f"<p>Dear {reservation.first_name},</p>"
                    "<p>Thank you for RSVPing to our wedding. We are truly humbled by the love and support we have received.</p>"
                    "<p>Unfortunately, due to strict venue capacity limitations, we are unable to accommodate your reservation request at this time. "
                    "We are genuinely sorry for this outcome and hope you understand that this decision was difficult for us to make.</p>"
                    "<p>Thank you for your warm wishes.</p>")
        else:
            return jsonify({'success': False, 'message': 'Can only send emails to CONFIRMED or DECLINED guests.'}), 400
            
        if reservation.email_sent:
             return jsonify({'success': False, 'message': 'Email already sent.'}), 400

        try:
            # Use Async send to avoid timeout on admin dashboard
            send_email_async(
                reservation.email,
                subject,
                body
            )
            reservation.email_sent = True
            db.session.commit()
            return jsonify({'success': True, 'message': 'Email sent successfully!'})
        except:
             return jsonify({'success': False, 'message': 'Failed to send email.'}), 500
        
    return jsonify({'success': False, 'message': 'Invalid action'}), 400

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=DEBUG_MODE, port=5000, host='0.0.0.0')
