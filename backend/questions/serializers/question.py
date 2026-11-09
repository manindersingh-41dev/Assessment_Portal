"""Serializers for faculty question-bank and test-case APIs."""

from django.db import transaction
from rest_framework import serializers

from questions.models import Question, TestCase
from questions.services import has_test_case_results, question_has_submissions


class TestCaseSerializer(serializers.ModelSerializer):
    """Read representation of a test case."""

    has_results = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            "id",
            "question",
            "input",
            "expected_output",
            "is_sample",
            "marks",
            "order",
            "created_at",
            "updated_at",
            "has_results",
        ]
        read_only_fields = fields

    def get_has_results(self, obj):
        return has_test_case_results(obj)


class TestCaseWriteSerializer(serializers.ModelSerializer):
    """Nested test-case input used when creating or updating a question."""

    id = serializers.UUIDField(required=False)

    class Meta:
        model = TestCase
        fields = ["id", "input", "expected_output", "is_sample", "marks", "order"]
        extra_kwargs = {"order": {"required": False}}

    def validate_input(self, value):
        if not value.strip():
            raise serializers.ValidationError("Input cannot be empty.")
        return value

    def validate_expected_output(self, value):
        if not value.strip():
            raise serializers.ValidationError("Expected output cannot be empty.")
        return value

    def validate_marks(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Marks must be between 1 and 100.")
        return value


class TestCaseCreateSerializer(serializers.ModelSerializer):
    """Create a test case for a question owned by the authenticated faculty."""

    question_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = TestCase
        fields = [
            "id",
            "question_id",
            "input",
            "expected_output",
            "is_sample",
            "marks",
            "order",
        ]
        read_only_fields = ["id"]
        extra_kwargs = {"order": {"required": False}}

    def validate_input(self, value):
        if not value.strip():
            raise serializers.ValidationError("Input cannot be empty.")
        return value

    def validate_expected_output(self, value):
        if not value.strip():
            raise serializers.ValidationError("Expected output cannot be empty.")
        return value

    def validate_marks(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Marks must be between 1 and 100.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        try:
            question = Question.objects.get(
                pk=attrs["question_id"], created_by=request.user
            )
        except Question.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"question_id": "Question not found or you do not own it."}
            ) from exc

        current_marks = sum(question.test_cases.values_list("marks", flat=True))
        if current_marks + attrs["marks"] > question.total_marks:
            raise serializers.ValidationError(
                {"marks": "Adding these marks would exceed the question total."}
            )
        if not attrs.get("is_sample", False) and not question.test_cases.filter(is_sample=True).exists():
            raise serializers.ValidationError(
                {"is_sample": "A question must have at least one sample test case."}
            )
        attrs.setdefault("order", question.test_cases.count() + 1)
        attrs["question"] = question
        return attrs

    def create(self, validated_data):
        validated_data.pop("question_id", None)
        return TestCase.objects.create(**validated_data)


