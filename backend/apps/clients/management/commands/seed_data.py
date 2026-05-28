from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from rest_framework.authtoken.models import Token
from apps.clients.models import Client, ReportingPeriod, UserProfile


class Command(BaseCommand):
    help = 'Seed demo data: client, reporting period, and default users'

    def handle(self, *args, **kwargs):
        client, _ = Client.objects.get_or_create(
            name='Demo Corp',
            defaults={'country_default': 'IN'}
        )
        self.stdout.write(f'Client: {client.name}')

        period, _ = ReportingPeriod.objects.get_or_create(
            client=client,
            name='FY2024',
            defaults={
                'start_date': date(2024, 1, 1),
                'end_date': date(2024, 12, 31),
            }
        )
        self.stdout.write(f'Period: {period.name}')

        users = [
            ('uploader1', 'breathe123', 'UPLOADER'),
            ('analyst1', 'breathe123', 'ANALYST'),
            ('admin1', 'breathe123', 'ADMIN'),
        ]
        for username, password, role in users:
            user, created = User.objects.get_or_create(username=username)
            if created:
                user.set_password(password)
                user.save()
            UserProfile.objects.get_or_create(
                user=user,
                defaults={'client': client, 'role': role}
            )
            Token.objects.get_or_create(user=user)
            self.stdout.write(f'User: {username} ({role})')

        self.stdout.write(self.style.SUCCESS('Seed data created successfully.'))
