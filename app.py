import os
import logging
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_mail import Mail, Message
from sqlalchemy.orm import DeclarativeBase
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


# Create base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

# Create the Flask application
app = Flask(__name__)

# Add custom Jinja2 filters
@app.template_filter('nl2br')
def nl2br_filter(text):
    if not text:
        return ""
    return text.replace('\n', '<br>')

# Configure the application
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-here")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///tender.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME",
                                             "kaushaldangodra@gmail.com")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD",
                                             "igmd qqph uxrb oxom")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER",
                                                   "kaushaldangodra.com")

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'
mail.init_app(app)

# Import models and routes
with app.app_context():
    from models import User, Role, Tender, TenderApplication, OTPVerification
    import forms
    from utils import send_verification_email, generate_captcha, send_tender_winner_notification, send_tender_result_notification

    # Create database tables
    db.create_all()

    # Create roles if they don't exist
    if not Role.query.filter_by(name='admin').first():
        admin_role = Role(name='admin', description='Administrator')
        db.session.add(admin_role)

    if not Role.query.filter_by(name='user').first():
        user_role = Role(name='user', description='Regular User')
        db.session.add(user_role)

    db.session.commit()

    # Run the database migration to add company fields
    try:
        import migrate_db
        migration_success = migrate_db.run_migration()
        if migration_success:
            app.logger.info("Database migration completed successfully")
        else:
            app.logger.warning("Database migration was not successful")
    except Exception as e:
        app.logger.error(f"Error running database migration: {str(e)}")

    # Create admin user if it doesn't exist
    if not User.query.filter_by(email='kaushaldangodra781@gmail.com').first():
        admin_role = Role.query.filter_by(name='admin').first()
        admin_user = User(
            name='Administrator',
            email='kaushaldangodra781@gmail.com',
            password_hash=generate_password_hash('admin123'),
            is_verified=True,
            # Add default values for company fields
            company_name='Admin Company',
            company_registration_number='ADMIN001',
            company_tax_id='TAX001',
            company_website='admin.example.com',
            company_founded_year=2023,
            company_size='small',
            industry_sector='information_technology',
            business_description='Administration services',
            company_address='Admin Office Address')
        admin_user.roles.append(admin_role)
        db.session.add(admin_user)
        db.session.commit()


# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))


# Routes
@app.route('/')
def index():
    from models import Tender
    if current_user.is_authenticated and 'admin' in [role.name for role in current_user.roles]:
        # For admin, show all tenders
        return redirect(url_for('admin_dashboard'))
    else:
        # For regular users, show only active tenders
        tenders = Tender.query.filter(
            (Tender.submission_deadline >= datetime.now()) &
            (Tender.status == 'active')
        ).order_by(Tender.created_at.desc()).limit(10).all()
        return render_template('index.html', tenders=tenders)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    from forms import RegistrationForm
    form = RegistrationForm()

    if form.validate_on_submit():
        from models import User, Role, OTPVerification

        # Check if user already exists
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered', 'danger')
            return render_template('register.html', form=form)

        # Create new user with company information
        user = User(
            name=form.name.data,
            email=form.email.data,
            phone=form.phone.data,
            password_hash=generate_password_hash(form.password.data),
            company_name=form.company_name.data,
            company_registration_number=form.company_registration_number.data,
            company_tax_id=form.company_tax_id.data,
            company_website=form.company_website.data,
            company_founded_year=form.company_founded_year.data,
            company_size=form.company_size.data,
            industry_sector=form.industry_sector.data,
            business_description=form.business_description.data,
            company_address=form.company_address.data,
            is_verified=False)

        # Add user role
        user_role = Role.query.filter_by(name='user').first()
        user.roles.append(user_role)

        db.session.add(user)
        db.session.commit()

        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        otp_expiry = datetime.now() + timedelta(minutes=15)

        # Store OTP
        verification = OTPVerification(user_id=user.id,
                                       otp=otp,
                                       expires_at=otp_expiry)
        db.session.add(verification)
        db.session.commit()

        # Send verification email
        from utils import send_verification_email
        try:
            if send_verification_email(user, otp):
                flash(
                    'Registration successful! Please check your email for verification OTP.',
                    'success')
                return redirect(url_for('verify', user_id=user.id))
            else:
                raise Exception("Failed to send email")
        except Exception as e:
            app.logger.error(f"Failed to send email: {str(e)}")
            flash(
                'Registration successful but failed to send verification email. Please try to login.',
                'warning')
            return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/verify/<int:user_id>', methods=['GET', 'POST'])
