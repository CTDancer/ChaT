# Generated by Django 4.1.3 on 2023-05-19 14:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hole', '0002_alter_user_avatar'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='bio',
            field=models.CharField(blank=True, default='这个人很懒，什么都没留下', max_length=500),
        ),
    ]