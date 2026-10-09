from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0003_alter_article_id_alter_author_id_alter_tag_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='abstract',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='article',
            name='translated_abstract',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='article',
            name='s3_key',
            field=models.CharField(blank=True, max_length=512),
        ),
    ]
