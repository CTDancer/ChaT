# Generated by Django 4.1.3 on 2023-05-20 09:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hole', '0004_remove_hole_time_updated_remove_hole_view_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hole',
            name='division',
            field=models.IntegerField(default=0, help_text='分区'),
        ),
    ]
