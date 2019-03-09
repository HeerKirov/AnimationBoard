# Generated by Django 2.1.7 on 2019-03-08 02:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20190308_0226'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='animation',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='api.Animation'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='diary',
            name='animation',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='api.Animation'),
            preserve_default=False,
        ),
    ]
