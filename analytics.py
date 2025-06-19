"""
Analytics module for TenderVista.
Provides data processing and visualization for tender statistics.
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
from io import BytesIO
import base64
from sqlalchemy import func, case, extract, and_
from models import Tender, TenderApplication, User, Role, db
from app import app

# Configure matplotlib to use Agg backend for server-side rendering
matplotlib.use('Agg')

class TenderAnalytics:
    """Class to handle tender analytics data processing and visualization"""
    
    @staticmethod
    def get_tender_activity(days=30):
        """Get tender activity statistics for the specified number of days"""
        # Calculate start date for analysis
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get tenders created in the time period
        tenders_query = db.session.query(
            func.date(Tender.created_at).label('date'),
            func.count().label('count')
        ).filter(
            Tender.created_at >= start_date
        ).group_by(
            func.date(Tender.created_at)
        ).order_by(
            func.date(Tender.created_at)
        ).all()
        
        # Get applications created in the time period
        applications_query = db.session.query(
            func.date(TenderApplication.created_at).label('date'),
            func.count().label('count')
        ).filter(
            TenderApplication.created_at >= start_date
        ).group_by(
            func.date(TenderApplication.created_at)
        ).order_by(
            func.date(TenderApplication.created_at)
        ).all()
        
        # Convert to dataframes and merge
        date_range = pd.date_range(start=start_date.date(), end=end_date.date())
        
        tenders_df = pd.DataFrame(tenders_query, columns=['date', 'tenders'])
        tenders_df['date'] = pd.to_datetime(tenders_df['date'])
        tenders_df.set_index('date', inplace=True)
        
        applications_df = pd.DataFrame(applications_query, columns=['date', 'applications'])
        applications_df['date'] = pd.to_datetime(applications_df['date'])
        applications_df.set_index('date', inplace=True)
        
        # Ensure all dates in the range are represented
        activity_df = pd.DataFrame(index=date_range)
        activity_df.index.name = 'date'
        
        # Merge the activity data
        activity_df = activity_df.join(tenders_df, how='left').join(applications_df, how='left')
        activity_df.fillna(0, inplace=True)
        
        # Convert to integers for display
        activity_df['tenders'] = activity_df['tenders'].astype(int)
        activity_df['applications'] = activity_df['applications'].astype(int)
        
        return activity_df
    
    @staticmethod
    def get_tender_categories_distribution():
        """Get the distribution of tenders by category"""
        categories_query = db.session.query(
            Tender.category,
            func.count().label('count')
        ).group_by(
            Tender.category
        ).order_by(
            func.count().desc()
        ).all()
        
        categories_df = pd.DataFrame(categories_query, columns=['category', 'count'])
        
        # Format category names for better display
        categories_df['category_name'] = categories_df['category'].apply(
            lambda x: x.replace('_', ' ').title()
        )
        
        return categories_df
    
    @staticmethod
    def get_tender_budget_distribution():
        """Get the distribution of tenders by budget range"""
        budget_ranges = [
            (0, 5000, 'Under ₹5K'),
            (5000, 20000, '₹5K-₹20K'),
            (20000, 50000, '₹20K-₹50K'),
            (50000, 100000, '₹50K-₹100K'),
            (100000, 500000, '₹100K-₹500K'),
            (500000, float('inf'), 'Above ₹500K')
        ]
        
        # Create SQL case expression for budget ranges
        budget_case = []
        for min_val, max_val, label in budget_ranges:
            if max_val == float('inf'):
                budget_case.append(
                    (Tender.budget >= min_val, label)
                )
            else:
                budget_case.append(
                    (and_(Tender.budget >= min_val, Tender.budget < max_val), label)
                )
        
        budget_query = db.session.query(
            case(*budget_case, else_='Other').label('range'),
            func.count().label('count')
        ).group_by(
            'range'
        ).order_by(
            'range'
        ).all()
        
        # Convert to dataframe and ensure all ranges are represented
        budget_df = pd.DataFrame(budget_query, columns=['range', 'count'])
        
        # Ensure all ranges are included even if count is 0
        range_labels = [label for _, _, label in budget_ranges]
        missing_ranges = set(range_labels) - set(budget_df['range'])
        
        for missing in missing_ranges:
            budget_df = pd.concat([
                budget_df, 
                pd.DataFrame([{'range': missing, 'count': 0}])
            ])
        
        # Sort by range using the order defined in budget_ranges
        range_order = {label: i for i, (_, _, label) in enumerate(budget_ranges)}
        budget_df['sort_order'] = budget_df['range'].map(range_order)
        budget_df.sort_values('sort_order', inplace=True)
        budget_df.drop('sort_order', axis=1, inplace=True)
        
        return budget_df
    
    @staticmethod
    def get_application_status_distribution():
        """Get the distribution of tender applications by status"""
        status_query = db.session.query(
            TenderApplication.status,
            func.count().label('count')
        ).group_by(
            TenderApplication.status
        ).order_by(
            TenderApplication.status
        ).all()
        
        status_df = pd.DataFrame(status_query, columns=['status', 'count'])
        
        # Format status names for better display
        status_df['status_name'] = status_df['status'].apply(lambda x: x.title())
        
        return status_df
    
    @staticmethod
    def get_tender_completion_rate():
        """Get the percentage of tenders that have selected a winner"""
        total_closed_tenders = db.session.query(func.count()).filter(
            Tender.submission_deadline < datetime.now()
        ).scalar() or 0
        
        completed_tenders = db.session.query(func.count()).filter(
            Tender.submission_deadline < datetime.now(),
            Tender.winner_selected == True
        ).scalar() or 0
        
        if total_closed_tenders > 0:
            completion_rate = (completed_tenders / total_closed_tenders) * 100
        else:
            completion_rate = 0
        
        return {
            'total_closed': total_closed_tenders,
            'completed': completed_tenders,
            'rate': round(completion_rate, 1)
        }
    
    @staticmethod
    def get_monthly_tender_activity(months=12):
        """Get monthly tender and application activity for the past X months"""
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)  # Approximate
        
        # Monthly tenders
        monthly_tenders = db.session.query(
            extract('year', Tender.created_at).label('year'),
            extract('month', Tender.created_at).label('month'),
            func.count().label('count')
        ).filter(
            Tender.created_at >= start_date
        ).group_by(
            extract('year', Tender.created_at),
            extract('month', Tender.created_at)
        ).order_by(
            extract('year', Tender.created_at),
            extract('month', Tender.created_at)
        ).all()
        
        # Monthly applications
        monthly_applications = db.session.query(
            extract('year', TenderApplication.created_at).label('year'),
            extract('month', TenderApplication.created_at).label('month'),
            func.count().label('count')
        ).filter(
            TenderApplication.created_at >= start_date
        ).group_by(
            extract('year', TenderApplication.created_at),
            extract('month', TenderApplication.created_at)
        ).order_by(
            extract('year', TenderApplication.created_at),
            extract('month', TenderApplication.created_at)
        ).all()
        
        # Convert to dataframes
        # Create a date range for all months in the period
        date_range = pd.date_range(
            start=datetime(start_date.year, start_date.month, 1),
            end=datetime(end_date.year, end_date.month, 1),
            freq='MS'  # Month start frequency
        )
        
        # Prepare dataframe with all months
        monthly_df = pd.DataFrame(index=date_range)
        monthly_df.index.name = 'date'
        monthly_df['month_label'] = monthly_df.index.strftime('%b %Y')
        
        # Process tenders data
        tenders_data = []
        for year, month, count in monthly_tenders:
            date = datetime(int(year), int(month), 1)
            tenders_data.append({'date': date, 'tenders': count})
        
        tenders_df = pd.DataFrame(tenders_data)
        if not tenders_df.empty:
            tenders_df.set_index('date', inplace=True)
            monthly_df = monthly_df.join(tenders_df, how='left')
        else:
            monthly_df['tenders'] = 0
        
        # Process applications data
        applications_data = []
        for year, month, count in monthly_applications:
            date = datetime(int(year), int(month), 1)
            applications_data.append({'date': date, 'applications': count})
        
        applications_df = pd.DataFrame(applications_data)
        if not applications_df.empty:
            applications_df.set_index('date', inplace=True)
            monthly_df = monthly_df.join(applications_df, how='left')
        else:
            monthly_df['applications'] = 0
        
        # Fill missing values and convert to integers
        monthly_df.fillna(0, inplace=True)
        monthly_df['tenders'] = monthly_df['tenders'].astype(int)
        monthly_df['applications'] = monthly_df['applications'].astype(int)
        
        return monthly_df
    
    @staticmethod
    def get_user_growth(months=12):
        """Get user growth statistics for the past X months"""
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)  # Approximate
        
        # Monthly new users
        monthly_users = db.session.query(
            extract('year', User.created_at).label('year'),
            extract('month', User.created_at).label('month'),
            func.count().label('count')
        ).filter(
            User.created_at >= start_date
        ).group_by(
            extract('year', User.created_at),
            extract('month', User.created_at)
        ).order_by(
            extract('year', User.created_at),
            extract('month', User.created_at)
        ).all()
        
        # Convert to dataframe
        date_range = pd.date_range(
            start=datetime(start_date.year, start_date.month, 1),
            end=datetime(end_date.year, end_date.month, 1),
            freq='MS'  # Month start frequency
        )
        
        # Prepare dataframe with all months
        monthly_df = pd.DataFrame(index=date_range)
        monthly_df.index.name = 'date'
        monthly_df['month_label'] = monthly_df.index.strftime('%b %Y')
        
        # Process users data
        users_data = []
        for year, month, count in monthly_users:
            date = datetime(int(year), int(month), 1)
            users_data.append({'date': date, 'new_users': count})
        
        users_df = pd.DataFrame(users_data)
        if not users_df.empty:
            users_df.set_index('date', inplace=True)
            monthly_df = monthly_df.join(users_df, how='left')
        else:
            monthly_df['new_users'] = 0
        
        # Fill missing values and convert to integers
        monthly_df.fillna(0, inplace=True)
        monthly_df['new_users'] = monthly_df['new_users'].astype(int)
        
        # Calculate cumulative users
        monthly_df['cumulative_users'] = monthly_df['new_users'].cumsum()
        
        # Get total users before the start date
        users_before_start = db.session.query(func.count()).filter(
            User.created_at < start_date
        ).scalar() or 0
        
        # Add to cumulative count
        monthly_df['cumulative_users'] += users_before_start
        
        return monthly_df
    
    @staticmethod
    def get_industry_sector_distribution():
        """Get distribution of companies by industry sector"""
        sector_query = db.session.query(
            User.industry_sector,
            func.count().label('count')
        ).filter(
            User.industry_sector.isnot(None)
        ).group_by(
            User.industry_sector
        ).order_by(
            func.count().desc()
        ).all()
        
        sector_df = pd.DataFrame(sector_query, columns=['sector', 'count'])
        
        # Format sector names for better display
        sector_df['sector_name'] = sector_df['sector'].apply(
            lambda x: x.replace('_', ' ').title() if x else 'Not Specified'
        )
        
        return sector_df
    
    @staticmethod
    def get_company_size_distribution():
        """Get distribution of companies by size"""
        size_query = db.session.query(
            User.company_size,
            func.count().label('count')
        ).filter(
            User.company_size.isnot(None)
        ).group_by(
            User.company_size
        ).all()
        
        size_df = pd.DataFrame(size_query, columns=['size', 'count'])
        
        # Define the order of company sizes
        size_order = {'micro': 0, 'small': 1, 'medium': 2, 'large': 3, None: 4}
        
        # Format size names for better display
        size_display = {
            'micro': 'Micro (1-9)',
            'small': 'Small (10-49)',
            'medium': 'Medium (50-249)',
            'large': 'Large (250+)',
            None: 'Not Specified'
        }
        
        size_df['size_name'] = size_df['size'].map(size_display)
        size_df['sort_order'] = size_df['size'].map(size_order)
        size_df.sort_values('sort_order', inplace=True)
        size_df.drop('sort_order', axis=1, inplace=True)
        
        return size_df
    
    # Chart generation methods
    @staticmethod
    def generate_chart_tender_activity(days=30):
        """Generate chart for tender activity"""
        activity_df = TenderAnalytics.get_tender_activity(days)
        
        plt.figure(figsize=(10, 5))
        plt.plot(activity_df.index, activity_df['tenders'], 'b-', label='Tenders')
        plt.plot(activity_df.index, activity_df['applications'], 'g-', label='Applications')
        plt.fill_between(activity_df.index, activity_df['tenders'], alpha=0.2, color='blue')
        plt.fill_between(activity_df.index, activity_df['applications'], alpha=0.2, color='green')
        
        plt.title(f'Tender Activity (Last {days} days)')
        plt.xlabel('Date')
        plt.ylabel('Count')
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_categories_distribution():
        """Generate chart for tender categories distribution"""
        categories_df = TenderAnalytics.get_tender_categories_distribution()
        
        if categories_df.empty:
            return None
        
        plt.figure(figsize=(10, 6))
        colors = plt.cm.viridis(np.linspace(0, 1, len(categories_df)))
        
        bars = plt.barh(categories_df['category_name'], categories_df['count'], color=colors)
        
        # Add count labels to the bars
        for bar in bars:
            width = bar.get_width()
            plt.text(width + 0.3, bar.get_y() + bar.get_height()/2, 
                    f'{width:.0f}', ha='left', va='center')
        
        plt.title('Tenders by Electronics Category')
        plt.xlabel('Number of Tenders')
        plt.grid(True, alpha=0.3, axis='x')
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_budget_distribution():
        """Generate chart for tender budget distribution"""
        budget_df = TenderAnalytics.get_tender_budget_distribution()
        
        plt.figure(figsize=(10, 6))
        explode = [0.05] * len(budget_df)  # Slightly explode all slices
        colors = plt.cm.coolwarm(np.linspace(0, 1, len(budget_df)))
        
        # Only include non-zero values in the pie chart
        non_zero_df = budget_df[budget_df['count'] > 0]
        
        if non_zero_df.empty:
            return None
        
        # Adjust explode array to match non-zero data
        explode = explode[:len(non_zero_df)]
        
        plt.pie(non_zero_df['count'], labels=non_zero_df['range'], 
                autopct='%1.1f%%', explode=explode, colors=colors,
                shadow=True, startangle=90)
        plt.axis('equal')
        plt.title('Tender Distribution by Budget Range')
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_application_status():
        """Generate chart for application status distribution"""
        status_df = TenderAnalytics.get_application_status_distribution()
        
        if status_df.empty:
            return None
        
        plt.figure(figsize=(8, 6))
        colors = {
            'pending': '#FFA726',  # Orange
            'approved': '#66BB6A',  # Green
            'rejected': '#EF5350',  # Red
            'winner': '#42A5F5'     # Blue
        }
        
        # Map colors to status
        status_colors = [colors.get(status, '#999999') for status in status_df['status']]
        
        bars = plt.bar(status_df['status_name'], status_df['count'], color=status_colors)
        
        # Add count labels to the bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}', ha='center', va='bottom')
        
        plt.title('Tender Applications by Status')
        plt.xlabel('Status')
        plt.ylabel('Number of Applications')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_monthly_activity(months=12):
        """Generate chart for monthly tender activity"""
        monthly_df = TenderAnalytics.get_monthly_tender_activity(months)
        
        fig, ax = plt.subplots(figsize=(12, 6))
        
        # Plot tenders as bars
        bars1 = ax.bar(monthly_df.index, monthly_df['tenders'], 
                     width=20, label='Tenders', color='#4285F4', alpha=0.7)
        
        # Plot applications as bars with offset
        bars2 = ax.bar(monthly_df.index, monthly_df['applications'], 
                     width=20, label='Applications', color='#34A853', alpha=0.7,
                     bottom=monthly_df['tenders'])
        
        # Format x-axis to show month and year
        ax.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45)
        
        # Add count labels to the bars
        for i, (tender_count, app_count) in enumerate(zip(monthly_df['tenders'], monthly_df['applications'])):
            total = tender_count + app_count
            if tender_count > 0:
                plt.text(bars1[i].get_x() + bars1[i].get_width()/2., tender_count/2,
                       f'{tender_count}', ha='center', va='center', color='white', fontweight='bold')
            if app_count > 0:
                plt.text(bars2[i].get_x() + bars2[i].get_width()/2., tender_count + app_count/2,
                       f'{app_count}', ha='center', va='center', color='white', fontweight='bold')
        
        plt.title(f'Monthly Tender Activity (Last {months} months)')
        plt.xlabel('Month')
        plt.ylabel('Count')
        plt.grid(True, alpha=0.3, axis='y')
        plt.legend()
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_user_growth(months=12):
        """Generate chart for user growth"""
        user_df = TenderAnalytics.get_user_growth(months)
        
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        # Plot monthly new users (bars)
        ax1.bar(user_df.index, user_df['new_users'], width=20, 
               color='#FBBC05', alpha=0.6, label='New Users')
        ax1.set_xlabel('Month')
        ax1.set_ylabel('New Users', color='#FBBC05')
        
        # Create second y-axis for cumulative users (line)
        ax2 = ax1.twinx()
        ax2.plot(user_df.index, user_df['cumulative_users'], 'b-', 
                linewidth=3, color='#EA4335', label='Total Users')
        ax2.set_ylabel('Total Users', color='#EA4335')
        
        # Format x-axis to show month and year
        ax1.xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%b %Y'))
        plt.xticks(rotation=45)
        
        # Combine legends from both axes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.title(f'User Growth (Last {months} months)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_industry_sectors():
        """Generate chart for industry sector distribution"""
        sector_df = TenderAnalytics.get_industry_sector_distribution()
        
        if sector_df.empty:
            return None
        
        plt.figure(figsize=(10, 6))
        colors = plt.cm.tab20(np.linspace(0, 1, len(sector_df)))
        
        # If too many sectors, limit to top N and group the rest
        max_sectors = 8
        if len(sector_df) > max_sectors:
            top_sectors = sector_df.iloc[:max_sectors-1].copy()
            other_count = sector_df.iloc[max_sectors-1:]['count'].sum()
            other_row = pd.DataFrame([{'sector': 'other', 'sector_name': 'Other', 'count': other_count}])
            sector_df = pd.concat([top_sectors, other_row])
        
        # Create pie chart
        explode = [0.05] * len(sector_df)  # Slightly explode all slices
        plt.pie(sector_df['count'], labels=sector_df['sector_name'], 
                autopct='%1.1f%%', explode=explode, colors=colors,
                shadow=True, startangle=90)
        plt.axis('equal')
        plt.title('Company Distribution by Industry Sector')
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def generate_chart_company_sizes():
        """Generate chart for company size distribution"""
        size_df = TenderAnalytics.get_company_size_distribution()
        
        if size_df.empty:
            return None
        
        plt.figure(figsize=(10, 6))
        
        # Define colors for each company size
        colors = {
            'Micro (1-9)': '#8BC34A',      # Light Green
            'Small (10-49)': '#4CAF50',    # Green
            'Medium (50-249)': '#009688',  # Teal
            'Large (250+)': '#00796B',     # Dark Teal
            'Not Specified': '#BDBDBD'     # Grey
        }
        
        # Map colors to sizes
        size_colors = [colors.get(name, '#999999') for name in size_df['size_name']]
        
        bars = plt.bar(size_df['size_name'], size_df['count'], color=size_colors)
        
        # Add count labels to the bars
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{height:.0f}', ha='center', va='bottom')
        
        plt.title('Company Distribution by Size')
        plt.xlabel('Company Size')
        plt.ylabel('Number of Companies')
        plt.grid(True, alpha=0.3, axis='y')
        plt.tight_layout()
        
        # Save chart to base64
        img = BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        
        plt.close()
        return base64.b64encode(img.getvalue()).decode('utf-8')
    
    @staticmethod
    def get_summary_stats():
        """Get summary statistics for the dashboard"""
        # Total users
        total_users = db.session.query(func.count(User.id)).scalar() or 0
        verified_users = db.session.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
        
        # Total tenders
        total_tenders = db.session.query(func.count(Tender.id)).scalar() or 0
        active_tenders = db.session.query(func.count(Tender.id)).filter(
            Tender.submission_deadline >= datetime.now()
        ).scalar() or 0
        
        # Total applications
        total_applications = db.session.query(func.count(TenderApplication.id)).scalar() or 0
        pending_applications = db.session.query(func.count(TenderApplication.id)).filter(
            TenderApplication.status == 'pending'
        ).scalar() or 0
        
        # Average applications per tender
        avg_applications = db.session.query(
            func.avg(
                db.session.query(func.count(TenderApplication.id))
                .filter(TenderApplication.tender_id == Tender.id)
                .scalar_subquery()
            )
        ).scalar() or 0
        
        # Most active categories
        top_categories_query = db.session.query(
            Tender.category, 
            func.count(Tender.id).label('tender_count'),
            func.count(TenderApplication.id).label('application_count')
        ).outerjoin(
            TenderApplication, TenderApplication.tender_id == Tender.id
        ).group_by(
            Tender.category
        ).order_by(
            func.count(TenderApplication.id).desc()
        ).limit(3).all()
        
        top_categories = [{
            'category': cat.replace('_', ' ').title(),
            'tenders': t_count,
            'applications': a_count
        } for cat, t_count, a_count in top_categories_query]
        
        return {
            'total_users': total_users,
            'verified_users': verified_users,
            'total_tenders': total_tenders,
            'active_tenders': active_tenders,
            'total_applications': total_applications,
            'pending_applications': pending_applications,
            'avg_applications': round(avg_applications, 1),
            'top_categories': top_categories
        }
    
    @staticmethod
    def export_tender_data_csv():
        """Export tender data to CSV format"""
        tenders = Tender.query.all()
        
        data = []
        for tender in tenders:
            # Count applications by status
            app_counts = db.session.query(
                TenderApplication.status,
                func.count().label('count')
            ).filter(
                TenderApplication.tender_id == tender.id
            ).group_by(
                TenderApplication.status
            ).all()
            
            status_counts = {status: count for status, count in app_counts}
            
            data.append({
                'Tender ID': tender.id,
                'Title': tender.title,
                'Category': tender.category.replace('_', ' ').title(),
                'Budget': f"₹{tender.budget:,.2f}",
                'submission_deadline': tender.submission_deadline.strftime('%Y-%m-%d %H:%M'),
                'is_open': 'Yes' if tender.is_open else 'No',
                'winner_selected': 'Yes' if tender.winner_selected else 'No',
                'created_at': tender.created_at.strftime('%Y-%m-%d %H:%M'),
                'total_applications': tender.applications.count(),
                'pending_applications': status_counts.get('pending', 0),
                'approved_applications': status_counts.get('approved', 0),
                'rejected_applications': status_counts.get('rejected', 0),
                'winner_applications': status_counts.get('winner', 0)
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return None
        
        # Generate CSV in memory
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Export as base64 string
        csv_b64 = base64.b64encode(csv_buffer.getvalue()).decode('utf-8')
        
        return {
            'csv_data': csv_b64,
            'filename': f'tender_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    
    @staticmethod
    def export_applications_data_csv():
        """Export application data to CSV format"""
        applications = db.session.query(
            TenderApplication.id,
            TenderApplication.proposal,
            TenderApplication.price_quote,
            TenderApplication.completion_time,
            TenderApplication.status,
            TenderApplication.bid_score,
            TenderApplication.ranking,
            TenderApplication.is_winner,
            TenderApplication.created_at,
            Tender.id.label('tender_id'),
            Tender.title.label('tender_title'),
            Tender.category.label('tender_category'),
            Tender.budget.label('tender_budget'),
            User.id.label('user_id'),
            User.name.label('user_name'),
            User.company_name.label('company_name')
        ).join(
            Tender, Tender.id == TenderApplication.tender_id
        ).join(
            User, User.id == TenderApplication.user_id
        ).all()
        
        # Convert to list of dicts
        data = []
        for app in applications:
            data.append({
                'id': app.id,
                'tender_id': app.tender_id,
                'tender_title': app.tender_title,
                'tender_category': app.tender_category,
                'tender_budget': app.tender_budget,
                'user_id': app.user_id,
                'user_name': app.user_name,
                'company_name': app.company_name,
                'price_quote': app.price_quote,
                'completion_time': app.completion_time,
                'bid_score': app.bid_score,
                'status': app.status,
                'ranking': app.ranking,
                'is_winner': 'Yes' if app.is_winner else 'No',
                'created_at': app.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        df = pd.DataFrame(data)
        
        if df.empty:
            return None
        
        # Generate CSV in memory
        csv_buffer = BytesIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        # Export as base64 string
        csv_b64 = base64.b64encode(csv_buffer.getvalue()).decode('utf-8')
        
        return {
            'csv_data': csv_b64,
            'filename': f'applications_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }