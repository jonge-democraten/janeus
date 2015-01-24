# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('janeus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='JaneusRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(max_length=250)),
                ('groups', models.ManyToManyField(to='auth.Group', blank=True)),
                ('permissions', models.ManyToManyField(to='auth.Permission', blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