def verify(user_id):
    from models import User, OTPVerification
    from forms import OTPVerificationForm

    user = User.query.get_or_404(user_id)

    if user.is_verified:
        flash('Your account is already verified. Please login.', 'info')
        return redirect(url_for('login'))

    form = OTPVerificationForm()

    if form.validate_on_submit():
        otp = form.otp.data
        verification = OTPVerification.query.filter_by(
            user_id=user.id).order_by(
                OTPVerification.created_at.desc()).first()

        if not verification:
            flash('OTP not found. Please request a new one.', 'danger')
            return render_template('verify.html', form=form, user_id=user_id)

        if verification.expires_at < datetime.now():
            flash('OTP has expired. Please request a new one.', 'danger')
            return render_template('verify.html', form=form, user_id=user_id)

        if verification.otp != otp:
            flash('Invalid OTP. Please try again.', 'danger')
            return render_template('verify.html', form=form, user_id=user_id)

        # Verify user
        user.is_verified = True
        db.session.commit()

        flash(
            'Your account has been verified successfully! You can now login.',
            'success')
        return redirect(url_for('login'))

    return render_template('verify.html', form=form, user_id=user_id)


@app.route('/resend-otp/<int:user_id>', methods=['POST'])
def resend_otp(user_id):
    from models import User, OTPVerification

    user = User.query.get_or_404(user_id)

    if user.is_verified:
        flash('Your account is already verified. Please login.', 'info')
        return redirect(url_for('login'))

    # Generate new OTP
    otp = ''.join(random.choices(string.digits, k=6))
    otp_expiry = datetime.now() + timedelta(minutes=15)

    # Store OTP
    verification = OTPVerification(user_id=user.id,
                                   otp=otp,
                                   expires_at=otp_expiry)
    db.session.add(verification)
    db.session.commit()

    # Send verification email
    from utils import send_verification_email
    try:
        if send_verification_email(user, otp):
            flash('A new OTP has been sent to your email.', 'success')
        else:
            flash('Failed to send OTP email. Please try again later.',
                  'danger')
    except Exception as e:
        app.logger.error(f"Failed to send OTP email: {str(e)}")
        flash('Failed to send OTP email. Please try again later.', 'danger')

    return redirect(url_for('verify', user_id=user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    from forms import LoginForm
    form = LoginForm()

    if request.method == 'GET':
        # Generate captcha for new login page load
        captcha_text = ''.join(
            random.choices(string.ascii_uppercase + string.digits, k=6))
        session['captcha'] = captcha_text

    if form.validate_on_submit():
        from models import User

        # Verify captcha
        if form.captcha.data.upper() != session.get('captcha', ''):
            flash('Invalid CAPTCHA code. Please try again.', 'danger')
            # Generate new captcha
            captcha_text = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6))
            session['captcha'] = captcha_text
            return render_template('login.html', form=form)

        # Find user by email
        user = User.query.filter_by(email=form.email.data).first()

        # Check if user exists and password is correct
        if not user or not check_password_hash(user.password_hash,
                                               form.password.data):
            flash('Invalid email or password', 'danger')
            # Generate new captcha
            captcha_text = ''.join(
                random.choices(string.ascii_uppercase + string.digits, k=6))
            session['captcha'] = captcha_text
            return render_template('login.html', form=form)

        # Check if user is verified
        if not user.is_verified:
            flash(
                'Your account is not verified. Please verify your email first.',
                'warning')
            return redirect(url_for('verify', user_id=user.id))

        # Login the user
        login_user(user, remember=form.remember_me.data)

        # Redirect to the next page or dashboard
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            if 'admin' in [role.name for role in user.roles]:
                next_page = url_for('admin_dashboard')
            else:
                next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    from forms import ProfileForm

    # Check if user is an admin
    is_admin = 'admin' in [
        role.name for role in current_user.roles
    ] if hasattr(current_user, 'roles') and current_user.roles else False

    # If it's an admin user, redirect to admin dashboard
    if is_admin:
        flash(
            'As an administrator, you do not need to maintain a company profile.',
            'info')
        return redirect(url_for('admin_dashboard'))

    form = ProfileForm(obj=current_user)

    if form.validate_on_submit():
        # Update user personal information
        current_user.name = form.name.data
        current_user.phone = form.phone.data

        # Update company information
        current_user.company_name = form.company_name.data
        current_user.company_registration_number = form.company_registration_number.data
        current_user.company_tax_id = form.company_tax_id.data
        current_user.company_website = form.company_website.data
        current_user.company_founded_year = form.company_founded_year.data
        current_user.company_size = form.company_size.data
        current_user.industry_sector = form.industry_sector.data
        current_user.business_description = form.business_description.data
        current_user.company_address = form.company_address.data

        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('profile'))

    return render_template('profile.html', form=form)


