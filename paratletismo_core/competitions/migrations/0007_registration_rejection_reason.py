from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competitions', '0006_alter_result_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='rejection_reason',
            field=models.TextField(blank=True, help_text='Motivo del rechazo informado al atleta/institucion'),
        ),
    ]
