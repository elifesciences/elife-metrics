# Generated by Django 3.2.18 on 2023-03-20 00:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('article_metrics', '0001_initial_squashed_0016_auto_20180205_0102'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='pmcid',
            field=models.CharField(blank=True, max_length=11, null=True, unique=True),
        ),
    ]
