"""Single active student-session support for JWT authentication."""

import uuid

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
    TokenVerifySerializer,
)
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken


SESSION_CLAIM = "portal_session_id"
User = get_user_model()


def issue_session_refresh_token(user):
    """Issue tokens and replace any previously active student session."""
    if user.role == User.ROLE_STUDENT:
        with transaction.atomic():
            locked_user = User.objects.select_for_update().get(pk=user.pk)
            locked_user.active_session_id = uuid.uuid4()
            locked_user.save(update_fields=["active_session_id", "updated_at"])
            user.active_session_id = locked_user.active_session_id

    refresh = RefreshToken.for_user(user)
    if user.role == User.ROLE_STUDENT:
        refresh[SESSION_CLAIM] = str(user.active_session_id)
    return refresh


def _validate_student_session(user, token):
    """Reject stale student tokens while preserving non-student JWT behavior."""
    if user.role != User.ROLE_STUDENT:
        return

    token_session_id = token.get(SESSION_CLAIM)
    active_session_id = user.active_session_id
    if active_session_id is not None or token_session_id is not None:
        if active_session_id is None or str(token_session_id) != str(active_session_id):
            raise InvalidToken(
                "This student session is no longer active. Sign in again on this device."
            )


class SingleStudentSessionJWTAuthentication(JWTAuthentication):
    """Validate the student's active session on every authenticated API call."""

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        try:
            _validate_student_session(user, validated_token)
        except InvalidToken as error:
            raise AuthenticationFailed(
                "Your student session is no longer active. Please sign in again."
            ) from error
        return user


class PortalTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Attach a fresh active-session claim to student login tokens."""

    @classmethod
    def get_token(cls, user):
        return issue_session_refresh_token(user)


class PortalTokenRefreshSerializer(TokenRefreshSerializer):
    """Do not refresh JWTs that were invalidated by a newer student login."""

    def validate(self, attrs):
        refresh = RefreshToken(attrs["refresh"])
        user_id = refresh.get(api_settings.USER_ID_CLAIM)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, TypeError, ValueError) as error:
            raise InvalidToken("The account for this session no longer exists.") from error

        _validate_student_session(user, refresh)
        return super().validate(attrs)


class PortalTokenVerifySerializer(TokenVerifySerializer):
    """Report invalidated student tokens as invalid to token verification clients."""

    def validate(self, attrs):
        data = super().validate(attrs)
        token = UntypedToken(attrs["token"])
        user_id = token.get(api_settings.USER_ID_CLAIM)
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, TypeError, ValueError) as error:
            raise InvalidToken("The account for this session no longer exists.") from error

        _validate_student_session(user, token)
        return data