@app.route('/tenders')
def tenders():
    from models import Tender, TenderApplication

    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')

    # Check if user is admin
    is_admin = current_user.is_authenticated and 'admin' in [role.name for role in current_user.roles]

    if is_admin:
        tenders_query = Tender.query
    else:
        tenders_query = Tender.query.filter(
            (Tender.submission_deadline >= datetime.now()) &
            (Tender.status == 'active')
        )

    # Apply category filter if selected
    if category:
        tenders_query = tenders_query.filter(Tender.category == category)

    # Get all unique categories for the filter dropdown
    categories = db.session.query(Tender.category).distinct().all()
    categories = [cat[0] for cat in categories]

    # Default sorting by submission deadline
    tenders_query = tenders_query.order_by(Tender.submission_deadline.asc())

    # Paginate the results
    tenders = tenders_query.paginate(page=page, per_page=10)

    return render_template('tenders.html', 
                         tenders=tenders, 
                         categories=categories,
                         category=category)


@app.route('/tenders/<int:tender_id>')
def tender_details(tender_id):
    from models import Tender, TenderApplication

    try:
        tender = Tender.query.get_or_404(tender_id)

        user_application = None
        if current_user.is_authenticated:
            user_application = TenderApplication.query.filter_by(
                tender_id=tender_id, user_id=current_user.id).first()

        # Ensure winner is loaded if selected
        winner = None
        if tender.winner_selected and tender.winner_id:
            winner = TenderApplication.query.get(tender.winner_id)

        current_time = datetime.now()

        return render_template('tender_details.html',
                            tender=tender,
                            user_application=user_application,
                            now=current_time,
                            winner=winner)
    except Exception as e:
        app.logger.error(f"Error in tender_details: {str(e)}")
        return render_template('500.html'), 500


@app.route('/tenders/<int:tender_id>/apply', methods=['GET', 'POST'])
@login_required
def apply_tender(tender_id):
    from models import Tender, TenderApplication
    from forms import TenderApplicationForm

    tender = Tender.query.get_or_404(tender_id)

    # Check if tender is still open
    if tender.submission_deadline < datetime.now():
        flash('This tender is no longer accepting applications.', 'warning')
        return redirect(url_for('tender_details', tender_id=tender_id))

    # Check if user already applied
    existing_application = TenderApplication.query.filter_by(
        tender_id=tender_id, user_id=current_user.id).first()

    if existing_application:
        flash('You have already applied for this tender.', 'info')
        return redirect(url_for('tender_details', tender_id=tender_id))

    form = TenderApplicationForm()

    if form.validate_on_submit():
        application = TenderApplication(
            tender_id=tender.id,
            user_id=current_user.id,
            proposal=form.proposal.data,
            price_quote=form.price_quote.data,
            completion_time=form.completion_time.data,
            status='pending')

        db.session.add(application)
        db.session.commit()

        flash('Your application has been submitted successfully!', 'success')
        return redirect(url_for('tender_details', tender_id=tender_id))

    return render_template('apply_tender.html', form=form, tender=tender)


@app.route('/my-applications')
@login_required
def my_applications():
    from models import TenderApplication

    applications = TenderApplication.query.filter_by(
        user_id=current_user.id).all()

    return render_template('my_applications.html', applications=applications)


# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    from models import User, Tender, TenderApplication

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get statistics for dashboard
    total_users = User.query.filter_by(is_verified=True).count()
    total_tenders = Tender.query.count()
    active_tenders = Tender.query.filter(
        Tender.submission_deadline >= datetime.now()).count()
    total_applications = TenderApplication.query.count()
    pending_applications = TenderApplication.query.filter_by(
        status='pending').count()

    # Get recent tenders
    recent_tenders = Tender.query.order_by(
        Tender.created_at.desc()).limit(5).all()

    # Get recent applications
    recent_applications = TenderApplication.query.order_by(
        TenderApplication.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           total_tenders=total_tenders,
                           active_tenders=active_tenders,
                           total_applications=total_applications,
                           pending_applications=pending_applications,
                           recent_tenders=recent_tenders,
                           recent_applications=recent_applications,
                           now=datetime.now())


@app.route('/admin/applications')
@login_required
def admin_applications():
    from models import TenderApplication

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.', 'danger')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    applications = TenderApplication.query.order_by(TenderApplication.created_at.desc()).paginate(page=page, per_page=10)

    return render_template('admin/applications.html', applications=applications)

@app.route('/admin/tenders', methods=['GET', 'POST'])
@login_required
def admin_tenders():
    from models import Tender

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Handle status update
    if request.method == 'POST':
        tender_id = request.form.get('tender_id')
        new_status = request.form.get('status')
        if tender_id and new_status:
            tender = Tender.query.get_or_404(tender_id)
            tender.status = new_status
            db.session.commit()
            flash('Tender status updated successfully!', 'success')

    page = request.args.get('page', 1, type=int)
    tenders = Tender.query.order_by(Tender.created_at.desc()).paginate(
        page=page, per_page=10)

    return render_template('admin/tenders.html',
                           tenders=tenders,
                           now=datetime.now())


@app.route('/admin/tenders/create', methods=['GET', 'POST'])
@login_required
def create_tender():
    from models import Tender
    from forms import TenderForm

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    form = TenderForm()

    if form.validate_on_submit():
        tender = Tender(title=form.title.data,
                        description=form.description.data,
                        category=form.category.data,
                        budget=form.budget.data,
                        submission_deadline=form.submission_deadline.data,
                        requirements=form.requirements.data)

        db.session.add(tender)
        db.session.commit()

        flash('Tender created successfully!', 'success')
        return redirect(url_for('admin_tenders'))

    return render_template('admin/add_edit_tender.html',
                           form=form,
                           title='Create Tender')