class TestCaseUpdateSerializer(serializers.ModelSerializer):
    """Update a test case without allowing its parent question to be changed."""

    class Meta:
        model = TestCase
        fields = ["input", "expected_output", "is_sample", "marks", "order"]
        extra_kwargs = {"order": {"required": False}}

    def validate_input(self, value):
        if not value.strip():
            raise serializers.ValidationError("Input cannot be empty.")
        return value

    def validate_expected_output(self, value):
        if not value.strip():
            raise serializers.ValidationError("Expected output cannot be empty.")
        return value

    def validate_marks(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Marks must be between 1 and 100.")
        question = self.instance.question
        other_marks = sum(
            question.test_cases.exclude(pk=self.instance.pk).values_list("marks", flat=True)
        )
        if other_marks + value > question.total_marks:
            raise serializers.ValidationError(
                "The test-case marks cannot exceed the question total."
            )
        return value

    def validate(self, attrs):
        question = self.instance.question
        remains_sample = question.test_cases.filter(is_sample=True).exclude(
            pk=self.instance.pk
        ).exists() or attrs.get("is_sample", self.instance.is_sample)
        if not remains_sample:
            raise serializers.ValidationError(
                {"is_sample": "A question must keep at least one sample test case."}
            )
        if has_test_case_results(self.instance):
            changed_fields = [
                field
                for field, value in attrs.items()
                if value != getattr(self.instance, field)
            ]
            if changed_fields:
                raise serializers.ValidationError(
                    "A test case with recorded results cannot be changed."
                )
        return attrs


class QuestionSerializer(serializers.ModelSerializer):
    """Read representation of a question and its accessible test cases."""

    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    test_cases = serializers.SerializerMethodField()
    has_submissions = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = [
            "id",
            "title",
            "description",
            "input_format",
            "output_format",
            "constraints",
            "sample_input",
            "sample_output",
            "sample_explanation",
            "difficulty",
            "topic",
            "language",
            "total_marks",
            "status",
            "time_limit_seconds",
            "memory_limit_mb",
            "created_by",
            "created_by_email",
            "test_cases",
            "has_submissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_test_cases(self, obj):
        test_cases = obj.test_cases.all()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        is_faculty = bool(user and user.is_authenticated and user.is_faculty())
        if not is_faculty:
            test_cases = test_cases.filter(is_sample=True)
        return TestCaseSerializer(test_cases, many=True, context=self.context).data

    def get_has_submissions(self, obj):
        return question_has_submissions(obj)


class QuestionCreateUpdateSerializer(serializers.ModelSerializer):
    """Create/update a question, including its test cases atomically."""

    test_cases = TestCaseWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "title",
            "description",
            "input_format",
            "output_format",
            "constraints",
            "sample_input",
            "sample_output",
            "sample_explanation",
            "difficulty",
            "topic",
            "language",
            "total_marks",
            "status",
            "time_limit_seconds",
            "memory_limit_mb",
            "test_cases",
        ]
        read_only_fields = ["id"]

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_total_marks(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Total marks must be between 1 and 100.")
        return value

    def validate_time_limit_seconds(self, value):
        if value < 1 or value > 3600:
            raise serializers.ValidationError("Time limit must be between 1 and 3600 seconds.")
        return value

    def validate_memory_limit_mb(self, value):
        if value < 1 or value > 2048:
            raise serializers.ValidationError("Memory limit must be between 1 and 2048 MB.")
        return value

    def validate(self, attrs):
        test_cases = attrs.get("test_cases")
        total_marks = attrs.get(
            "total_marks",
            self.instance.total_marks if self.instance else Question._meta.get_field("total_marks").default,
        )

        if test_cases is not None:
            if not test_cases:
                raise serializers.ValidationError(
                    {"test_cases": "At least one test case is required."}
                )

            submitted_ids = [case["id"] for case in test_cases if "id" in case]
            if len(submitted_ids) != len(set(submitted_ids)):
                raise serializers.ValidationError({"test_cases": "Duplicate test-case IDs were submitted."})

            if self.instance:
                existing_cases = {case.id: case for case in self.instance.test_cases.all()}
                existing_ids = set(existing_cases)
                if any(case_id not in existing_ids for case_id in submitted_ids):
                    raise serializers.ValidationError({"test_cases": "A test case does not belong to this question."})
                submitted_id_set = set(submitted_ids)
                if any(
                    has_test_case_results(case)
                    for case_id, case in existing_cases.items()
                    if case_id not in submitted_id_set
                ):
                    raise serializers.ValidationError({
                        "test_cases": "A test case with recorded results cannot be removed."
                    })
                for case_data in test_cases:
                    case = existing_cases.get(case_data.get("id"))
                    if case and has_test_case_results(case):
                        changes = [
                            field
                            for field in ("input", "expected_output", "is_sample", "marks", "order")
                            if field in case_data and case_data[field] != getattr(case, field)
                        ]
                        if changes:
                            raise serializers.ValidationError({
                                "test_cases": "A test case with recorded results cannot be changed."
                            })
            elif submitted_ids:
                raise serializers.ValidationError({"test_cases": "New questions cannot include existing test-case IDs."})

            if test_cases:
                marks = sum(case.get("marks", 0) for case in test_cases)
                if marks != total_marks:
                    raise serializers.ValidationError({
                        "test_cases": f"Test-case marks ({marks}) must equal question total marks ({total_marks})."
                    })
                if not any(case.get("is_sample", False) for case in test_cases):
                    raise serializers.ValidationError({"test_cases": "At least one sample test case is required."})
        elif self.instance and self.instance.test_cases.exists():
            if total_marks != self.instance.total_marks:
                existing_marks = sum(self.instance.test_cases.values_list("marks", flat=True))
                if existing_marks != total_marks:
                    raise serializers.ValidationError({
                        "total_marks": f"Existing test-case marks ({existing_marks}) must equal total marks ({total_marks})."
                    })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        test_cases_data = validated_data.pop("test_cases", [])
        validated_data["created_by"] = self.context["request"].user
        question = Question.objects.create(**validated_data)
        for index, test_case_data in enumerate(test_cases_data, start=1):
            test_case_data.pop("id", None)
            test_case_data.setdefault("order", index)
            TestCase.objects.create(question=question, **test_case_data)
        return question

    @transaction.atomic
    def update(self, instance, validated_data):
        test_cases_data = validated_data.pop("test_cases", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if test_cases_data is not None:
            existing_cases = {test_case.id: test_case for test_case in instance.test_cases.all()}
            retained_ids = set()
            for index, test_case_data in enumerate(test_cases_data, start=1):
                test_case_id = test_case_data.pop("id", None)
                test_case_data.setdefault("order", index)
                if test_case_id:
                    test_case = existing_cases[test_case_id]
                    for field, value in test_case_data.items():
                        setattr(test_case, field, value)
                    test_case.save()
                    retained_ids.add(test_case_id)
                else:
                    test_case = TestCase.objects.create(question=instance, **test_case_data)
                    retained_ids.add(test_case.id)

            instance.test_cases.exclude(id__in=retained_ids).delete()

        return instance


class QuestionBulkCreateSerializer(serializers.Serializer):
    """Validate and create a batch of questions with nested test cases."""

    questions = QuestionCreateUpdateSerializer(many=True, allow_empty=False)

    def validate_questions(self, questions):
        if len(questions) > 100:
            raise serializers.ValidationError("A bulk import can contain at most 100 questions.")
        errors = [{} for _ in questions]
        for index, question in enumerate(questions):
            if not question.get("test_cases"):
                errors[index]["test_cases"] = "At least one test case is required for every imported question."
        if any(errors):
            raise serializers.ValidationError(errors)
        return questions

    @transaction.atomic
    def create(self, validated_data):
        question_list = self.fields["questions"]
        return question_list.create(validated_data["questions"])
