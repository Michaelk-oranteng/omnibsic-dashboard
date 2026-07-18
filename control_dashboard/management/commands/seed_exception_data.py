# control_dashboard/management/commands/seed_exception_data.py

from django.core.management.base import BaseCommand
from control_dashboard.models import Branch, ExceptionCategory
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seed exception categories and branches'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting data seeding...'))
        
        # Seed Branches (including departments)
        self.seed_branches()
        
        # Seed Exception Categories
        self.seed_exception_categories()
        
        self.stdout.write(self.style.SUCCESS('Data seeding completed successfully!'))

    def seed_branches(self):
        """Seed branch data including all branches and departments"""
        
        # All departments and branches from the list
        branches = [
            # DEPARTMENTS (First 30)
            'GENERAL SERVICES & PROCUREMENT',
            'BRANCH SUPPORT',
            'CLEARING',
            'FINOPS',
            'CORPORATE COMMS',
            'CREDIT',
            'RISK',
            'E-BUSINESS',
            'FACILITIES MANAGEMENT',
            'FINANCE',
            'CPU',
            'HCM',
            'LEGAL',
            'RECONCILIATION',
            'SERVICE QUALITY',
            'TRADE SERVICES',
            'CMU',
            'TREASURY',
            'REMITTANCE',
            'IT',
            'TRANSPORT & LOGISTICS',
            'RECOVERY',
            'CORPORATE GROUP',
            'CRB',
            'CENTRALIZED ACCOUNT OPENING',
            'CLASSIC BANKING',
            'ASSET MONITORING AND ARCHIVES',
            'TROPS',
            'CYBER SECURITY',
            'INFORMATION TECHNOLOGY',
            
            # BRANCHES (Remaining 41 branches)
            'ABELEMKPE',
            'ABOSSEY OKAI',
            'ACCRA CENTRAL',
            'ACHIMOTA',
            'ADABRAKA',
            'ADUM ADDO KUFOUR',
            'ADUM PREMPEH',
            'AHODWO',
            'AIRPORT',
            'AMAKOM',
            'ASHALEY BOTWE',
            'ATOMIC',
            'DANSOMAN',
            'DOME',
            'EAST LEGON',
            'KASOA',
            'KEJETIA',
            'KNUST',
            'KOFORIDUA',
            'KOKOMLEMLE',
            'KRONUM',
            'LABONE',
            'MADINA ESTATE',
            'MANHYIA',
            'NIMA',
            'NORTH INDUSTRIAL AREA',
            'ODORKOR',
            'OSU',
            'SPINTEX BASKET',
            'SPINTEX MANET',
            'SUNYANI',
            'TAKORADI HARBOUR',
            'TAKORADI MARKET CIRCLE',
            'TAMALE',
            'TARKWA',
            'TECHIMAN',
            'TEMA COMMUNITY 1',
            'TEMA COMMUNITY 11',
            'TEMA EAST',
            'TEMA HARBOUR',
            'WEIJA'
        ]

        # Add branches
        branch_count = 0
        for branch in branches:
            try:
                Branch.objects.get_or_create(name=branch)
                branch_count += 1
                self.stdout.write(f'Created/Updated branch: {branch}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating branch {branch}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created/Updated {branch_count} branches/departments'))

    def seed_exception_categories(self):
        """Seed exception categories - all unique categories from the list"""
        
        # All unique exception categories from the provided list
        exception_categories = [
            'BRANCH AMBIENCE & BRANDING',
            'BRANCH SECURITY',
            'CALLOVER, VAULT & CASH',
            'DELAY OR FAILURE TO PROCESS CUSTOMER REQUEST',
            'GL EXCEPTIONS',
            'INCOME LEAKAGE',
            'KYC/ACCOUNT OPENING',
            'OTHERS',
            'REGISTERS, FORMS & FILES',
            'SECURITY SWEEP & CLEAN DESK',
            'VISA CARD & CHEQUE BOOKS PHYSICAL SECURITY',
            'VAULT & CASH/CALLOVER',
            'POLICY/REGULATORY BREACH',
            'COST SAVED/EXPENSE',
            'KYC',
            'TOTAL ISSUES',
            'OUTSTANDING ISSUES DATA & DATABASE MANAGEMENT CONTROL',
            'INFORMATION SECURITY GOVERNANCE & COMPLIANCE',
            'IT OPERATIONS & SERVICE MANAGEMENT',
            'ACCESS & PRIVILEDGE MANAGEMENT',
            'SOC, THREAT INTELLIGENCE, INCIDENT & FORENSICS',
            'APPLICATION & E-BANKING CONTROLS',
            'INFRASTRUCTURE, SERVERS & DATA CENTRE CONTROL',
            'CYBERSECURITY & RISK CONTROL'
        ]

        category_count = 0
        for category_name in exception_categories:
            try:
                ExceptionCategory.objects.get_or_create(
                    name=category_name,
                    defaults={'is_active': True}
                )
                category_count += 1
                self.stdout.write(f'Created category: {category_name}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating category {category_name}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {category_count} exception categories'))