@app.route('/admin/tenders/<int:tender_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_tender(tender_id):
    from models import Tender
    from forms import TenderForm

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    tender = Tender.query.get_or_404(tender_id)
    form = TenderForm(obj=tender)

    if form.validate_on_submit():
        tender.title = form.title.data
        tender.description = form.description.data
        tender.category = form.category.data
        tender.budget = form.budget.data
        tender.submission_deadline = form.submission_deadline.data
        tender.requirements = form.requirements.data

        db.session.commit()

        flash('Tender updated successfully!', 'success')
        return redirect(url_for('admin_tenders'))

    return render_template('admin/add_edit_tender.html',
                           form=form,
                           tender=tender,
                           title='Edit Tender')


@app.route('/admin/applications/<int:application_id>')
@login_required
def application_details(application_id):
    from models import TenderApplication

    # Get application
    application = TenderApplication.query.get_or_404(application_id)

    # Check if user has admin role
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. Administrative privileges required.', 'danger')
        return redirect(url_for('index'))

    return render_template('admin/application_details.html', application=application)

@app.route('/admin/applications/<int:application_id>/update-status', methods=['POST'])
@login_required
def update_application_status(application_id):
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. Administrative privileges required.', 'danger')
        return redirect(url_for('index'))

    application = TenderApplication.query.get_or_404(application_id)
    application.status = request.form.get('status')
    application.admin_remarks = request.form.get('admin_remarks')

    db.session.commit()

    # Send email notification about status update
    from utils import send_application_status_update
    try:
        if send_application_status_update(application):
            flash('Application status updated and notification sent successfully', 'success')
        else:
            flash('Application status updated but notification failed to send', 'warning')
    except Exception as e:
        app.logger.error(f"Error sending status update notification: {str(e)}")
        flash('Application status updated but notification failed to send', 'warning')

    return redirect(url_for('application_details', application_id=application_id))

@app.route('/admin/tenders/<int:tender_id>/delete', methods=['POST'])
@login_required
def delete_tender(tender_id):
    from models import Tender

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    tender = Tender.query.get_or_404(tender_id)

    db.session.delete(tender)
    db.session.commit()

    flash('Tender deleted successfully!', 'success')
    return redirect(url_for('admin_tenders'))





@app.route('/admin/tenders/<int:tender_id>/rankings')
@login_required
def tender_rankings(tender_id):
    from models import Tender, TenderApplication

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    tender = Tender.query.get_or_404(tender_id)

    # Update rankings
    applications = tender.update_application_rankings()
    db.session.commit()

    # Get applications with rankings
    ranked_applications = TenderApplication.query.filter_by(
        tender_id=tender_id,
        status='approved').order_by(TenderApplication.ranking).all()

    return render_template('admin/tender_rankings.html',
                           tender=tender,
                           applications=ranked_applications,
                           winner=tender.winner)


@app.route('/admin/tenders/<int:tender_id>/select-winner', methods=['POST'])
@login_required
def select_tender_winner(tender_id):
    from models import Tender
    from utils import send_tender_winner_notification, send_application_status_update, send_tender_result_notification

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('tender_rankings', tender_id=tender_id))

    tender = Tender.query.get_or_404(tender_id)

    # Check if tender is still open
    if tender.is_open:
        flash('Cannot select a winner while the tender is still open.',
              'warning')
        return redirect(url_for('tender_rankings', tender_id=tender_id))

    # Select winner
    success, message = tender.select_winner()

    if success:
        # Send notifications
        if tender.winner:
            try:
                # Send congratulatory notification to winner
                from utils import send_tender_winner_notification, send_tender_result_notification

                winner_notified = send_tender_winner_notification(tender.winner)

                # Send notifications to other applicants
                other_applicants_notified = True
                for application in tender.applications:
                    if application.id != tender.winner_id:
                        application.status = 'rejected'
                        if not send_tender_result_notification(application, tender.winner):
                            other_applicants_notified = False

                if winner_notified and other_applicants_notified:
                    flash('Winner selected and all notifications sent successfully!', 'success')
                else:
                    flash('Winner selected but some notifications failed to send.', 'warning')

            except Exception as e:
                app.logger.error(f"Error sending notifications: {str(e)}")
                db.session.commit()  # Save winner selection even if notifications fail
                flash('Winner selected successfully, but there was an error sending notifications.', 'warning')
        else:
            flash('Winner selected, but no winner found to notify.', 'warning')
    else:
        flash(message, 'danger')

    db.session.commit()
    return redirect(url_for('tender_rankings', tender_id=tender_id))


@app.route('/admin/users')
@login_required
def admin_users():
    from models import User, Role

    #Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get search query if any
    search_query = request.args.get('search', '')

    # Filter users - exclude admin users and the current admin
    query = User.query

    # Apply search if provided
    if search_query:
        query = query.filter((User.name.ilike(f'%{search_query}%'))
                             | (User.email.ilike(f'%{search_query}%')))

    # Get all users except the current admin
    query = query.filter(User.id != current_user.id)

    # Paginate results
    page = request.args.get('page', 1, type=int)
    users = query.order_by(User.created_at.desc()).paginate(page=page,
                                                            per_page=10)

    return render_template('admin/users.html', users=users)


