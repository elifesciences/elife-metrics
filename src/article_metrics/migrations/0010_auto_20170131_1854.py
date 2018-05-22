# -*- coding: utf-8 -*-
# Generated by Django 1.11a1 on 2017-01-31 18:54


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('article_metrics', '0009_auto_20170130_1756'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='doi',
            field=models.CharField(help_text=b'article identifier', max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='article',
            name='pmcid',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='article',
            name='pmid',
            field=models.PositiveIntegerField(blank=True, null=True, unique=True),
        ),
    ]