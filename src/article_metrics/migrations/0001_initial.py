# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('doi', models.CharField(help_text=b'article identifier', max_length=255)),
            ],
            options={
                'db_table': 'metrics_article',
            },
        ),
        migrations.CreateModel(
            name='GAMetric',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.CharField(help_text=b"the date this metric is for in YYYY-MM-DD, YYYY-MM and YYYY formats or None for 'all time'", max_length=10, null=True, blank=True)),
                ('type', models.CharField(max_length=10, choices=[(b'day', b'Daily'), (b'month', b'Monthly'), (b'year', b'Yearly'), (b'ever', b'All time')])),
                ('full', models.PositiveSmallIntegerField(help_text=b'article page views')),
                ('abstract', models.PositiveSmallIntegerField(help_text=b'article abstract page views')),
                ('digest', models.PositiveSmallIntegerField(help_text=b'article digest page views')),
                ('pdf', models.PositiveSmallIntegerField(help_text=b'pdf downloads')),
                ('article', models.ForeignKey(to='article_metrics.Article')),
            ],
            options={
                'db_table': 'metrics_metric',
            },

        ),
        migrations.AlterUniqueTogether(
            name='gametric',
            unique_together=set([('article', 'date', 'type')]),
        ),
    ]