# Analytics routes
@app.route('/admin/analytics/dashboard')
@login_required
def analytics_dashboard():
    from analytics import TenderAnalytics

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get analytics data
    summary_stats = TenderAnalytics.get_summary_stats()
    tender_completion = TenderAnalytics.get_tender_completion_rate()
    
    # Get analytics data
    summary_stats = TenderAnalytics.get_summary_stats()

    # Generate charts
    charts = {
        'tender_activity':
        TenderAnalytics.generate_chart_tender_activity(days=30),
        'categories':
        TenderAnalytics.generate_chart_categories_distribution(),
        'budget':
        TenderAnalytics.generate_chart_budget_distribution(),
        'application_status':
        TenderAnalytics.generate_chart_application_status(),
        'monthly_activity':
        TenderAnalytics.generate_chart_monthly_activity(months=12),
        'user_growth':
        TenderAnalytics.generate_chart_user_growth(months=12)
    }

    return render_template('admin/analytics/dashboard.html',
                           summary_stats=summary_stats,
                           tender_completion=tender_completion,
                           charts=charts)


@app.route('/admin/analytics/tenders')
@login_required
def analytics_tenders():
    from analytics import TenderAnalytics
    from models import Tender

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get analytics data
    categories_df = TenderAnalytics.get_tender_categories_distribution()
    budget_df = TenderAnalytics.get_tender_budget_distribution()

    # Convert dataframes to lists for the template
    categories_data = [{
        'category': row['category'],
        'name': row['category_name'],
        'count': row['count']
    } for _, row in categories_df.iterrows()]

    budget_data = [{
        'range': row['range'],
        'count': row['count']
    } for _, row in budget_df.iterrows()]

    # Generate charts
    charts = {
        'categories':
        TenderAnalytics.generate_chart_categories_distribution(),
        'budget':
        TenderAnalytics.generate_chart_budget_distribution(),
        'monthly_activity':
        TenderAnalytics.generate_chart_monthly_activity(months=12)
    }

    # Export functionality
    export_data = TenderAnalytics.export_tender_data_csv()

    return render_template('admin/analytics/tenders.html',
                           categories_data=categories_data,
                           budget_data=budget_data,
                           charts=charts,
                           export_data=export_data)


@app.route('/admin/analytics/applications')
@login_required
def analytics_applications():
    from analytics import TenderAnalytics

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get analytics data
    status_df = TenderAnalytics.get_application_status_distribution()

    # Convert dataframe to list for the template
    status_data = [{
        'status': row['status'],
        'name': row['status_name'],
        'count': row['count']
    } for _, row in status_df.iterrows()]

    # Generate charts
    charts = {
        'application_status':
        TenderAnalytics.generate_chart_application_status(),
        'tender_activity':
        TenderAnalytics.generate_chart_tender_activity(days=90)
    }

    # Export functionality
    export_data = TenderAnalytics.export_applications_data_csv()

    return render_template('admin/analytics/applications.html',
                           status_data=status_data,
                           charts=charts,
                           export_data=export_data)


@app.route('/admin/analytics/users')
@login_required
def analytics_users():
    from analytics import TenderAnalytics

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    # Get analytics data
    sector_df = TenderAnalytics.get_industry_sector_distribution()
    size_df = TenderAnalytics.get_company_size_distribution()

    # Convert dataframes to lists for the template
    sector_data = [{
        'sector': row['sector'],
        'name': row['sector_name'],
        'count': row['count']
    } for _, row in sector_df.iterrows()]

    size_data = [{
        'size': row['size'],
        'name': row['size_name'],
        'count': row['count']
    } for _, row in size_df.iterrows()]

    # Generate charts
    charts = {
        'industry_sectors': TenderAnalytics.generate_chart_industry_sectors(),
        'company_sizes': TenderAnalytics.generate_chart_company_sizes(),
        'user_growth': TenderAnalytics.generate_chart_user_growth(months=12)
    }

    return render_template('admin/analytics/users.html',
                           sector_data=sector_data,
                           size_data=size_data,
                           charts=charts)


