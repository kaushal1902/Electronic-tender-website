from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, SelectField, FloatField, IntegerField, DateTimeLocalField, DateField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, NumberRange, Optional
from datetime import datetime

class RegistrationForm(FlaskForm):
    """Form for user registration with company information"""
    # Personal information
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField('Phone Number', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=60)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    # Company information
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=150)])
    company_registration_number = StringField('Company Registration Number', validators=[DataRequired(), Length(max=50)])
    company_tax_id = StringField('Tax ID / VAT Number', validators=[Length(max=50)])
    company_website = StringField('Company Website', validators=[Length(max=150)])
    company_founded_year = IntegerField('Year Founded', validators=[NumberRange(min=1800, max=datetime.now().year)])
    
    company_size = SelectField('Company Size', choices=[
        ('', 'Select Size'),
        ('micro', 'Micro (1-9 employees)'),
        ('small', 'Small (10-49 employees)'),
        ('medium', 'Medium (50-249 employees)'),
        ('large', 'Large (250+ employees)')
    ], validators=[DataRequired()])
    
    industry_sector = SelectField('Electronics Industry Sector', choices=[
        ('', 'Select Electronics Sector'),
        ('consumer_electronics', 'Consumer Electronics'),
        ('computer_hardware', 'Computer Hardware & Accessories'),
        ('electronic_manufacturing', 'Electronic Manufacturing'),
        ('telecommunications', 'Telecommunications'),
        ('semiconductor', 'Semiconductor'),
        ('electronic_components', 'Electronic Components'),
        ('electronic_distribution', 'Electronic Distribution'),
        ('electronic_repair', 'Electronic Repair & Maintenance'),
        ('iot_devices', 'IoT & Smart Devices'),
        ('electronic_design', 'Electronic Design & Engineering'),
        ('circuit_board', 'Circuit Board Assembly'),
        ('other_electronics', 'Other Electronics')
    ], validators=[DataRequired()])
    
    business_description = TextAreaField('Business Description', validators=[Length(max=500)])
    company_address = TextAreaField('Company Address', validators=[DataRequired(), Length(max=200)])
    
    submit = SubmitField('Register')

class OTPVerificationForm(FlaskForm):
    """Form for OTP verification"""
    otp = StringField('Enter OTP', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('Verify')

class LoginForm(FlaskForm):
    """Form for user login"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    captcha = StringField('Enter CAPTCHA', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProfileForm(FlaskForm):
    """Form for user profile update with company information"""
    # Personal information
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone Number', validators=[Length(max=20)])
    
    # Company information
    company_name = StringField('Company Name', validators=[DataRequired(), Length(max=150)])
    company_registration_number = StringField('Company Registration Number', validators=[DataRequired(), Length(max=50)])
    company_tax_id = StringField('Tax ID / VAT Number', validators=[Length(max=50)])
    company_website = StringField('Company Website', validators=[Length(max=150)])
    company_founded_year = IntegerField('Year Founded', validators=[NumberRange(min=1800, max=datetime.now().year)])
    
    company_size = SelectField('Company Size', choices=[
        ('', 'Select Size'),
        ('micro', 'Micro (1-9 employees)'),
        ('small', 'Small (10-49 employees)'),
        ('medium', 'Medium (50-249 employees)'),
        ('large', 'Large (250+ employees)')
    ], validators=[DataRequired()])
    
    industry_sector = SelectField('Electronics Industry Sector', choices=[
        ('', 'Select Electronics Sector'),
        ('consumer_electronics', 'Consumer Electronics'),
        ('computer_hardware', 'Computer Hardware & Accessories'),
        ('electronic_manufacturing', 'Electronic Manufacturing'),
        ('telecommunications', 'Telecommunications'),
        ('semiconductor', 'Semiconductor'),
        ('electronic_components', 'Electronic Components'),
        ('electronic_distribution', 'Electronic Distribution'),
        ('electronic_repair', 'Electronic Repair & Maintenance'),
        ('iot_devices', 'IoT & Smart Devices'),
        ('electronic_design', 'Electronic Design & Engineering'),
        ('circuit_board', 'Circuit Board Assembly'),
        ('other_electronics', 'Other Electronics')
    ], validators=[DataRequired()])
    
    business_description = TextAreaField('Business Description', validators=[Length(max=500)])
    company_address = TextAreaField('Company Address', validators=[DataRequired(), Length(max=200)])
    
    submit = SubmitField('Update Profile')

class TenderForm(FlaskForm):
    """Form for creating and editing tenders"""
    title = StringField('Tender Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    category = SelectField('Electronics Category', validators=[DataRequired()], choices=[
        ('consumer_electronics', 'Consumer Electronics'),
        ('computer_hardware', 'Computer Hardware'),
        ('electronic_components', 'Electronic Components'),
        ('telecommunications', 'Telecommunications'),
        ('audio_video', 'Audio/Video Equipment'),
        ('office_electronics', 'Office Electronics'),
        ('electronic_services', 'Electronic Services'),
        ('iot_devices', 'IoT Devices'),
        ('other_electronics', 'Other Electronics')
    ])
    budget = FloatField('Budget (INR)', validators=[DataRequired(), NumberRange(min=0)])
    requirements = TextAreaField('Requirements')
    submission_deadline = DateTimeLocalField('Submission Deadline', 
                                            format='%Y-%m-%dT%H:%M',
                                            validators=[DataRequired()],
                                            default=datetime.now)
    submit = SubmitField('Save Tender')

    def validate_submission_deadline(self, field):
        if field.data < datetime.now():
            raise ValidationError('Deadline must be in the future')

class TenderApplicationForm(FlaskForm):
    """Form for submitting tender applications"""
    proposal = TextAreaField('Your Proposal', validators=[DataRequired()])
    price_quote = FloatField('Price Quote (INR)', validators=[DataRequired(), NumberRange(min=0)])
    completion_time = IntegerField('Completion Time (days)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Submit Application')

class TenderSearchForm(FlaskForm):
    """Form for searching and filtering tenders"""
    category = SelectField('Electronics Category', choices=[
        ('', 'All Categories'),
        ('consumer_electronics', 'Consumer Electronics'),
        ('computer_hardware', 'Computer Hardware'),
        ('electronic_components', 'Electronic Components'),
        ('telecommunications', 'Telecommunications'),
        ('audio_video', 'Audio/Video Equipment'),
        ('office_electronics', 'Office Electronics'),
        ('electronic_services', 'Electronic Services'),
        ('iot_devices', 'IoT Devices'),
        ('other_electronics', 'Other Electronics')
    ], validators=[Optional()])
    submit = SubmitField('Filter')

class EmailSettingsForm(FlaskForm):
    """Form for email server settings"""
    mail_server = StringField('SMTP Server', validators=[DataRequired(), Length(max=100)])
    mail_port = IntegerField('Port', validators=[DataRequired(), NumberRange(min=1, max=65535)])
    mail_username = StringField('Username', validators=[DataRequired(), Length(max=100)])
    mail_password = PasswordField('Password', validators=[DataRequired(), Length(max=100)])
    mail_use_tls = BooleanField('Use TLS')
    mail_use_ssl = BooleanField('Use SSL')
    mail_default_sender = StringField('Default Sender Email', validators=[DataRequired(), Email(), Length(max=100)])
    submit = SubmitField('Save Settings')
