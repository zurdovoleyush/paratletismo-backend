from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournaments', '0017_tournament_payment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='tournament',
            name='is_active',
            field=models.BooleanField(default=True, help_text='Torneo visible en el perfil del organizador y habilitado para el publico'),
        ),
    ]
