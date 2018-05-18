# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('article_metrics', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='gametric',
            options={
                'db_table': 'metrics_metric',
                'ordering': ('date',)}
        ),
    ]
