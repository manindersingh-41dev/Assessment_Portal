# Generated to align the question schema with the current models.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questions", "0002_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="question",
            old_name="modified_at",
            new_name="updated_at",
        ),
        migrations.RenameField(
            model_name="testcase",
            old_name="modified_at",
            new_name="updated_at",
        ),
        migrations.AddField(
            model_name="question",
            name="input_format",
            field=models.TextField(
                default="",
                help_text="Explanation of input format.",
                verbose_name="input format",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="question",
            name="output_format",
            field=models.TextField(
                default="",
                help_text="Explanation of output format.",
                verbose_name="output format",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="question",
            name="constraints",
            field=models.TextField(
                default="",
                help_text="Technical constraints on input data.",
                verbose_name="constraints",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="question",
            name="sample_input",
            field=models.TextField(
                default="",
                help_text="Sample input for display.",
                verbose_name="sample input",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="question",
            name="sample_output",
            field=models.TextField(
                default="",
                help_text="Sample output for display.",
                verbose_name="sample output",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="question",
            name="sample_explanation",
            field=models.TextField(
                blank=True,
                null=True,
                help_text="Explanation for the sample input/output.",
                verbose_name="sample explanation",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="topic",
            field=models.CharField(
                blank=True,
                null=True,
                max_length=100,
                help_text="Topic or tag for the question.",
                verbose_name="topic",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="memory_limit_mb",
            field=models.PositiveIntegerField(
                default=128,
                help_text="Memory limit in MB.",
                verbose_name="memory limit (mb)",
            ),
        ),
        migrations.AddIndex(
            model_name="question",
            index=models.Index(fields=["topic"], name="ques_topic_idx"),
        ),
    ]
