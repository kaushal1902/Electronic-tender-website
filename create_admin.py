"""
Script to create a default admin user for TenderVista.
Run this script once to set up the initial admin account.
"""

import os
from werkzeug.security import generate_password_hash
from app import app, db
from models import User, Role

def create_admin_account(email, password, name):
    """Create an admin account with the specified email and password"""
    with app.app_context():
        # Check if the admin role exists
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin', description='Administrator role with full access')
            db.session.add(admin_role)
            db.session.flush()
        
        # Check if the admin user already exists
        admin_user = User.query.filter_by(email=email).first()
        if admin_user:
            print(f"Admin user with email {email} already exists.")
            return False
        
        # Create the admin user
        admin_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            name=name,
            is_verified=True,
            company_name="Electronic Tender Admin",
            company_registration_number="ADMIN-0001",
            company_size="large",
            industry_sector="other_electronics",
            company_address="Admin Office"
        )
        
        db.session.add(admin_user)
        db.session.flush()
        
        # Assign the admin role to the user
        admin_user.roles.append(admin_role)
        
        db.session.commit()
        print(f"Admin user created successfully with email: {email}")
        return True

def main():
    """Main function to create the admin account"""
    # Get admin credentials from environment variables or use defaults
    admin_email = os.environ.get("ADMIN_EMAIL", "kaushaldangodra781@gmail.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@123")
    admin_name = os.environ.get("ADMIN_NAME", "System Administrator")
    
    # Create the admin account
    success = create_admin_account(admin_email, admin_password, admin_name)
    
    if success:
        print(f"""
==================== Admin Account Created ====================
Email: {admin_email}
Password: {admin_password}
Name: {admin_name}
================================================================

Please change the default password after the first login.
        """)

if __name__ == "__main__":
    main()