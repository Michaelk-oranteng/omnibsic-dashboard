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
        """Seed branch data including all branches and departments in alphabetical order"""
        
        # All departments and branches from the list - SORTED ALPHABETICALLY
        branches = sorted([
            # DEPARTMENTS
            'ASSET MONITORING AND ARCHIVES',
            'BRANCH SUPPORT',
            'CENTRALIZED ACCOUNT OPENING',
            'CLASSIC BANKING',
            'CLEARING',
            'CMU',
            'CORPORATE COMMS',
            'CORPORATE GROUP',
            'CPU',
            'CRB',
            'CREDIT',
            'CYBER SECURITY',
            'E-BUSINESS',
            'FACILITIES MANAGEMENT',
            'FINANCE',
            'FINOPS',
            'GENERAL SERVICES & PROCUREMENT',
            'HCM',
            'INFORMATION TECHNOLOGY',
            'IT',
            'LEGAL',
            'RECONCILIATION',
            'RECOVERY',
            'REMITTANCE',
            'RISK',
            'SERVICE QUALITY',
            'TRADE SERVICES',
            'TRANSPORT & LOGISTICS',
            'TREASURY',
            'TROPS',
            
            # BRANCHES
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
        ])

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
        """Seed exception categories - all unique categories sorted alphabetically"""
        
        # All unique exception categories from the provided list - SORTED ALPHABETICALLY
        exception_categories = sorted([
            'ACCESS & PRIVILEDGE MANAGEMENT',
            'APPLICATION & E-BANKING CONTROLS',
            'BRANCH AMBIENCE & BRANDING',
            'BRANCH SECURITY',
            'CALLOVER, VAULT & CASH',
            'COST SAVED/EXPENSE',
            'CYBERSECURITY & RISK CONTROL',
            'DELAY OR FAILURE TO PROCESS CUSTOMER REQUEST',
            'GL EXCEPTIONS',
            'INCOME LEAKAGE',
            'INFRASTRUCTURE, SERVERS & DATA CENTRE CONTROL',
            'INFORMATION SECURITY GOVERNANCE & COMPLIANCE',
            'IT OPERATIONS & SERVICE MANAGEMENT',
            'KYC',
            'KYC/ACCOUNT OPENING',
            'OTHERS',
            'OUTSTANDING ISSUES DATA & DATABASE MANAGEMENT CONTROL',
            'POLICY/REGULATORY BREACH',
            'REGISTERS, FORMS & FILES',
            'SECURITY SWEEP & CLEAN DESK',
            'SOC, THREAT INTELLIGENCE, INCIDENT & FORENSICS',
            'TOTAL ISSUES',
            'VAULT & CASH/CALLOVER',
            'VISA CARD & CHEQUE BOOKS PHYSICAL SECURITY'
        ])

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