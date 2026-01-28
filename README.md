# Ndivhuwo & Mpho Wedding Reservation System

A beautiful, custom-designed wedding reservation website built with Flask. Guests can RSVP, select their specific seats from a visual grid, and view wedding details. Administrators have a dedicated dashboard to manage the guest list.

## Features

- **Guest RSVP**:
  - Interactive seating grid (1-120).
  - Visual feedback for Available (Peach) vs. Reserved (Grey) seats.
  - "Themed" success and error pop-ups.
- **Admin Dashboard**:
  - View Pending, Confirmed, and Declined reservations.
  - **Accept/Decline**: One-click management with "Undo" capability.
  - **Manual Email**: Manually trigger "You're In!" confirmation emails to guests.
  - **Locks**: Reservations are locked once the confirmation email is sent.
  - Dashboard is protected by login.

## Setup & Installation

1.  **Clone the repository** (if applicable) or download the source.
2.  **Install Dependencies**:
    ```bash
    pip install flask flask-sqlalchemy
    ```
3.  **Initialize the Database**:
    Run the reset script to create the database table:
    ```bash
    python3 reset_db.py
    ```

## Running the Application

1.  Start the Flask server:
    ```bash
    python3 app.py
    ```
2.  Open your browser and navigate to:
    - **Homepage**: `http://127.0.0.1:5000/`
    - **Admin Dashboard**: `http://127.0.0.1:5000/admin`

## Admin Credentials

- **Username**: `admin`
- **Password**: `password123`

*(Note: Update these in `app.py` before deploying to a public server!)*

## Usage Guide for Admin

1.  **Pending Reservations**: New RSVPs appear here. Click **Accept** to move them to the Guest List, or **Decline** to remove them.
2.  **Confirmed Guests**:
    - **Undo (Decline)**: Did you accept by mistake? Click this to release the seat.
    - **Send Email**: When ready, click this to send the confirmation email.
    - **Locked**: Once emailed, the record is locked to prevent accidental changes.
3.  **Declined**:
    - **Undo (Accept)**: Did you decline by mistake? Click this to restore their seat (if still available).

## Customization

- **Fonts**: The "Holiday" font is used for headers.
- **Colors**: Defined in `static/style.css` (Peach/Salmon theme).