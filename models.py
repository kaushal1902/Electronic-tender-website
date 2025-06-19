from datetime import datetime
from app import db
from flask_login import UserMixin

# Association table for many-to-many relationship between User and Role
user_roles = db.Table('user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    """User model for authentication and profile information"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(20))
    
    # Company related fields
    company_name = db.Column(db.String(150))
    company_registration_number = db.Column(db.String(50))
    company_tax_id = db.Column(db.String(50))
    company_website = db.Column(db.String(150))
    company_founded_year = db.Column(db.Integer)
    company_size = db.Column(db.String(50))  # Small, Medium, Large
    industry_sector = db.Column(db.String(100))
    business_description = db.Column(db.Text)
    company_address = db.Column(db.String(200))
    
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    roles = db.relationship('Role', secondary=user_roles, backref=db.backref('users', lazy='dynamic'))
    applications = db.relationship('TenderApplication', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    verifications = db.relationship('OTPVerification', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'
    
    def has_role(self, role_name):
        return any(role.name == role_name for role in self.roles)

class Role(db.Model):
    """Role model for user permissions"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<Role {self.name}>'

class Tender(db.Model):
    """Tender model for tender information"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100), nullable=False)
    budget = db.Column(db.Float, nullable=False)
    requirements = db.Column(db.Text)
    submission_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='active')  # active, inactive, closed
    winner_selected = db.Column(db.Boolean, default=False)
    winner_id = db.Column(db.Integer, db.ForeignKey('tender_application.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    applications = db.relationship('TenderApplication', backref='tender', lazy='dynamic', 
                                  primaryjoin="Tender.id==TenderApplication.tender_id", 
                                  cascade='all, delete-orphan', foreign_keys='TenderApplication.tender_id')
    winner = db.relationship('TenderApplication', uselist=False, 
                           primaryjoin="Tender.winner_id==TenderApplication.id", 
                           foreign_keys="Tender.winner_id", post_update=True)
    
    def __repr__(self):
        return f'<Tender {self.title}>'
    
    @property
    def is_open(self):
        if self.status == 'inactive':
            return False
        
        is_deadline_valid = datetime.now() <= self.submission_deadline
        current_status = self.status
        
        if not is_deadline_valid and current_status == 'active':
            self.status = 'closed'
            db.session.add(self)
            try:
                db.session.commit()
                # Auto-select winner when tender closes
                self.update_application_rankings()
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error updating tender status: {e}")
            
        return is_deadline_valid and self.status == 'active'

    def update_status(self):
        """Force update status based on current time"""
        is_deadline_valid = datetime.now() <= self.submission_deadline
        if not is_deadline_valid and self.status == 'active':
            self.status = 'closed'
            db.session.add(self)
            db.session.commit()
            return True
        return False
        
    def update_application_rankings(self):
        """Calculate bid scores and update rankings for all applications"""
        # Get all approved applications
        applications = TenderApplication.query.filter_by(
            tender_id=self.id, 
            status='approved'
        ).all()
        
        # Calculate bid scores for each application
        for app in applications:
            app.calculate_bid_score()
            
        # Sort applications by bid score (highest first)
        applications.sort(key=lambda x: x.bid_score, reverse=True)
        
        # Update rankings
        for i, app in enumerate(applications):
            app.ranking = i + 1  # Rankings start at 1
            
        return applications
        
    def select_winner(self):
        """Select the highest-ranked application as the winner"""
        if self.status == 'active':
            return False, "Cannot select a winner while tender is active."
            
        # Update rankings first
        applications = self.update_application_rankings()
        
        if not applications:
            return False, "No approved applications found for this tender."
        
        # Get the top-ranked application
        winner = applications[0] if applications else None
        
        if winner:
            # Reset any previous winner
            TenderApplication.query.filter_by(
                tender_id=self.id, 
                is_winner=True
            ).update({'is_winner': False, 'status': 'approved'})
            
            # Set new winner
            winner.is_winner = True
            winner.status = 'winner'
            self.winner_id = winner.id
            self.winner_selected = True
            
            return True, "Winner has been selected successfully."
        
        return False, "No suitable winner found."

class TenderApplication(db.Model):
    """TenderApplication model for tender applications"""
    id = db.Column(db.Integer, primary_key=True)
    tender_id = db.Column(db.Integer, db.ForeignKey('tender.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    proposal = db.Column(db.Text, nullable=False)
    price_quote = db.Column(db.Float, nullable=False)
    completion_time = db.Column(db.Integer, nullable=False)  # in days
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, winner
    admin_remarks = db.Column(db.Text)
    bid_score = db.Column(db.Float, default=0.0)  # Score calculated based on price, completion time, etc.
    ranking = db.Column(db.Integer, default=0)  # Ranking position compared to other applications
    is_winner = db.Column(db.Boolean, default=False)  # Whether this application was selected as winner
    notification_sent = db.Column(db.Boolean, default=False)  # Whether winner notification was sent
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<TenderApplication {self.id} - {self.status}>'
        
    def calculate_bid_score(self):
        """
        Calculate bid score based on price quote and completion time.
        Maximum score is 100 points:
        - Price (50 points): Lower price gets higher score
        - Time (50 points): Faster completion gets higher score
        """
        tender = Tender.query.get(self.tender_id)
        if not tender:
            return 0
            
        # Calculate price score (50 points max)
        # Full score if price is 30% below budget, zero if at or above budget
        price_factor = min(1.0, max(0, (tender.budget - self.price_quote) / (0.3 * tender.budget)))
        price_score = price_factor * 50
        
        # Calculate time score (50 points max)
        # Baseline is 30 days
        baseline_days = 30
        # Full score if delivery time is 50% of baseline (15 days), zero if at or above baseline
        time_factor = min(1.0, max(0, (baseline_days - self.completion_time) / (0.5 * baseline_days)))
        time_score = time_factor * 50
        
        # Total score (100 points max)
        total_score = price_score + time_score
        
        # Update the bid score
        self.bid_score = round(total_score, 2)
        return self.bid_score

class OTPVerification(db.Model):
    """OTPVerification model for email verification"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    otp = db.Column(db.String(6), nullable=False)
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<OTPVerification {self.user_id}>'