@app.route('/admin/email-settings', methods=['GET', 'POST'])
@login_required
def admin_email_settings():
    from forms import EmailSettingsForm

    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied. You do not have administrative privileges.',
              'danger')
        return redirect(url_for('index'))

    form = EmailSettingsForm()

    if request.method == 'GET':
        # Load current settings into the form
        form.mail_server.data = app.config.get('MAIL_SERVER')
        form.mail_port.data = app.config.get('MAIL_PORT')
        form.mail_username.data = app.config.get('MAIL_USERNAME')
        form.mail_password.data = app.config.get('MAIL_PASSWORD')
        form.mail_use_tls.data = app.config.get('MAIL_USE_TLS', False)
        form.mail_use_ssl.data = app.config.get('MAIL_USE_SSL', False)
        form.mail_default_sender.data = app.config.get(
            'MAIL_DEFAULT_SENDER') or app.config.get('MAIL_USERNAME')

    if form.validate_on_submit():
        try:
            # Update app configuration with new settings
            app.config['MAIL_SERVER'] = form.mail_server.data
            app.config['MAIL_PORT'] = form.mail_port.data
            app.config['MAIL_USERNAME'] = form.mail_username.data
            app.config['MAIL_PASSWORD'] = form.mail_password.data
            app.config['MAIL_USE_TLS'] = form.mail_use_tls.data
            app.config['MAIL_USE_SSL'] = form.mail_use_ssl.data
            app.config['MAIL_DEFAULT_SENDER'] = form.mail_default_sender.data

            # Recreate mail instance with new settings
            mail.init_app(app)

            # Save settings in a JSON file for persistence across restarts
            email_settings = {
                'MAIL_SERVER': form.mail_server.data,
                'MAIL_PORT': form.mail_port.data,
                'MAIL_USERNAME': form.mail_username.data,
                'MAIL_PASSWORD': form.mail_password.data,
                'MAIL_USE_TLS': form.mail_use_tls.data,
                'MAIL_USE_SSL': form.mail_use_ssl.data,
                'MAIL_DEFAULT_SENDER': form.mail_default_sender.data
            }

            with open('instance/email_settings.json', 'w') as f:
                json.dump(email_settings, f)

            flash('Email settings updated successfully!', 'success')
            return redirect(url_for('admin_email_settings'))

        except Exception as e:
            app.logger.error(f"Error updating email settings: {str(e)}")
            flash(f'Error updating email settings: {str(e)}', 'danger')

    return render_template('admin/email_settings.html', form=form)


