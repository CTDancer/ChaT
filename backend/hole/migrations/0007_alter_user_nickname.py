# Generated by Django 4.1.3 on 2023-05-23 11:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hole', '0006_rename_history_floor_likes_remove_floor_like_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='nickname',
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
