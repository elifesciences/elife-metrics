# -*- coding: utf-8 -*-


from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('article_metrics', '0005_auto_20150921_1541'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='metric',
            unique_together=set([('article', 'date', 'period', 'source')]),
        ),
    ]
