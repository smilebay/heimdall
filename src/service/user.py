from flask import current_app
from src.entity.user import User
from time import time
from src.entity.user import Roles
from src.util.password import encrypt, check
from src.repo.user import insert, find_by_email, update_last_login_data, update_password, update_email_verified
from pymysql import IntegrityError
from src.errors.custom_error import CustomError
from typing import Union
from src.util.jwt_ops import encode, decode
from jwt import InvalidTokenError


def register(user: User):
    """
    Tries to insert a new user to the database, send verification mail to him
    """

    try:
        user.ts_registration = time()
        user.ts_last_login = time()
        user.enabled = True
        user.email_verified = False
        user.roles = [Roles.ROLE_USER]
        user.password = encrypt(user.password)

        insert(user)
    except IntegrityError as e:
        raise CustomError(
            message="User already registered",
            status_code=400,
        )

    current_app.logger.debug('User with email {} registered'.format(user.email))

    # Send event to notification service for email validation


def login(email: str, password: str, last_login_ip: list) -> str:
    """
    Logs the user in (returns a jwt) if the user exists in database and the credentials are correct
    and update last login ip and last login date in the database and returns a jwt associated with the user
    """

    user: Union[None, User] = find_by_email(email)

    if user is None or not check(password, user.password):
        raise CustomError(
            message="Wrong credentials",
            status_code=401,
        )
    elif not user.enabled:
        raise CustomError(
            message="User is unauthorized by system admins",
            status_code=401,
        )
    elif not user.email_verified:
        raise CustomError(
            message="User's email is not verified.",
            status_code=401,
        )

    user.last_login_ip = last_login_ip

    update_last_login_data(user, int(time()))

    return encode(user.jwt_payload(), current_app.config["JWT_SECRET"], current_app.config["JWT_TTL"])


def forgot_password(email: str):
    """
    If the user exists in database, send a mail to him about resetting the password
    """

    user: Union[None, User] = find_by_email(email)

    if user is None:
        raise CustomError(
            message="User not found",
            status_code=401,
        )

    # Send a mail with jwt payload


def reset_password(email: str, new_password: str):
    """
    Change the password of the user
    """
    update_password(email, encrypt(new_password))

    current_app.logger.debug("Password updated for the user {}".format(email))


def verify(token: str):
    """
    Validates the token and extracts claims to update email verified field of the user
    """
    if token is None:
        raise CustomError(
            message="Jwt token is empty",
            status_code=400
        )

    try:
        decoded = decode(token, current_app.config["JWT_SECRET"])
    except InvalidTokenError:
        raise CustomError(
            message="Invalid Token",
            status_code=401
        )

    update_email_verified(decoded["email"], 1)

    current_app.logger.debug("Email verified field changed for user {} to {}".format(decoded["email"], 1))