@app.route('/admin/test-email', methods=['POST'])
@login_required
def admin_test_email():
    # Check if user is an admin
    if 'admin' not in [role.name for role in current_user.roles]:
        return jsonify({'success': False, 'error': 'Access denied'})

    data = request.json
    if not data or 'email' not in data:
        return jsonify({
            'success': False,
            'error': 'No email address provided'
        })

    recipient = data['email']

    try:
        msg = Message(subject='Test Email from TenderVista',
                      recipients=[recipient],
                      body=f"""
Hello,

This is a test email from TenderVista.

If you're receiving this email, your email settings are configured correctly.

Time sent: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Best regards,
TenderVista Team
            """)
        mail.send(msg)
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error sending test email: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.route('/application/<int:application_id>/download')
@login_required
def download_application(application_id):
    from models import TenderApplication
    import io
    from flask import send_file
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.units import inch

    # Get application
    application = TenderApplication.query.get_or_404(application_id)

    # Check if user owns this application or is admin
    if not (current_user.id == application.user_id or 
            'admin' in [role.name for role in current_user.roles]):
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    story.append(Paragraph("TENDER APPLICATION DETAILS", title_style))

    # Basic Information
    content = [
        f"<b>Application ID:</b> {application.id}",
        f"<b>Submission Date:</b> {application.created_at.strftime('%Y-%m-%d %H:%M')}",
        f"<b>Status:</b> {application.status.upper()}",
        "<br/><br/>",
        "<b>TENDER INFORMATION</b>",
        f"<b>Title:</b> {application.tender.title}",
        f"<b>Category:</b> {application.tender.category.replace('_', ' ').title()}",
        f"<b>Budget:</b> ₹{application.tender.budget:,.2f}",
        "<br/><br/>",
        "<b>APPLICANT INFORMATION</b>",
        f"<b>Company:</b> {application.user.company_name}",
        f"<b>Contact Person:</b> {application.user.name}",
        f"<b>Email:</b> {application.user.email}",
        f"<b>Phone:</b> {application.user.phone}",
        "<br/><br/>",
        "<b>APPLICATION DETAILS</b>",
        f"<b>Price Quote:</b> ₹{application.price_quote:,.2f}",
        f"<b>Completion Time:</b> {application.completion_time} days",
        f"<b>Bid Score:</b> {application.bid_score}/100",
        f"<b>Ranking:</b> {application.ranking if application.ranking > 0 else 'Not ranked'}",
        "<br/><br/>",
        "<b>PROPOSAL</b>",
        application.proposal,
        "<br/><br/>",
        f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    ]

    for line in content:
        story.append(Paragraph(line, styles["Normal"]))
        story.append(Spacer(1, 12))

    # Build PDF
    doc.build(story)
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'tender_application_{application.id}.pdf',
        mimetype='application/pdf'
    )

@app.route('/faq')
def faq():
    return render_template('faq.html')

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

@app.route('/admin/tenders/<int:tender_id>/close', methods=['POST'])
@login_required
def close_tender(tender_id):
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied.', 'danger')
        return redirect(url_for('index'))

    tender = Tender.query.get_or_404(tender_id)
    tender.status = 'closed'
    db.session.commit()
    flash('Tender has been closed successfully.', 'success')
    return redirect(url_for('tender_rankings', tender_id=tender_id))

@app.route('/admin/tenders/<int:tender_id>/announce', methods=['POST'])
@login_required
def announce_winner(tender_id):
    if 'admin' not in [role.name for role in current_user.roles]:
        flash('Access denied.', 'danger')
        return redirect(url_for('tender_rankings', tender_id=tender_id))

    tender = Tender.query.get_or_404(tender_id)

    if not tender.winner_selected:
        flash('Please select a winner before announcing results.', 'warning')
        return redirect(url_for('tender_rankings', tender_id=tender_id))

    try:
        if tender.winner:
            # Send winner notification
            winner_notified = send_tender_winner_notification(tender.winner)
            tender.winner.notification_sent = True
            
            # Update and notify other applicants
            for application in tender.applications:
                if application.id != tender.winner_id:
                    application.status = 'rejected'
                    send_tender_result_notification(application, tender.winner)
            
            db.session.commit()
            flash('Results announced and notifications sent successfully!', 'success')
        else:
            flash('No winner found to announce.', 'danger')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error announcing winner: {str(e)}")
        flash('Error occurred while sending notifications.', 'danger')
    
    return redirect(url_for('tender_rankings', tender_id=tender_id))

    if success:
        try:
            # Send notifications to winner and other applicants
            if tender.winner:
                if send_tender_winner_notification(tender.winner):
                    # Update other applications and send notifications
                    for application in tender.applications:
                        if application.id != tender.winner_id:
                            application.status = 'rejected'
                            send_application_status_update(application)
                    flash('Winner announced and notifications sent successfully!', 'success')
                else:
                    flash('Winner selected but notifications failed to send.', 'warning')
        except Exception as e:
            app.logger.error(f"Error sending winner notifications: {str(e)}")
            flash('Winner selected but there was an error sending notifications.', 'warning')
    else:
        flash(message, 'danger')

    db.session.commit()
    return redirect(url_for('tender_rankings', tender_id=tender_id))

if __name__ == '__main__':
    app.run(debug=True)