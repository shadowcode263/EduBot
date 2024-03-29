"""Action validator for the Ngena."""
# pylint: disable=line-too-long
# pylint: disable=import-error
# pylint: disable=no-name-in-module
import re
import sys
import math
from io import BytesIO
import datetime
import requests
from django.core.cache import cache
from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from decouple import config
from courses.models import Course
from assignments.models import Assignment, PendingWork
from material.models import CourseMaterial
from quiz.models import Quiz
from tutorials.models import CallRequest, Conversation, Tutorial
from tutorials.serializers import CallRequestSerializer
from payments.models import Payment
from packages.models import Package
from users.serializers import UserSerializer
from users.models import User
from utils.helper_functions import (
    is_phone_number,
    payment_method
)
from services.quiz import QuizService
from services.paypal import PAYPALCLIENTAPI
from packages.models import Package
HOST = config("HOST", default="http://localhost:8000")


class ActionValidator(object):
    """Action validator for the Ngena."""

    def __init__(self):
        """Initialize the action validator."""
        self.registry = {
            "greet": self.greet,
            "user_exists": self.user_exists,
            "register": self.registration,
            "menu": self.menu,
            "enroll": self.enroll,
            "assignments": self.assignments,
            "profile": self.profile,
            "courses": self.my_courses,
            "payments": self.payments,
            "help": self.help,
            "about": self.about,
            "handle_payment": self.handle_payment,
            "join_class": self.join_class,
            "cancel_payment": self.cancel_payment
        }
        self.pagination = config("PAGINATION_COUNT", cast=int, default=5)
        self.pending_work = None

    # pylint: disable=unused-argument
    def greet(self, phone_number, message=None, session=dict):
        """Greet the user."""
        user = User.objects.filter(phone_number=phone_number)
        if user.exists():
            cache.set(phone_number, {
                "state": "menu",
                "data": None
            }, 60*60*24)
            return {
                "is_valid": True,
                "data": None,
                "message": {
                    "response_type": "interactive",
                    "username": "Welcome to Ngena. \n\n 📂 Enroll \n\n 📚 Courses \n\n 📝 Assignments \n\n 💳 Payments \n\n 👤 Profile\n\n 🆘 Help\n\n ℹ️ About Us\n\nWhat would you like to do?",
                    "menu_name": "Select Action",
                    "menu_items": [
                        {"id": "enroll", "name": "📂 Enroll",
                            "description": "Enroll in a course"},
                        {"id": "courses", "name": "📚 Courses",
                            "description": "View your courses"},
                        {"id": "assignments", "name": "📝 Assignments",
                            "description": "Go to assignments"},
                        {"id": "payments", "name": "💳 Payments",
                            "description": "View your payments"},
                        {"id": "profile", "name": "👤 Profile",
                            "description": "View your profile"},
                        {"id": "help", "name": "🆘 Help",
                            "description": "User guide"},
                        {"id": "about", "name": "ℹ️ About Us",
                            "description": "Contact Us"},
                    ]
                }
            }
        cache.set(phone_number, {
            "state": "greet",
            "data": None
        }, 60*60*24)
        return {
            "is_valid": False,
            "data": None,
            "message": {
                "response_type": "text",
                "text": "Welcome to *Ngena*. Let's sign you up to get started.\n\nWhat is your first name?"
            }
        }

    def user_exists(self, phone_number, message=None, session=dict, payload=dict):
        """Check if the user exists."""
        user = User.objects.filter(phone_number=phone_number)
        print("Session : ", session, "\n", phone_number, "->", message)
        if user.exists():
            cache.set(phone_number, {
                "state": "menu",
                "data": None
            }, 60*60*24)
            return {
                "is_valid": True,
                "data": None,
                "message": {
                    "response_type": "interactive",
                    "text": "*Main Menu*\n\n 📂 Enroll \n\n 📚 Courses \n\n 📝 Assignments \n\n 💳 Payments \n\n 👤 Profile\n\n 🆘 Help\n\n ℹ️ About Us\n\nWhat would you like to do?",
                    "username": f"{user.first().first_name} {user.first().last_name}",
                    "menu_name": "🏠 Select Action",
                    "menu_items": [
                        {"id": "enroll", "name": "📂 Enroll",
                            "description": "Enroll in a course"},
                        {"id": "courses", "name": "📚 Courses",
                            "description": "View your courses"},
                        {"id": "assignments", "name": "📝 Assignments",
                            "description": "Go to assignments"},
                        {"id": "payments", "name": "💳 Payments",
                            "description": "View your payments"},
                        {"id": "profile", "name": "👤 Profile",
                            "description": "View your profile"},
                        {"id": "help", "name": "🆘 Help",
                            "description": "User guide"},
                        {"id": "about", "name": "ℹ️ About Us",
                            "description": "Contact Us"},

                    ]
                }
            }
        message = "Welcome to *Ngena*. Sign up to get started.\n\nWhat is your first name?" if not user.exists() else ""
        return {
            "is_valid": user.exists(),
            "data": user.first() if user.exists() else None,
            "message": {
                "response_type": "text",
                "text": message
            }
        }

    def registration(self, phone_number, message=None, session=dict, payload=dict):
        """Validate the registration action."""
        user = User.objects.filter(phone_number=phone_number)
        print("Session : ", session, "\n", phone_number, "->", message)
        if not user.exists():
            if session:
                if not session.get("data").get("password"):
                    session["data"]["password"] = phone_number
                if not session.get("data").get("phone_number"):
                    session["data"]["phone_number"] = phone_number
                if not session.get("data").get("username"):
                    session["data"]["username"] = phone_number

                if not session.get("data").get("role"):
                    session["data"]["role"] = "STUDENT"

                if not session["data"].get("first_name") and message:
                    regex_legal_name = r"^[a-zA-Z]+(([',. -][a-zA-Z ])?[a-zA-Z]*)*$"
                    if not re.match(regex_legal_name, message):
                        return {
                            "is_valid": False,
                            "data": "Invalid first name",
                            "message": {
                                "response_type": "text",
                                "text": f"{message} is not a valid first name.\n\nPlease enter a valid first name",
                            }
                        }
                    session["data"]["first_name"] = message
                    message = None

                if not session["data"].get("last_name") and message:
                    regex_legal_name = r"^[a-zA-Z]+(([',. -][a-zA-Z ])?[a-zA-Z]*)*$"
                    if not re.match(regex_legal_name, message):
                        return {
                            "is_valid": False,
                            "data": "Invalid last name",
                            "message": {
                                "response_type": "text",
                                "text": f"{message} is not a valid last name.\n\nPlease enter a valid last name"
                            }
                        }
                    session["data"]["last_name"] = message
                    message = None

                if not session["data"].get("email") and message:
                    # Validate email including emails that start with numbers, can have hyphens and underscores and Capital letters
                    email_address_regex = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
                    print("Validating email address", re.match(
                        email_address_regex, message))
                    if not re.match(email_address_regex, message):
                        return {
                            "is_valid": False,
                            "data": "Invalid email",
                            "message": {
                                "response_type": "text",
                                "text": f"{message} is not a valid email.\n\nPlease enter a valid email address"
                            }
                        }
                    else:
                        session["data"]["email"] = message
                    message = None
                cache.set(phone_number, session, 60*60*24)

                if not session["data"].get("sex") and message:
                    if message.title() not in ["Male", "Female", "Other"]:
                        return {
                            "is_valid": False,
                            "data": "Invalid sex",
                            "message": {
                                "response_type": "text",
                                "text": f"{message} should be Male or Female or Other.\n\nPlease enter your sex"
                            }
                        }
                    else:
                        session["data"]["sex"] = message.upper()
                    message = None
                cache.set(phone_number, session, 60*60*24)
        serializer = UserSerializer(data=session["data"])
        is_valid = serializer.is_valid()
        if not is_valid:
            message = serializer.errors[
                "non_field_errors"
            ][0].replace("ErrorDetail(string='", "").replace("', code='invalid')", "")
            print(message)
        else:
            serializer.save()
            message = f"Welcome *{serializer.data.get('first_name')} {serializer.data.get('last_name')}* to *Ngena*.\n\nYou have successfully registered.You can now access the *Ngena* menu to get started."
        return {
            "is_valid": is_valid,
            "data": serializer.data if is_valid else serializer.errors,
            "message": {
                "exclude_back": True,
                "response_type": "button" if is_valid else "text",
                "text": message,
            }
        }

    def menu(self, phone_number, message=None, session=dict, payload=dict):
        """Validate the menu action."""
        user = User.objects.filter(phone_number=phone_number)
        print("MENU SESSION : ", session, "\n", user, "->", message)
        if not user.exists():
            cache.set(phone_number, {
                "state": "register",
                "data": None
            }, 60*60*24)
            return {
                "is_valid": False,
                "data": "User does not exist",
                "message": {
                    "response_type": "text",
                    "text": "You are not registered with Ngena.  Sign up to get started.\n\nWhat is your first name?"
                }
            }
        cache.set(phone_number, {
            "state": "menu",
            "data": None
        }, 60*60*24)
        return {
            "is_valid": True,
            "data": user.first(),
            "message": {
                "response_type": "interactive",
                "text": "*Main Menu*\n\n 📂 Enroll \n\n 📚 Courses \n\n 📝 Assignments \n\n 💳 Payments \n\n 👤 Profile\n\n 🆘 Help\n\n ℹ️ About Us\n\nWhat would you like to do?",
                "username": f"{user.first().first_name} {user.first().last_name}",
                "menu_name": "🏠 Select Action",
                "menu_items": [
                    {"id": "enroll", "name": "📂 Enroll",
                        "description": "Enroll in a course"},
                    {"id": "courses", "name": "📚 Courses",
                        "description": "View your courses"},
                    {"id": "assignments", "name": "📝 Assignments",
                        "description": "Go to assignments"},
                    {"id": "payments", "name": "💳 Payments",
                        "description": "View your payments"},
                    {"id": "profile", "name": "👤 Profile",
                        "description": "View your profile"},
                    {"id": "help", "name": "🆘 Help", "description": "User guide"},
                    {"id": "about", "name": "ℹ️ About Us",
                        "description": "Contact Us"},
                ]
            }
        }

    def enroll(self, phone_number, message=None, session=dict, payload=dict):
        """Validate the enroll action."""
        user = User.objects.filter(phone_number=phone_number)

        # pylint: disable=no-member
        user_courses = [
            course.code for course in user.first().enrolled_courses.all()]
        user_courses.append("COUT")
        courses = Course.objects.all().exclude(code__in=user_courses)
        if cache.get(phone_number):
            session = cache.get(phone_number)

            if session.get("state") == "enroll":
                if session["data"].get("selected_course"):
                    print("Selected course >>>>>>>>>> ",
                          session["data"]["selected_course"])
                    if session["data"]["action"] == "select_package":
                        session["data"]["selected_package"] = message
                        package = Package.objects.get(
                            id=session["data"]["selected_package"])
                        course = Course.objects.get(
                            code=session["data"]["selected_course"])
                        cache.set(phone_number, session, 60*60*24)
                        return {
                            "is_valid": False,
                            "data": user.first(),
                            "message": {
                                "response_type": "interactive",
                                "text": f"*Payment Options*\n\n 🇺🇸 PayPal\n\n 🇿🇼 PayNow \n\nSelect payment option to purchase {course.name.capitalize()}\n\nYou will be enrolled in {course.name.capitalize()} {package.name.capitalize()} package with access to {package.get_permissions()}.\n\nYou will be charged *${package.price}* for this package.",
                                "username": f"{user.first().first_name} {user.first().last_name}",
                                "menu_name": "Purchase",
                                "menu_items": [
                                    {
                                        "id": "handle_payment",
                                        "name": "🇺🇸 PayPal",
                                        "description": "Complete purchase with PayPal",
                                    },
                                    {
                                        "id": "disabled",
                                        "name": "🇿🇼 PayNow (Disabled)",
                                        "description": "Complete purchase with PayNow",
                                    },
                                ]
                            }
                        }

                    elif message == "disabled":
                        print("PAYNOW")
                        session["data"]["payment_method"] = "select_package"
                        cache.set(phone_number, session, 60*60*24)
                        return {
                            "is_valid": False,
                            "data": user.first(),
                            "message": {
                                "response_type": "text",
                                "text": "*🇿🇼 PayNow*\n\nThis feature is currently disabled. Please select another payment option.",
                            }
                        }
                    elif message == "paynow":
                        print("PAYNOW")
                        session["data"]["payment_method"] = "paynow"
                        cache.set(phone_number, session, 60*60*24)
                        return {
                            "is_valid": False,
                            "data": user.first(),
                            "message": {
                                "response_type": "text",
                                "text": "*🇿🇼 PayNow*\n\nPlease enter the phone number you want to pay with\n\ne.g. 0771111111\n\n*NB:* _The number should be registered with Ecocash or OneMoney._",
                            }
                        }
                    elif session["data"].get("payment_method") == "paynow" and session["data"].get("paying_phone_number") is None:
                        if not is_phone_number(message):
                            return {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "text",
                                    "text": f"*🇿🇼 PayNow*\n\n{message} is not a valid number, please enter a valid phone number ",
                                }
                            }

                        if payment_method(message) in ["ecocash", "onemoney"] and message != "retry":
                            if message == "retry":
                                message = session["data"]["payee"]
                            session["data"]["payee"] = message
                            cache.set(phone_number, session, 60*60*24)
                            course = Course.objects.get(
                                code=session["data"]["selected_course"])
                            package = Package.objects.get(
                                name=session["data"]["selected_package"])
                            method = payment_method(message)
                            print(course, package, method)
                            # pylint: disable=no-value-for-parameter
                            payment = Payment.create_payment(
                                course=course,
                                package=package,
                                method=method,
                                user=user.first(),
                                payment_type=session["data"]["payment_method"],
                            )
                            print(payment)
                            response = Payment.send_payment_request(
                                payment, message)
                            if response.get("status") == "Error":
                                print("ERROR==============>>>>", phone_number)
                                Payment.objects.filter(id=payment.id).update(
                                    payment_status="Declined")

                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "response_type": "text",
                                        "text": f"*🇿🇼 PayNow*\n\nFailed to process payment with error *{response.get('error')}*\n\nPlease try entering your phone number again.",
                                    }
                                }
                            # Initiate payment here
                            return {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "text",
                                    "text": f"*🇿🇼 PayNow*\n\nYour ${payment.amount} {payment_method(message).lower()} payment has been initiated. Please complete the payment on your handset on prompt.",
                                }
                            }
                        else:
                            return {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "text",
                                    "text": f"*🇿🇼 PayNow*\n\n{payment_method(message).title()} is not supported. Please enter a valid Ecocash or OneMoney phone number.",
                                }
                            }

                    else:
                        return {
                            "is_valid": False,
                            "data": "Invalid selection",
                            "message": {
                                "exclude_back": True,
                                "response_type": "button",
                                "text": "*Invalid selection*\n\nPlease select a valid option from the menu.",
                            }
                        }
                elif message in [course.code for course in courses]:
                    print("COURSE: ", message)
                    print("PACKAGE: ", Package.objects.filter(
                        service_type="course_registration"))
                    course = Course.objects.get(code=message)
                    session["data"]["selected_course"] = message
                    session['data']['action'] = 'select_package'
                    cache.set(phone_number, session, 60*60*24)
                    return {
                        "is_valid": False,
                        "data": user.first(),
                        "message": {
                            "response_type": "interactive",
                            "text": f"*Subscription Packages*\n\n*Course:* {course.name}\n*Duration:* {course.duration} week(s)\n\n*Description*\n\n{course.description}\n\n",
                            "username": f"{user.first().first_name} {user.first().last_name}",
                            "menu_name": "📦 Available Packages",
                            "menu_items": [
                                {
                                    "id": package.id,
                                    "name": f"{package.name.title()} (${package.price})",
                                    "description": f"{package.description}",
                                } for package in Package.objects.filter(service_type="course_registration")
                            ]
                        }
                    }
                cache.set(phone_number, session, 60*60*24)
                return {
                    "is_valid": False,
                    "data": user.first(),
                    "message": {
                        "response_type": "interactive",
                        "text": "Select a course to enroll in.",
                        "username": f"{user.first().first_name} {user.first().last_name}",
                        "menu_name": "📚 Available Courses",
                        "menu_items": [
                            {
                                "id": course.code,
                                "name": course.name,
                                "description": f"{course.description[:45]}...",
                            } for course in courses[:10]
                        ]
                    }
                }

        session = {
            "state": "enroll",
            "data": {
                "page": 1,
                "total_pages": math.ceil(len(courses)/5),
                "selected_course": None
            }
        }
        cache.set(phone_number, session, 60*60*24)
        def generate_menu(courses_list): return [
            f"{count}. {course.name}" for count, course in enumerate(courses_list, 1)]
        return {
            "is_valid": False,
            "data": user.first(),
            "message": {
                "response_type": "interactive",
                "text": "*Available Courses* \n\n" + "\n\n".join(generate_menu(courses[:self.pagination])) + f"\n\nPage {session['data']['page']} of {math.ceil(len(courses)/5)}",
                "username": f"{user.first().first_name} {user.first().last_name}",
                "menu_name": "📚 Available Courses",
                "menu_items": [
                    {
                        "id": course.code,
                        "name": f"📚 {course.name}",
                        "description": f"{course.description[:45]}...",
                    } for course in courses
                ]
            }
        } if courses else {
            "is_valid": False,
            "data": user.first(),

            "message": {
                "exclude_back": True,
                "menu": "course_menu",
                "response_type": "button",
                "text": "*No Courses Available!!*\n\nNo courses available at the moment.\nPlease contact tutor to upload courses.",
            }
        }

    def my_courses(self, phone_number, message, session, payload=dict):
        """My courses menu"""
        user = User.objects.filter(phone_number=phone_number)
        # pylint: disable=no-member
        courses = Course.objects.filter(students__in=user).exclude(code="COUT")
        base = []
        if session.get("data"):
            if session["data"].get("total_pages"):
                pass
        else:
            session["data"] = {
                "page": 1,
                "total_pages": math.ceil(len(courses)/self.pagination)
            }
        base = []
        if message == "next":
            base = []
            session["data"]["page"] += 1
            cache.set(phone_number, session, 60*60*24)
            if session["data"]["page"] > 1:
                base.append({
                    "id": "previous",
                    "name": "Previous",
                    "description": "Previous page"
                })
            if session["data"]["page"] < session["data"]["total_pages"]:
                base.append({
                    "id": "next",
                    "name": "Next",
                    "description": "Next page"
                })

            def generate_menu(courses_list): return [
                f"{count}. {course.name}" for count, course in enumerate(courses_list, 1)]
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "interactive",
                    "text": f"*Your Courses ({session['data']['page']} of {math.ceil(len(courses)/self.pagination)}).*\n\n" + "\n\n".join(generate_menu(courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination])),
                    "username": f"{user.first().first_name} {user.first().last_name}",
                    "menu_name": "📚 My Courses",
                    "menu_items": [
                        {
                            "id": course.code,
                            "name": f"📚 {course.name}",
                            "description": f"{course.description[:45]}...",
                        } for course in courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination]
                    ] + base
                }
            }
        elif message == "previous":
            base = []
            if session["data"]["page"] > 1:
                session["data"]["page"] -= 1
                cache.set(phone_number, session, 60*60*24)

            if session["data"]["page"] > 1:
                base.append({
                    "id": "previous",
                    "name": "Previous",
                    "description": "Previous page"
                })

            print("\n\nSESSION : ", session["data"], session["data"]["page"], math.ceil(len(
                courses)/self.pagination), session["data"]["page"] < math.ceil(len(courses)/self.pagination))
            if session["data"]["page"] < math.ceil(len(courses)/self.pagination):
                base.append({
                    "id": "next",
                    "name": "Next",
                    "description": "Next page"
                })

                def generate_menu(courses_list): return [
                    f"{count}. {course.name}" for count, course in enumerate(courses_list, 1)]
                return {
                    "is_valid": True,
                    "data": user.first(),
                    "message": {
                        "response_type": "interactive",
                        "text": f"*Your Courses({session['data']['page']} of {math.ceil(len(courses)/self.pagination)})*\n\n" + " \n\n ".join(generate_menu(courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination])),
                        "username": f"{user.first().first_name} {user.first().last_name}",
                        "menu_name": "📚 My Courses",
                        "menu_items": [
                            {
                                "id": course.code,
                                "name": f"📚 {course.name}",
                                "description": f"{course.description[:45]}...",
                            } for course in courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination]
                        ] + base
                    }
                }
            return {
                "is_valid": False,
                "data": user.first(),
                "message": {
                    "response_type": "button",
                    "text": "You are already on the first page."
                }
            }
        else:
            if not session["data"].get("selected_course") and message not in [i.code for i in courses]:
                print("NO SELECTED COURSE AND MESSAGE NOT IN COURSES")
                session = {
                    "state": "my_courses",
                    "data": {
                        "page": 1,
                        "total_pages": math.ceil(len(courses)/self.pagination),
                        "selected_course": None
                    }
                }
                cache.set(phone_number, session, 60*60*24)
                if session["data"]["page"] > config('PAGINATION_COUNT', cast=int):
                    base.append({
                        "id": "previous",
                        "name": "Previous",
                        "description": "Previous page"
                    })
                if session["data"]["page"] < math.ceil(len(courses)/self.pagination):
                    base.append({
                        "id": "next",
                        "name": "Next",
                        "description": "Next page"
                    })
                menu_items = [
                    {
                        "id": course.code,
                        "name": f"📚 {course.name}",
                        "description": f"{course.description[:45]}...",
                    } for course in courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination]
                ]
                if base and menu_items and courses.count() > self.pagination:
                    menu_items.extend(base)

                def generate_menu(courses_list): return [
                    f"{count}. {course.name}" for count, course in enumerate(courses_list, 1)]
                return {
                    "is_valid": False,
                    "data": user.first(),
                    "message": {
                        "response_type": "interactive",
                        "text": f"*Your Courses (Page {session['data']['page']} of {math.ceil(len(courses)/self.pagination)})*\n\n" + " \n\n ".join(generate_menu(courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination])),
                        "username": f"{user.first().first_name} {user.first().last_name}",
                        "menu_name": "📚 My Courses",
                        "menu_items": menu_items
                    }
                } if courses else {
                    "is_valid": False,
                    "data": user.first(),
                    "message": {
                        "response_type": "button",
                        "text": "*Oops!*\n\n You are not enrolled in any course at the moment.  Please try again later.",
                    }
                }
            else:
                print("SELECTED COURSE OR MESSAGE IN COURSES",
                      session["data"].get("selected_course"))
                if message in [i.code for i in courses]:
                    session["data"]["selected_course"] = message
                    session["action"] = "course_menu"
                    cache.set(phone_number, session, 60*60*24)
                    course = Course.objects.get(code=message)
                    return {
                        "is_valid": False,
                        "data": user.first(),
                        "message": {
                            "response_type": "interactive",
                            "text": f"*Course Menu ({user.first().course_package(session['data']['selected_course']).name.title() if user.first().course_package(session['data']['selected_course']) else 'No Package Detected'})*\n\n 📜 Outline\n\n 📹 Tutorials\n\n 📚 Material\n\n 📊 Assessment\n\n 👨‍🏫📞 Schedule Call\n\n 🗣 Conversation\n\n 🔙 Back\n\nSelect an option to continue.",
                            "username": f"{user.first().first_name} {user.first().last_name}",
                            "menu_name": f"📚 {course.name}",
                            "menu_items": [
                                {
                                    "id": "course_outline",
                                    "name": "📜 Outline",
                                    "description": "Course Outline"
                                },
                                {
                                    "id": "tutorials",
                                    "name": "📹 Tutorials",
                                    "description": "Course Tutorial"
                                },
                                {
                                    "id": "course_material",
                                    "name": "📚 Material",
                                    "description": "Course Material"
                                },
                                {
                                    "id": "course_assessment",
                                    "name": "📊 Assessment",
                                    "description": "Course Assessment"
                                },
                                {
                                    "id": "request_call",
                                    "name": "👨‍🏫📞 Schedule Call",
                                    "description": "Request a call from a tutor"
                                },
                                {
                                    "id": "conversation",
                                    "name": "🗣 Conversation",
                                    "description": "Conversation"

                                },
                                {
                                    "id": "back_to_courses",
                                    "name": "🔙 Back",
                                    "description": "Back to courses"
                                }
                            ]
                        }
                    }
                elif message == "course_menu":
                    session["action"] = "course_menu"
                    session["data"] = {
                        "selected_course": session["data"]["selected_course"],
                        "page": 1,
                    }
                    cache.set(phone_number, session, 60*60*24)
                    course = Course.objects.get(
                        code=session["data"]["selected_course"])
                    return {
                        "is_valid": False,
                        "data": user.first(),
                        "message": {
                            "response_type": "interactive",
                            "text": f"*Course Menu({user.first().course_package(session['data']['selected_course']).name.title() if user.first().course_package(session['data']['selected_course']) else 'No Package Detected'})*\n\n 📜 Outline\n\n 📹 Tutorials\n\n 📚 Material\n\n 📊 Assessment\n\n 👨‍🏫📞 Schedule Call\n\n 🗣 Conversation\n\n 🔙 Back\n\nSelect an option to continue.",
                            "username": f"{user.first().first_name} {user.first().last_name}",
                            "menu_name": f"📚 {course.name}",
                            "menu_items": [
                                {
                                    "id": "course_outline",
                                    "name": "📜 Outline",
                                    "description": "Course Outline"
                                },
                                {
                                    "id": "tutorials",
                                    "name": "📹 Tutorials",
                                    "description": "Course Tutorial"
                                },
                                {
                                    "id": "course_material",
                                    "name": "📚 Material",
                                    "description": "Course Material"
                                },
                                {
                                    "id": "course_assessment",
                                    "name": "📊 Assessment",
                                    "description": "Course Assessment"
                                },
                                {
                                    "id": "request_call",
                                    "name": "👨‍🏫📞 Schedule Call",
                                    "description": "Request a call from a tutor"
                                },
                                {
                                    "id": "conversation",
                                    "name": "🗣 Conversation",
                                    "description": "Conversation"

                                },
                                {
                                    "id": "back_to_courses",
                                    "name": "🔙 Back",
                                    "description": "Back to courses"
                                }
                            ]
                        }
                    }
                else:
                    if session["data"].get("selected_course") and message in ["course_outline", "back", "Outline"]:
                        session["back"] = -3
                        session["data"] = {
                            'selected_course': session['data']['selected_course'],
                            'page': 1
                        }
                        cache.set(f"bookmark_{phone_number}", -2, 60*60*24)
                        course = Course.objects.get(
                            code=session["data"]["selected_course"])
                        return {
                            "is_valid": False,
                            "data": user.first(),
                            "message": {
                                "menu": "course_menu",
                                "exclude_back": True,
                                "response_type": "button",
                                "text": f"*📜 _Course Outline_*\n\n{course.description[:1024]}",
                            }
                        }

                    else:
                        print("Message", message, session["data"].get(
                            "selected_course"), session['data'].get("action"), session["data"].get("stage"))
                        if message.lower() in ["back_to_courses", "courses"]:
                            session = {
                                "action": "my_courses",
                                "data": {
                                    "page": 1,
                                    "total_pages": math.ceil(len(courses)/self.pagination),
                                    "selected_course": None
                                }
                            }
                            cache.set(phone_number, session, 60*60*24)
                            if session["data"]["page"] > 1:
                                base.append({
                                    "id": "previous",
                                    "name": "Previous",
                                    "description": "Previous page"
                                })
                            if session["data"]["page"] < session["data"]["total_pages"]:
                                base.append({
                                    "id": "next",
                                    "name": "Next",
                                    "description": "Next page"
                                })
                            menu_items = [
                                {
                                    "id": course.code,
                                    "name": f"📚 {course.name}",
                                    "description": f"{course.description[:45]}..."
                                } for course in courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination]
                            ]
                            if base and menu_items and courses.count() > self.pagination:
                                menu_items.extend(base)
                                ##

                            def generate_menu(courses_list): return [
                                f"*{count}.* {item.name}" for count, item in enumerate(courses_list, 1)]
                            return {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "interactive",
                                    "text": f"*Your Courses (Page {session['data']['page']} of {session['data']['total_pages']})*\n\n" + " \n\n ".join(generate_menu(courses[session["data"]["page"]*self.pagination-self.pagination:session["data"]["page"]*self.pagination])),
                                    "username": f"{user.first().first_name} {user.first().last_name}",
                                    "menu_name": "📚 My Courses",
                                    "menu_items": menu_items
                                }
                            } if courses else {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "button",
                                    "text": "Oops! You are not enrolled in any course at the moment.  Please try again later.",
                                }
                            }

                        elif message.lower() in  ["request_call", "schedule call", "schedule", "call"] or session['data'].get("action") == "request_call" or session['data'].get("stage") in ["date_of_call", "agenda", "call_type"]:
                            session['data']["action"] = "request_call"

                            if not user.first().has_active_permission_for_course(session["data"].get("selected_course")):
                                session["data"] = {
                                    'selected_course': session['data']['selected_course'],
                                    'page': 1
                                }
                                cache.set(phone_number, session, 60*60*24)
                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "menu": "course_menu",
                                        "exclude_back": True,
                                        "response_type": "button",
                                        "text": "*Request Call Unauthorised* \n\nYour subscription does not allow you to request a call. Please upgrade your subscription to request calls.",
                                    }
                                }

                            if CallRequest.call_request_exists(user=user.first(), course=Course.objects.get(code=session["data"].get("selected_course")), date_of_call=datetime.datetime.today()):
                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "menu": "course_menu",
                                        "exclude_back": True,
                                        "response_type": "button",
                                        "text": "Request Call \n\nYou already have another pending call scheduled for today.",
                                    }
                                }
                            


                            payload = session['data'].get('payload')
                            # date fommat 2020-12-12 12:00 or 2020-12-12
                            regex_date_time = r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})\s(?P<hour>\d{2}):(?P<minute>\d{2})$"
                            regex_date = r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$"
                            regex_time = r"^(?P<hour>\d{2}):(?P<minute>\d{2})$"
                            print("\n\n\n\n#####################Request call",
                                  session['data'].get("action"), payload, message)
                            print("Regex", re.match(regex_date_time, message))

                            if session['data'].get("stage") == "date_of_call" and (re.match(regex_date_time, message) or re.match(regex_date, message) or re.match(regex_time, message)):
                                if re.match(regex_time, message):
                                    message = f"{datetime.datetime.today().strftime('%Y-%m-%d')} {message}"
                                payload["date_of_call"] = message
                                session['data']["payload"] = payload
                                session['data']["stage"] = "call_type"
                                cache.set(phone_number, session, 60*60*24)
                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "response_type": "text",
                                        "text": "Request Call\n\nWhat topic or concept would you like to discuss?",
                                    }
                                }
                            
                            if session['data'].get("stage") == "call_type":
                                payload["agenda"] = message
                                session['data']["payload"] = payload
                                session['data']["stage"] = "agenda"
                                cache.set(phone_number, session, 60*60*24)
                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "response_type": "interactive",
                                        "text": "Call Type\n\nWhat is type of call?",
                                        "menu_name": "📅 Agenda",
                                        "menu_items": [
                                            {
                                                "id": item,
                                                "name": item,
                                                "description": item,
                                            } for item in user.first().call_permissions(session["data"].get("selected_course")) if item != "Curated Content"
                                        ] if user.first().call_permissions(session["data"].get("selected_course")) else [
                                            {
                                                "id": "course_menu",
                                                "name": "Menu",
                                                "description": "No call permissions",
                                            }
                                        ]
                                    }
                                }
                            
                            
                            if session['data'].get("stage") == "agenda":
                                payload["call_type"] = message
                                session['data']["payload"] = payload
                                cache.set(phone_number, session, 60*60*24)

                            serializer = CallRequestSerializer(
                                data=payload, context={"user": user.first()})
                            if serializer.is_valid():
                                serializer.save()
                                session['data']["action"] = "course_menu"
                                cache.set(phone_number, session, 60*60*24)
                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "menu": "course_menu",
                                        "exclude_back": True,
                                        "response_type": "button",
                                        "text": "Request Call\n\nYour request has been received. We will contact you shortly.",
                                    }
                                }

                            else:
                                print("Invalid serializer",
                                      serializer.errors, payload)
                                if not payload:
                                    session['data']["payload"] = {
                                        "requested_by": user.first().id,
                                        "course": Course.objects.get(code=session["data"]["selected_course"]).id
                                    }
                                    session['data']["action"] = "request_call"
                                    session['data']["stage"] = "date_of_call"
                                    cache.set(phone_number, session, 60*60*24)
                                    print("Session", cache.get(phone_number))
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "response_type": "text",
                                            "text": "Request Call\n\nWhen would you like to be contacted today ?\n\n_Please enter a valid time in the format e.g. *14:00*_",
                                        }
                                    }
                                # REQUEST CALL FAILED
                                session['data']["action"] = "course_menu"
                                session['data']["payload"] = {}
                                session['data']["stage"] = ""

                                cache.set(phone_number, session, 60*60*24)
                                message = f"{list(serializer.errors.values())[0][0]}".replace("[ErrorDetail(string='", "").replace(
                                    "', code='invalid')]", "").replace("YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].", "YYYY-MM-DDThh:mm").lstrip()

                                return {
                                    "is_valid": False,
                                    "data": user.first(),
                                    "message": {
                                        "menu": "course_menu",
                                        "exclude_back": True,
                                        "response_type": "button",
                                        "text": f"Request Call Failed \n\n{message}",
                                    }
                                }

                        elif message.lower() == "tutorials" or session['data'].get("action") == "tutorials":
                            print("Tutorials", session['data'].get(
                                "action"), message, session['data'].get("tutorial_stage"))
                            if session['data'].get("tutorial_stage") is None:
                                print("Tutorials is Nonne", session['data'].get(
                                    "action"), message, session['data'].get("tutorial_stage"))
                                session['data']["tutorial_stage"] = "select_tutorial"
                                cache.set(phone_number, session, 60*60*24)
                                tutorials = Tutorial.objects.filter(
                                    course__code=session["data"].get("selected_course"), published=True)
                                if tutorials:
                                    # Pagination for tutorials
                                    if session['data'].get("action") == "tutorials":
                                        if message == "next":
                                            session['data']["page"] += 1
                                        elif message == "previous":
                                            session['data']["page"] -= 1
                                        cache.set(phone_number,
                                                  session, 60*60*24)
                                    else:
                                        session['data']["action"] = "tutorials"
                                        session['data']["page"] = 1
                                        cache.set(phone_number,
                                                  session, 60*60*24)
                                    # Pagination for tutorials
                                    tutorials = tutorials[(
                                        session['data']["page"]-1)*self.pagination:session['data']["page"]*self.pagination]
                                    base = []
                                    if message == "next":
                                        base = []
                                        session["data"]["page"] += 1
                                        cache.set(phone_number,
                                                  session, 60*60*24)

                                    if session["data"]["page"] > 1:
                                        base.append({
                                            "id": "previous",
                                            "name": "Previous",
                                            "description": "Previous page"
                                        })
                                    if session["data"]["page"] < math.ceil(len(tutorials)/self.pagination):
                                        base.append({
                                            "id": "next",
                                            "name": "Next",
                                            "description": "Next page"
                                        })
                                    if base and tutorials and courses.count() > self.pagination:
                                        tutorials.extend(base)

                                    def generate_menu(tutorials_list): return [
                                        f"{count}. *{tutorial.title}*" for count, tutorial in enumerate(tutorials_list[:8], 1)]
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "response_type": "interactive",
                                            "text": f"*Tutorials (Page {session['data']['page']} of {math.ceil(len(tutorials)/self.pagination)}).* \n\n" + " \n\n ".join(generate_menu(tutorials)) + "\n\nSelect a tutorial to start tutorial.",
                                            "username": f"{user.first().first_name} {user.first().last_name}",
                                            "menu_name": "📹 Tutorials",
                                            "menu_items": [
                                                {
                                                    "id": f"{tutorial.id}",
                                                    "name": tutorial.title,
                                                    "description": tutorial.description[:69] + "..." if len(tutorial.description) > 69 else tutorial.description,
                                                } for tutorial in tutorials
                                            ] + base
                                        }
                                    }
                                else:
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "menu": "course_menu",
                                            "exclude_back": True,
                                            "response_type": "button",
                                            "text": "*No tutorials yet!!*\n\nNo tutorials have been added to this course yet.\n\nPlease select another course or contact your tutor for more information.",
                                        }
                                    }

                            elif session['data'].get("tutorial_stage") == "select_tutorial":
                                print("Tutorials is select_tutorial", session['data'].get(
                                    "action"), message, session['data'].get("tutorial_stage"))
                                uuid4 = re.compile(
                                    r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', re.I)

                                session['data']["tutorial_identifier"] = message if uuid4.match(
                                    message) else session['data'].get("tutorial_identifier")
                                print("Tutorials is select_tutorial >>>>>>>>>> ",
                                      session['data'].get("tutorial_identifier"))
                                tutorial = Tutorial.objects.filter(
                                    id=session['data']["tutorial_identifier"], published=True)

                                print("Tutorials is select_tutorial", tutorial)
                                try:
                                    if tutorial:
                                        tutorial = tutorial.first()
                                        print("STEPS : ", tutorial.steps.all())
                                        session['data']["tutorial_stage"] = "ongoing_tutorial"
                                        session['data']["selected_tutorial"] = message
                                        cache.set(phone_number,
                                                  session, 60*60*24)
                                        if session.get("data").get("step_position") is None:
                                            session["data"]["step_position"] = 1
                                            is_first_step = True

                                            cache.set(phone_number,
                                                      session, 60*60*24)
                                        steps = tutorial.steps.all().order_by("id")
                                        is_last_step = False
                                        if steps:
                                            if session["data"]["step_position"] < len(steps):
                                                step = steps[0]
                                                if step.content_type == "text":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "tutorial",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                        }
                                                    }
                                                elif step.content_type == "image":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls":  True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "image",
                                                            "text": f"{step.instructions}",
                                                            "image":  f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                elif step.content_type == "video":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "video",
                                                            "text": f"{step.instructions}",
                                                            "video": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                elif step.content_type == "audio":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "audio",
                                                            "text": f"{step.instructions}",
                                                            "audio": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                elif step.content_type == "document":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "document",
                                                            "text": f"{step.instructions}",
                                                            "document": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                # session["data"]["step_position"] += 1
                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                            else:
                                                session['data']["tutorial_stage"] = "select_tutorial"
                                                session['data']["step_position"] = None
                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                                return {
                                                    "is_valid": False,
                                                    "data": user.first(),
                                                    "message": {
                                                        "response_type": "text",
                                                        "text": "🏁 The End\n\nCongratulations! You have reached the end of the tutorial.\n\nYou can select another tutorial to continue learning or go to *Assessment* to test your knowledge.",
                                                    }
                                                }
                                        else:
                                            session['data']["tutorial_stage"] = "select_tutorial"
                                            session['data']["step_position"] = None
                                            cache.set(phone_number,
                                                      session, 60*60*24)
                                            return {
                                                "is_valid": False,
                                                "data": user.first(),
                                                "message": {
                                                    "response_type": "text",
                                                    "text": "🏁 The End\n\nCongratulations! You have reached the end of the tutorial.\n\nYou can select another tutorial to continue learning or go to *Assessment* to test your knowledge.",
                                                }
                                            }

                                    else:
                                        session['data']["tutorial_stage"] = "select_tutorial"
                                        cache.set(phone_number,
                                                  session, 60*60*24)
                                        return {
                                            "is_valid": False,
                                            "data": user.first(),
                                            "message": {
                                                "exclude_back": True,
                                                "response_type": "button",
                                                "text": "*Invalid selection*\n\nPlease select a valid option from the menu.",
                                            }
                                        }
                                except Exception as e:
                                    print("Error in select_tutorial", e)
                                    session['data']["tutorial_stage"] = "select_tutorial"
                                    cache.set(phone_number, session, 60*60*24)
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "response_type": "text",
                                            "text": f"Error in select_tutorial: {e}",
                                        }
                                    }
                            elif session['data'].get("tutorial_stage") == "ongoing_tutorial":
                                is_first_step = False
                                is_last_step = False
                                if message == "tutorial_next":
                                    tutorial = Tutorial.objects.filter(
                                        id=session['data'].get("selected_tutorial")).first()
                                    if tutorial:
                                        steps = tutorial.steps.all().order_by("id")
                                        if steps:
                                            if session["data"]["step_position"] < len(steps):
                                                step = steps[session["data"]
                                                             ["step_position"]]
                                                session["data"]["step_position"] += 1
                                                is_first_step = True if session["data"]["step_position"] == 1 else False
                                                is_last_step = True if session["data"]["step_position"] > steps.count(
                                                )-1 else False
                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                                if step.content_type == "text":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "tutorial",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                        }
                                                    }
                                                elif step.content_type == "image":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "image",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "image":  f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                elif step.content_type == "video":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "video",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "video": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                elif step.content_type == "audio":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "audio",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "audio": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                elif step.content_type == "document":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "document",
                                                            "text": f"{step.instructions}",
                                                            "document": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                else:
                                                    session['data']["tutorial_stage"] = "select_tutorial"
                                                    session['data']["step_position"] = None
                                                    cache.set(
                                                        phone_number, session, 60*60*24)
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "text",
                                                            "text": "Oops! Something went wrong.",
                                                        }
                                                    }
                                            else:
                                                session['data'].pop(
                                                    "tutorial_stage")
                                                session['data'].pop(
                                                    "step_position")
                                                session['data'].pop(
                                                    "selected_tutorial")

                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                                return {
                                                    "is_valid": False,
                                                    "data": user.first(),
                                                    "is_first_step": is_first_step,
                                                    "is_last_step": is_last_step,
                                                    "message": {
                                                        "exclude_back": True,
                                                        "menu": "course_menu",
                                                        "response_type": "button",
                                                        "text": "🏁 The End\n\nCongratulations! You have reached the end of the tutorial.\n\nYou can select another tutorial to continue learning or go to *Assessment* to test your knowledge.",
                                                    }
                                                }
                                        else:
                                            session['data'].pop(
                                                "tutorial_stage")
                                            session['data'].pop(
                                                "step_position")
                                            session['data'].pop(
                                                "selected_tutorial")
                                            cache.set(phone_number,
                                                      session, 60*60*24)
                                            return {
                                                "is_valid": False,
                                                "data": user.first(),
                                                "is_first_step": is_first_step,
                                                "is_last_step": is_last_step,
                                                "message": {
                                                    "menu": "course_menu",
                                                    "response_type": "button",
                                                    "text": "🏁 The End\n\nCongratulations! You have reached the end of the tutorial.\n\nYou can select another tutorial to continue learning or go to *Assessment* to test your knowledge.",
                                                }
                                            }
                                    else:
                                        session['data']["tutorial_stage"] = "select_tutorial"
                                        session['data']["step_position"] = None
                                        cache.set(phone_number,
                                                  session, 60*60*24)
                                        return {
                                            "is_valid": False,
                                            "data": user.first(),
                                            "is_first_step": is_first_step,
                                            "is_last_step": is_last_step,
                                            "message": {
                                                "exclude_back": True,
                                                "menu": "course_menu",
                                                "response_type": "button",
                                                "text": "*Invalid selection*\n\nPlease select a valid option from the menu.",
                                            }
                                        }
                                elif message == "tutorial_prev":
                                    tutorial = Tutorial.objects.filter(
                                        id=session['data'].get("selected_tutorial"), published=True).first()
                                    if tutorial:
                                        steps = tutorial.steps.all().order_by("id")
                                        if steps:
                                            if session["data"]["step_position"] > 1:
                                                step = steps[session["data"]
                                                             ["step_position"]-2]

                                                session["data"]["step_position"] -= 1
                                                is_first_step = True if session["data"]["step_position"] == 1 else False
                                                is_last_step = True if session["data"]["step_position"] > steps.count(
                                                )-1 else False

                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                                if step.content_type == "text":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": False,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "tutorial",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                        }
                                                    }
                                                elif step.content_type == "image":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "image",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "image":  f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                elif step.content_type == "video":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "video",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "video": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                elif step.content_type == "audio":
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "audio",
                                                            "text": f"*{step.title}*\n\n{step.instructions}",
                                                            "audio": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }

                                                elif step.content_type == "document":

                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "requires_controls": True,
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "document",
                                                            "text": f"{step.instructions}",
                                                            "document": f"{HOST}{step.file.url}" if step.file else None,
                                                        }
                                                    }
                                                else:
                                                    session['data']["tutorial_stage"] = "select_tutorial"
                                                    session['data']["step_position"] = None
                                                    cache.set(
                                                        phone_number, session, 60*60*24)
                                                    return {
                                                        "is_valid": False,
                                                        "data": user.first(),
                                                        "is_first_step": is_first_step,
                                                        "is_last_step": is_last_step,
                                                        "message": {
                                                            "response_type": "text",
                                                            "text": "Oops! Something went wrong.",
                                                        }
                                                    }
                                            else:
                                                session['data'].pop(
                                                    "tutorial_stage")
                                                session['data'].pop(
                                                    "step_position")
                                                session['data'].pop(
                                                    "selected_tutorial")
                                                cache.set(
                                                    phone_number, session, 60*60*24)
                                                return {
                                                    "is_valid": False,
                                                    "data": user.first(),
                                                    "is_first_step": is_first_step,
                                                    "is_last_step": is_last_step,
                                                    "message": {
                                                        "exclude_back": True,
                                                        "menu": "course_menu",
                                                        "response_type": "button",
                                                        "text": "🏁 The End\n\\nYou have reached the start of the tutorial. You cannot go back any further.",
                                                    }
                                                }

                        elif message.lower() in ["course_assessment", "assessment", "course assessment"] or session["data"].get("action") == "select_quiz" or session["data"].get("stage") == "course_assessment":
                            print("IN HEREEEEEEssss", session)
                            all_quizzes = Quiz.objects.filter(
                                course__code=session["data"]["selected_course"], is_published=True)
                            if cache.get(f"{phone_number}_quiz_session"):
                                quiz_session = cache.get(
                                    f"{phone_number}_quiz_session")
                                sess = {
                                    "phone_number": phone_number,
                                    "selected_answer": message,
                                    "quiz_id": quiz_session["quiz_id"],
                                }

                            else:
                                sess = {
                                    "phone_number": phone_number,
                                    "selected_answer": message,
                                }

                            if message == "course_assessment" and sess.get("quiz_id") is None:
                                session['data']['stage'] = "course_assessment"
                                session['data']["action"] = "select_quiz"
                                cache.set(phone_number, session, 60*60*24)
                                all_quizzes = Quiz.objects.filter(
                                    course__code=session["data"]["selected_course"], is_published=True)
                                base = [

                                ]
                                if all_quizzes.count() > 0:
                                    if not session["data"].get("quiz_page"):
                                        session["data"]["quiz_page"] = 1

                                    if not session["data"].get("total_pages"):
                                        session["data"]["total_pages"] = math.ceil(
                                            all_quizzes.count()/self.pagination)

                                    if session["data"].get("quiz_page") > config('PAGINATION_COUNT', cast=int):

                                        base.append({
                                            "id": "previous",
                                            "name": "Previous",
                                            "description": "Previous page"
                                        })
                                    if session["data"]["quiz_page"] < session["data"]["total_pages"]:
                                        base.append({
                                            "id": "next",
                                            "name": "Next",
                                            "description": "Next page"
                                        })
                                    menu_items = [
                                        {
                                            "id": f"quiz_{quiz.id}",
                                            "name": f"{quiz.title}",
                                            "description": f"{quiz.description[:45]}...",
                                        } for quiz in all_quizzes[session["data"]["quiz_page"]*self.pagination-self.pagination:session["data"]["quiz_page"]*self.pagination]
                                    ]
                                    if base and menu_items and courses.count() > self.pagination:
                                        menu_items.extend(base)

                                    def generate_menu(quizzes_list): return [
                                        f"{count}. *{quiz.title}*" for count, quiz in enumerate(quizzes_list[:8], 1)]
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "response_type": "interactive",
                                            "text": f"*Quiz Menu (Page {session['data']['page']} of {math.ceil(all_quizzes.count()/self.pagination)}).*\n\n" + " \n\n ".join(generate_menu(all_quizzes[session['data']['quiz_page']*self.pagination-self.pagination:session['data']['quiz_page']*self.pagination])) + "\n\nPlease select a quiz to take.",
                                            "username": f"{user.first().first_name} {user.first().last_name}",
                                            "menu_name": "📝 Quiz",
                                            "menu_items": menu_items
                                        }
                                    }
                                else:
                                    return {
                                        "is_valid": False,
                                        "data": user.first(),
                                        "message": {
                                            "exclude_back": True,
                                            "response_type": "button",
                                            "text": "*Empty*\n\nNo quiz available for this course at the moment.Please try again later.",
                                        }
                                    }
                            elif session['data'].get('stage') == "course_assessment" and session['data'].get("action") == "select_quiz":
                                if message in [f"quiz_{quiz.id}" for quiz in all_quizzes]:
                                    session['data']["action"] = "quiz"
                                    session['data']["quiz"] = message.split("_")[
                                        1]
                                    quiz_session = {
                                        "quiz_id": message.split("_")[1],
                                        "phone_number": phone_number,
                                        "selected_answer": message

                                    }
                                    cache.set(
                                        f"{phone_number}_quiz_session", quiz_session, 60*60*24)
                                    cache.set(phone_number, session, 60*60*24)
                                    service = QuizService(quiz_session)
                                    return service.deliver_quiz()
                            elif message in ['A', 'B', 'C', 'D'] and session['data'].get("action") == "quiz":
                                quiz_session = {
                                    "quiz_id": session['data'].get("quiz"),
                                    "phone_number": phone_number,
                                    "selected_answer": message,

                                }
                                service = QuizService(quiz_session)
                                return service.deliver_quiz()

                            print("WILDCARD : ", message, session['data'])
                            return {
                                "is_valid": False,
                                "data": user.first(),
                                "message": {
                                    "response_type": "button",
                                    "text": "*Invalid selection*\n\nPlease select a valid option from the menu.",
                                }
                            }

                        elif message.lower() in ["conversation", "chat"] or session["data"].get('action') in ["conversation", "send_message"] or (session["data"].get('action') == "conversation" and message == "conversation"):
                            user = User.objects.get(phone_number=phone_number)
                            print("CONVERSATION : ", message, session['data'])
                            if session["data"].get("action") is None:
                                session["data"]["action"] = "conversation"
                                cache.set(user.phone_number,
                                          session, timeout=60*60*24)
                                conversation = Conversation.objects.filter(
                                    course__students=user, course__code=session["data"]["selected_course"]).first()
                                if conversation:
                                    def chat(conversation): return [
                                        f"*From :* {item.sender.first_name} {item.sender.last_name}\n*Date :* {item.date_sent.strftime('%d-%m-%Y %H:%M:%S')}\n*Message :* {item.content}" for item in conversation.messages.all()]
                                    session["data"]["action"] = "conversation"
                                    cache.set(user.phone_number,
                                              session, timeout=60*60*24)
                                    conversation.has_unread = False
                                    conversation.save()
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "conversation",
                                            "text": f"*{conversation.course.name}*\n\n*Chat*\n\n" + "\n\n".join(chat(conversation)),
                                        }
                                    }
                                else:
                                    course = Course.objects.get(
                                        code=session["data"]["selected_course"])
                                    session["data"]["action"] = "send_message"
                                    cache.set(user.phone_number,
                                              session, timeout=60 * 60 * 24)
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "conversation",
                                            "text": f"*{course.name}*\n\n*Chat Empty*.\nSend a message to start a conversation.",
                                        }
                                    }
                            elif session["data"].get("action") == "conversation":
                                if message == "send_message":
                                    session["data"]["action"] = "send_message"
                                    cache.set(user.phone_number,
                                              session, timeout=60 * 60 * 24)
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "text",
                                            "text": "Enter your message...",
                                        }
                                    }
                            elif session["data"].get("action") == "send_message":
                                conversation = Conversation.objects.filter(
                                    course__students=user, course__code=session["data"]["selected_course"]).first()
                                if conversation:
                                    conversation.post_message(user, message)

                                    def chat(conversation): return [
                                        f"*From :* {item.sender.first_name} {item.sender.last_name}\n*Date :* {item.date_sent.strftime('%d-%m-%Y %H:%M:%S')}\n*Message :* {item.content}" for item in conversation.messages.all()]
                                    session["data"]["action"] = "conversation"
                                    cache.set(user.phone_number,
                                              session, timeout=60*60*24)
                                    conversation.has_unread = False
                                    conversation.save()
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "conversation",
                                            "text": f"*{conversation.course.name}*\n\nChat\n\n" + "\n\n".join(chat(conversation)),
                                        }
                                    }
                                else:
                                    course = Course.objects.get(
                                        code=session["data"]["selected_course"])
                                    conversation = Conversation.objects.create(
                                        user=user, course=course)
                                    conversation.post_message(user, message)

                                    def chat(conversation): return [
                                        f"*From :* {item.sender.first_name} {item.sender.last_name}\n*Date :* {item.date_sent.strftime('%d-%m-%Y %H:%M:%S')}\n*Message :* {item.content}" for item in conversation.messages.all()]
                                    session["data"]["action"] = "conversation"
                                    cache.set(user.phone_number,
                                              session, timeout=60*60*24)
                                    conversation.has_unread = False
                                    conversation.save()
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "conversation",
                                            "text": f"*{conversation.course.name}*\n\nChat\n\n" + "\n\n".join(chat(conversation)),
                                        }
                                    }

                        elif message.lower() in ["course_material", "materials", "course materials"]  or session["data"].get('action') in ["course_material"] or (session["data"].get('action') == "course_material" and message == "course_material"):
                            user = User.objects.get(phone_number=phone_number)
                            if session["data"].get("action") is None:
                                session["data"]["action"] = "course_material"
                                cache.set(user.phone_number,
                                          session, timeout=60*60*24)
                                course_materials = CourseMaterial.objects.filter(
                                    course__students=user, course__code=session["data"]["selected_course"])
                                if course_materials:
                                    paginated_response = self.paginated_menu(
                                        user, message, course_materials, session, 'course_materials', prefix='course_material')
                                    def generate_menu(course_materials_list): return [
                                        f"*{count}.* {item.title}" for count, item in enumerate(course_materials_list[:8], 1)]
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "response_type": "paginated_interactive",
                                            "menu_name": "*Course Materials*",
                                            "text": "*Course Materials*\n\n" + " \n\n ".join(generate_menu(course_materials[session['data']['page']*self.pagination-self.pagination:session['data']['page']*self.pagination])) + "\n\nPlease select a course material to view",
                                            "menu_items": paginated_response,
                                        }
                                    }
                                else:
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "exclude_back": True,
                                            "menu": "course_menu",
                                            "response_type": "button",
                                            "text": "*Empty*\n\nNo course material available for this course at the moment.Please try again later.",
                                        }
                                    }
                            elif session["data"].get("action") == "course_material":
                                # if message starts with course_material_ then it is a course material
                                if message.startswith("course_material_"):
                                    course_material_id = message.split("_")[2]
                                    course_material = CourseMaterial.objects.get(
                                        id=course_material_id, )
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "requires_controls": True,
                                        "is_first_step": False,
                                        "is_last_step": False,
                                        "type": "document",
                                        "message": {
                                            "response_type": "document",
                                            "text": f"*{course_material.title}*\n\n{course_material.description}",
                                            "document": f"{HOST}{course_material.file.url}",
                                        }
                                    }
                                else:
                                    return {
                                        "is_valid": False,
                                        "data": user,
                                        "message": {
                                            "exclude_back": True,
                                            "response_type": "button",
                                            "text": "*Invalid selection*\n\nPlease select a valid option from the menu.",
                                        }
                                    }

                    return {
                        "is_valid": False,
                        "data": user.first(),
                        "message": {
                            "response_type": "interactive",
                            "text": f"*Course Menu({user.first().course_package(session['data']['selected_course']).name.title() if user.first().course_package(session['data']['selected_course']) else 'No Package Detected'})*\n\n 📜 Outline\n\n 📹 Tutorials\n\n 📚 Material\n\n 📊 Assessment\n\n 👨‍🏫📞 Schedule Call\n\n 🗣 Conversation\n\n 🔙 Back\n\nSelect an option to continue.",
                            "username": f"{user.first().first_name} {user.first().last_name}",
                            "menu_name": f"📚 {course.name}",
                            "menu_items": [
                                {
                                    "id": "course_outline",
                                    "name": "📜 Outline",
                                    "description": "Course Outline"
                                },
                                {
                                    "id": "tutorials",
                                    "name": "📹 Tutorials",
                                    "description": "Course Tutorial"
                                },
                                {
                                    "id": "course_material",
                                    "name": "📚 Material",
                                    "description": "Course Material"
                                },
                                {
                                    "id": "course_assessment",
                                    "name": "📊 Assessment",
                                    "description": "Course Assessment"
                                },
                                {
                                    "id": "request_call",
                                    "name": "👨‍🏫📞 Schedule Call",
                                    "description": "Request a call from a tutor"
                                },
                                {
                                    "id": "conversation",
                                    "name": "🗣 Conversation",
                                    "description": "Conversation"

                                },
                                {
                                    "id": "back_to_courses",
                                    "name": "🔙 Back",
                                    "description": "Back to courses"
                                }
                            ]
                        }
                    }

    def profile(self, phone_number, message, session, payload=dict):
        """Profile menu"""
        user = User.objects.filter(phone_number=phone_number)

        if message == "update":
            session = {
                "state": "update_profile",
                "data": {
                    "first_name": user.first().first_name,
                    "last_name": user.first().last_name,
                    "email": user.first().email,
                    "phone_number": user.first().phone_number,
                    "done": False
                }
            }
            cache.set(phone_number, session, 60*60*24)

        if user.first().sex == "MALE":
            imo = '🤵🏽‍♂'
        elif user.first().sex == "FEMALE":
            imo = '🤵🏽‍♀'
        else:
            imo = '🤵🏽'

        return {
            "is_valid": True,
            "data": user.first(),
            "message": {
                "response_type": "interactive",
                "text": f"*Your Profile*\n\n*Email:* {user.first().email}\n*Phone Number:* {user.first().phone_number}\n*Name: _{user.first().first_name} {user.first().last_name}_*\n*Sex: _{user.first().sex.title()}_*",
                "username": f"{user.first().first_name} {user.first().last_name}",
                "menu_name": f"{imo} Profile",
                "menu_items": [
                    {"id": "deactivate", "name": "Deactivate Profile",
                        "description": "Suspend your profile"},
                    {"id": "menu", "name": "Main Menu", "description": "Menu"},
                ]
            }
        }

    def help(self, phone_number, message, session, payload=dict):
        """Help menu"""
        user = User.objects.filter(phone_number=phone_number)
        print(message, session)
        if message == "guide":
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "button",
                    "text": "Ngena is a chatbot that helps you to manage your courses and profile.\n\n1. Follow the instructions to register.\n2. Type *menu* to get started.\n3. Enroll in a course.\n4. Manage your profile.\n5. Enjoy Learning!\n\nAt any point, you can type *menu* to get back to your main menu.\n\n",
                }
            }
        elif message == "contact":
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "button",
                    "text": "If you have any questions or feedback, please contact the developer at *+263771516726*\n\n Thank you for using Ngena!",
                }
            }
        return {
            "is_valid": True,
            "data": user.first(),
            "message": {
                "response_type": "interactive",
                "text": "*Help Menu*\n\n 📚 User guide\n\n 👨‍💻 Contact\n\n 🏠 Main Menu",
                "username": f"{user.first().first_name} {user.first().last_name}",
                "menu_name": "🆘 Help",
                "menu_items": [
                    {"id": "guide", "name": "📚 User guide",
                        "description": "User guide"},
                    {"id": "contact", "name": "👨‍💻 Contact",
                        "description": "Contact the developer"},
                    {"id": "menu", "name": "Main Menu",
                        "description": "Back To Menu"},
                ]
            }
        }

    def paginated_menu(self, user, message, section_objects, session, key, prefix=None):
        """Paginated menu"""
        print("PAGINATED INSTRUCTIONS MENU", section_objects)
        total_records = section_objects.count()
        if not session['data'].get(key):
            session['data'][key] = {
                "count": 0
            }
            cache.set(user.phone_number, session, 60*60*24)
        else:
            if message == 'next_page':
                session['data'][key]['count'] += 1
                session.save()
            elif message == 'prev_page':
                session['data'][key]['count'] -= 1
                cache.set(user.phone_number, session, 60*60*24)

        if total_records <= 10:
            sections = [
                {
                    "id": f"{prefix}_{item.id}" if prefix else item.id,
                    "title": item.title if item.title else '',
                    "description": f"{item.description[:69] if item.description else ''}..."
                } for item in section_objects
            ]

        else:

            paginated_data = section_objects[session['data'][key]
                                             ['count'] * 8:session['data'][key]['count'] * 8 + 8]
            print("PAGINATED DATA", paginated_data)
            sections = [
                {
                    "id": f"{prefix}_{item.id}" if prefix else item.id,
                    "title": item.title,
                    "description": f"{item.description[:69] if item.description else ''}..."
                } for item in paginated_data
            ]

            if session['data'][key]['count'] > 0:
                sections.append({
                    "id": "prev_page",
                    "title": "Previous Page",
                })

            if session['data'][key]['count'] < total_records // 8:
                sections.append({
                    "id": "next_page",
                    "title": "Next Page",
                })
        return sections

    def about(self, phone_number, message, session, payload=dict):
        """About menu"""
        user = User.objects.filter(phone_number=phone_number)
        print(message, session)
        return {
            "is_valid": True,
            "data": user.first(),
            "message": {
                "exclude_back": True,
                "response_type": "button",
                "text": "*About Us*\n\nNgena is a chatbot that helps \nyou to manage your courses \nand profile brought to you by \n*Empart*.\n\nFor more information, visit * https://www.ngena.com* nor contact us on *https://wa.me/263771516726*",
            }
        }

    def payments(self, phone_number, message, session, payload=dict):
        """Payment menu"""
        user = User.objects.filter(phone_number=phone_number)
        # pylint: disable=maybe-no-member
        payments = Payment.objects.filter(
            user=user.first()).order_by("-created_at")[:7]
        if not session["data"]:
            session["data"] = {}

        if message in [str(payment.id) for payment in payments]:
            payment = Payment.objects.get(id=message)
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "button",
                    "text": f"*📜Payment Details*\n\n*Course: _{payment.course.name}_*\n*Amount:* ${payment.amount}\n*Date:* _{payment.created_at.strftime('%d %b %Y')}_\n*Status:* _{payment.payment_status} {'✅' if payment.payment_status == 'Paid' else '🚫'}_\n\n",
                }
            }
        if payments:
            statuses = {
                "paid": "✅",
                "pending": "⏳",
                "failed": "🚫",
                "created": "📝",
                "awaitingdelivery": "⏳",
                "cancelled": "🚫",
                "unknown": "❓"

            }
            def generate_menu(payment): return [
                f"*{count}.* {payment.course.name} {statuses.get(payment.payment_status.strip().lower()) if statuses.get(payment.payment_status.strip().lower()) else statuses.get('unknown')}" for count, payment in enumerate(payments[:8], 1)]
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "interactive",
                    "text": "*Recent Payments* \n\n"+" \n\n ".join(generate_menu(payments)),
                    "username": f"{user.first().first_name} {user.first().last_name}",
                    "menu_name": "💰 Payments",
                    "menu_items": [
                        {"id": f"{payment.id}", "name": f"{payment.course.name}", "description": f"{payment.created_at.strftime('%d %b %Y %H:%M')}"} for payment in payments
                    ]

                }
            }

        else:
            return {
                "is_valid": True,
                "data": user.first(),
                "message": {
                    "response_type": "button",
                    "text": "*💳 No Payments Available*\n\nYou have not made any payments yet.",
                }
            }

    def assignments(self, phone_number, message, session, payload=dict):
        """Assignment menu"""
        user = User.objects.get(phone_number=phone_number)

        # pylint: disable=maybe-no-member
        pending_work = PendingWork.objects.filter(
            course__students__in=[user]
        ).exclude(
            submitted_assignments__submitted_by=user
        ).order_by("-created_at")

        session = cache.get(f"{phone_number}_session", {"data": {}})

        if message in [str(work.id) for work in pending_work]:
            session["data"]["assignment_id"] = message
            cache.set(f"{phone_number}_session", session, 60*60*24)
            work = PendingWork.objects.get(id=message)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "download",
                    "text": f"*{work.title} Details*\n\n*Course: _{work.course.name}_*\n*Deadline:* _{work.deadline.strftime('%d %b %Y %H:%M') if  work.deadline else 'No deadline'}_\n*Description:* _{work.description}_\n\n",
                }
            }

        elif message == "download":
            work = PendingWork.objects.get(id=session["data"]["assignment_id"])
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "document",
                    "text": f"*📜 {work.title} Details*\n\n*Course: _{work.course.name}_*\n*Deadline:* _{work.deadline.strftime('%d %b %Y %H:%M') if  work.deadline else 'No deadline'}_\n*Description:* _{work.description}_\n\n",
                    "document": settings.NGROK + work.file.url,
                    "filename": work.file.name
                }
            }

        elif message == "upload":
            session["data"]["action"] = 'upload'
            cache.set(f"{phone_number}_session", session, 60*60*24)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "text",
                    "text": "*📎 Upload Document* \n\nPlease upload and send your assignment as a document here."
                }
            }

        elif session["data"].get("action") == "upload":
            print("uploading >>>>>>>>>>>>>>>>>>>>>> ", payload)
            url_regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                # domain...
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if url_regex.match(message):
                file = requests.get(url=message, headers={
                                    'Authorization': f"Bearer {config('CLOUD_API_TOKEN')}"})
                print("FILE: ", payload)
                bytesio_o = BytesIO(file.content)
                print("SIZE: ", f'{sys.getsizeof(bytesio_o)} kb')
                print("TYPE: ", file.headers.get("content-type"))
                print("NAME: ", payload.get("filename"))
                filetype = file.headers.get("content-type")
                print("FILENAME: ", filetype)

                obj = InMemoryUploadedFile(
                    file=bytesio_o,
                    field_name='file',
                    name=payload['messages'][0]['document']['filename'],
                    content_type=file.headers.get("content-type"),
                    size=sys.getsizeof(bytesio_o),
                    charset="Unicode - UTF8"
                )
                print("OBJ: ", obj)

                # pylint: disable=no-member
                work = PendingWork.objects.get(
                    id=session["data"]["assignment_id"])
                assignment = Assignment.objects.create(
                    title=f"{work.title} - {user.first_name} {user.last_name}",
                    file=obj,
                    status="Completed",
                    referenced_work=work,
                    submitted_by=user
                )
                print(assignment, "<<============>>", obj)
                work.submitted_assignments.add(assignment)
                assignment.file = obj
                assignment.save()
                work.save()
                session["data"]["action"] = None
                cache.set(f"{phone_number}_session", session, 60*60*24)
                return {
                    "is_valid": True,
                    "data": user,
                    "message": {
                        "exclude_back": True,
                        "response_type": "button",
                        "text": "✅ *Upload Successful*\n\nYour assignment has been submitted successfully.",
                    }
                }
            else:
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "text",
                        "text": "*📎 Upload Document* \n\nPlease upload and send your assignment as a document here."
                    }
                }

        elif message == "my_assignments":
            cache.set(f"{phone_number}_session", session, 60*60*24)
            # filter pending work if user is enrolled in the course and user not in the list of submitted assignments

            def generate_menu(pending_work): return [
                f"*{count}.* {pending_work.title}" for count, pending_work in enumerate(pending_work[:8], 1)]
            if pending_work:
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "interactive",
                        "text": "*Pending Assignments*\n\n"+" \n\n".join(generate_menu(pending_work)),
                        "username": f"{user.first_name} {user.last_name}",
                        "menu_name": "📝 Pending",
                        "menu_items": [
                            {"id": f"{work.id}", "name": f"{work.course.name}", "description": f"Due {work.deadline.strftime('%d %b %Y %H:%M') if  work.deadline else 'No deadline'}"} for work in pending_work
                        ]
                    }
                }
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "button",
                    "text": "*⚠️Not Found*\n\nYou have not been assigned any assignments yet. Please check back later.",
                }
            }

        elif message == "get_help":
            session["data"]["action"] = message
            cache.set(f"{phone_number}_session", session, 60*60*24)
            pending = Assignment.objects.filter(
                submitted_by=user, status="Pending", assignment_type="Outsourced")
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "interactive",
                    "text": f"*Help Menu*\n\n 📤 Upload Assignment\n\n 📂 View Pending ({pending.count()})\n\n 🔙 Back",
                    "username": f"{user.first_name} {user.last_name}",
                    "menu_name": "🆘 Get Help",
                    "menu_items": [
                        {"id": "outsource", "name": "📤 Upload Assignment",
                            "description": "Upload your assignment"},
                        {"id": "pending",
                            "name": f"📂 View Pending ({pending.count()})", "description": "View pending assignments"},
                        {"id": "back", "name": "🔙 Back",
                            "description": "Back to assignments menu"},
                    ]
                }
            }

        elif session["data"].get("action") == "get_help" and message == "outsource":
            session["data"]["action"] = "assignment_type"
            cache.set(f"{phone_number}_session", session, timeout=60*60*24)

            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "interactive",
                    "text": "*Assignment Type*\n\n 📐 Math Assignment\n\n 🔬 Science Assignment\n\n 📚 Language Assignment\n\n 📖 Social Studies\n\n 💻 ICT Assignment\n\n 📚 Other\n\nSelect type.",
                    "menu_name": "View Types",
                    "menu_items": [
                        {"id": "math", "name": "📐 Math Assignment",
                            "description": "Math"},
                        {"id": "science", "name": "🔬 Science Assignment",
                            "description": "Science"},
                        {"id": "language", "name": "📚 Language Assignment",
                            "description": "Language"},
                        {"id": "social", "name": "📖 Social Studies",
                            "description": "Social"},
                        {"id": "ict", "name": "💻 ICT Assignment",
                         "description": "ICT"},
                        {"id": "other", "name": "📚 Other", "description": "Other"},
                    ]

                }
            }
        elif session["data"].get("action") == "assignment_type" and message in ["math", "science", "language", "social", "ict", "other"]:
            session["data"]["action"] = "assignment_name"
            session["data"]["field"] = message
            cache.set(f"{phone_number}_session", session, 60*60*24)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "text",
                    "text": "*📜 Assignment Identifier*\n\nPlease enter a reference name of the assignment you are submitting."
                }
            }

        elif session["data"].get("action") == "assignment_name":
            session["data"]["action"] = 'assignment_description'
            session["data"]["assignment_name"] = message
            cache.set(f"{phone_number}_session", session, 60*60*24)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "text",
                    "text": "*📜 Assignment Description*\n\nPlease enter a description or instructions for the assignment."
                }
            }

        elif session["data"].get("action") == "assignment_description":
            session["data"]["action"] = 'receive_assignment'
            session["data"]["assignment_description"] = message
            cache.set(f"{phone_number}_session", session, 60*60*24)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "text",
                    "text": "*📎 Upload Document* \n\nPlease upload and send your assignment document and we will get back to you."
                }
            }

        elif session["data"].get("action") == "receive_assignment":
            print("RECEIVING ASSIGNMENT", message)
            session["data"]["field"] = message
            # try:
            url_regex = re.compile(
                r'^(?:http|ftp)s?://'  # http:// or https://
                # domain...
                r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
                r'localhost|'  # localhost...
                r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
                r'(?::\d+)?'  # optional port
                r'(?:/?|[/?]\S+)$', re.IGNORECASE)
            if url_regex.match(message):
                file = requests.get(url=message, headers={
                    'Authorization': f"Bearer {config('CLOUD_API_TOKEN')}"})
                bytesio_o = BytesIO(file.content)

                obj = InMemoryUploadedFile(
                    file=bytesio_o,
                    field_name='file',
                    name=payload['messages'][0]['document']['filename'],
                    content_type=file.headers.get("content-type"),
                    size=sys.getsizeof(bytesio_o),
                    charset="Unicode - UTF8"
                )
                assignment = Assignment.objects.create(
                    title=session["data"]["assignment_name"],
                    field_of_study=session["data"]["field"],
                    description=session["data"]["assignment_description"],
                    assignment_type="Outsourced",
                    status="Pending",
                    submitted_by=user,
                    file=obj

                )
                payment = Payment.objects.create(
                    user=user,
                    amount=0,
                    course=Course.objects.get(code="COUT"),
                    payment_type="Outsource",
                    payment_status="Awaiting Payment"
                )
                assignment.payment = payment
                assignment.save()

                session["data"]["action"] = "pending_payment"
                cache.set(f"{phone_number}_session", session, 60*60*24)
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "exclude_download": True,
                        "response_type": "pay_download",
                        "id": payment.id,
                        "text": f"*📝 Assignment Received* \n\nWe have received your assignment referenced {assignment.title.title()}.\n\nPlease note that you will be charged a fee for this service. Complete the payment process so we can start working on it.\n\nThank you for using our service.",
                    }
                }
            else:
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "text",
                        "text": "*📎 Upload Document* \n\nPlease upload and send your assignment as a document here.*"
                    }
                }

        elif session["data"].get("action") == "get_help" and message == "pending":
            session["data"]["action"] = "view_pending"
            cache.set(f"{phone_number}_session", session, timeout=60*60*24)
            pending_work = Assignment.objects.filter(
                assignment_type="Outsourced").order_by("-created_at")
            print("===>>>>>>>>", pending_work)
            if pending_work:
                session["data"]["action"] = "view_pending"
                cache.set(f"{phone_number}_session", session, timeout=60*60*24)
                section_objects = pending_work.exclude(status="Completed")
                key = "outsourced"
                menu_items = self.paginated_menu(
                    user, message, section_objects, session, key, prefix="outsourced")

                def generate_menu(pending_work): return [
                    f"{count}. {pending_work.title}" for count, pending_work in enumerate(pending_work[:8], 1)]
                return {
                    "is_valid": False,
                    "data": user,

                    "message": {
                        "response_type": "paginated_interactive",
                        "text": "*Pending Assignments* \n\n"+"\n\n".join(generate_menu(pending_work)),
                        "username": f"{user.first_name} {user.last_name}",
                        "menu_name": "📝 Pending",
                        "menu_items": menu_items

                    }
                }
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "button",
                    "text": "*⚠️ Not Found* \n\nYou have not uploaded any assignments yet. Please upload an assignment to get started.",
                }
            }
        elif session["data"].get("action") == "view_pending" and message.startswith("outsourced_"):
            session["data"]["action"] = "download_outsourced"
            cache.set(f"{phone_number}_session", session, timeout=60*60*24)

            assignment = Assignment.objects.get(id=message.split("_")[1])
            if assignment.status == "Pending" and assignment.payment:
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "text",
                        "text": f"*⏳ Pending*\n\n{assignment.title.title()} is still pending. Please complete the payment process to get started."
                    }
                }

            elif assignment.status == "Completed":
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "download_outsourced",
                        "text": f"*✅ Completed*\n\n{assignment.title.title()} has been completed. Please download the file below.",
                        "download_solution": assignment.id
                    }
                }
            elif assignment.status == "In Progress":
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "download_outsourced",
                        "text": f"*⏳ Pending*\n\n{assignment.title.title()} is currently being worked on. Please wait for a response from our team."
                    }
                }
            elif assignment.status == "Revision":
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "download_outsourced",
                        "text": f"*⏳ Revision*\n\n {assignment.title.title()} is currently being revised. Please wait for a response from our team."
                    }
                }
            else:
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "download_outsourced",
                        "text": f"*⏳ Pending*\n\n{assignment.title.title()} is currently being worked on. Please wait for a response from our team."
                    }
                }

        elif session["data"].get("action") == "download_outsourced" and message.startswith("download_outsourced_"):
            assignment = Assignment.objects.filter(
                id=message.split("_")[1]).first()
            if assignment.status == "Completed":
                return {
                    "is_valid": False,
                    "data": user,
                    "message": {
                        "response_type": "document",
                        "text": f"Assignment {assignment.title.title()} has been completed. Please click on the file to download your solution. \n\nThank you for using our service.",
                        "document": assignment.solution.url
                    }
                }

        elif session["data"].get("action") == "pending_payment" and message.startswith("payment_"):
            if message.split("_")[1] in [str(payment.id) for payment in Payment.objects.filter(user=user, payment_status="Awaiting Payment")]:
                session["data"]["action"] = "pending_payment"
                cache.set(f"{phone_number}_payment",
                          message.split("_")[1], timeout=60*60*24)
                cache.set(f"{phone_number}", session, timeout=60*60*24)
                print("Saving session : ", session['data'])
                def generate_menu(packages): return [
                    f"{count}. {package.name.title()} Package(${package.price})" for count, package in enumerate(packages, 1)]
                return {
                    "is_valid": False,
                    "data": user,
                    "id": "paypal",
                    "message": {
                        "response_type": "interactive",
                        "text": "*Packages Menu*\n\n"+" \n\n".join(generate_menu(Package.objects.filter(service_type="assignment_outsourcing"))),
                        "username": f"{user.first_name} {user.last_name}",
                        "menu_name": "📦 Packages",
                        "include_description": True,
                        "menu_items": [
                                {
                                    "id": f"package_{package.id}",
                                    "name": f"{package.name.title()} Package(${package.price})",
                                    "description": package.description
                                } for package in Package.objects.filter(service_type="assignment_outsourcing")
                        ]
                    }
                }

        elif session["data"].get("action") == "pending_payment" and message.startswith("package_"):
            print("Saving session : ", session['data'])
            session["data"]["action"] = "assignment_payment"
            session["data"]["selected_package"] = message.split("_")[1]
            payment = Payment.objects.get(
                id=cache.get(f"{phone_number}_payment"))
            package = Package.objects.get(id=message.split("_")[1])
            payment.amount = package.price
            payment.package = package
            payment.save()
            session["data"]["payment_id"] = payment.id
            cache.set(f"{phone_number}", session, timeout=60*60*24*7)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "interactive",
                    "text": "*Complete Payment*\n\n 🇺🇸 PayPal\n\n 🇿🇼 PayNow\n\nPay For Assignment with",
                    "username": f"{user.first_name} {user.last_name}",
                    "menu_name": "Payment Options",
                    "menu_items": [
                        {
                            "id": "handle_payment",
                            "name": "🇺🇸 PayPal",
                            "description": "Complete purchase with PayPal",
                        },
                        {
                            "id": "disabled",
                            "name": "🇿🇼 PayNow (disabled)",
                            "description": "Complete purchase with PayNow",
                        },
                    ]
                }
            }
        if message == "disabled":
            print("PAYNOW")
            session["data"]["action"] = "pending_payment"
            cache.set(phone_number, session, 60*60*24)
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "response_type": "button",
                    "exclude_back": True,
                    "text": "*🇿🇼 PayNow*\n\nThis feature is currently disabled. Please select another payment option.",
                }
            }

        return {
            "is_valid": False,
            "data": user,
            "message": {
                "response_type": "interactive",
                "text": "*Assignments*\n\n 📚 Course Assignments\n\n 📝 Outsource Assignment\n\n 🏠 Main Menu\n\nSelect an option below",
                "username": f"{user.first_name} {user.last_name}",
                "menu_name": "📝 Assignment Menu",
                "menu_items": [
                    {"id": "my_assignments", "name": "📚 Course Assignments",
                        "description": "View your assignments"},
                    {"id": "get_help", "name": "📝 Outsource Assignment",
                        "description": "Get help with your assignments"},
                    {"id": "menu", "name": "🏠 Main Menu",
                        "description": "Back to main menu"},
                ]
            }
        }

    def handle_payment(self, phone_number, message, session, payload=dict):
        """Handle payment related actions"""
        paypal_payload = {
            "currency": "USD",
            "brandName": "Ngena"
        }

        user = User.objects.get(phone_number=phone_number)
        print("PAYMENT PAYLOAD", session, message)
        if session["data"].get("action") == "select_package" and message == "handle_payment":
            # pylint: disable=no-member
            package = Package.objects.get(
                id=session["data"].get("selected_package"))
            course = Course.objects.get(
                code=session["data"].get("selected_course")
            )
            paypal_payload['name'] = f"{course.name.capitalize()} {package.name}"
            paypal_payload['description'] = f"{course.description} {package.get_permissions()}"
            paypal_payload['amount'] = float(package.price)

            payment = Payment.objects.create(
                course=course,
                user=user,
                amount=package.price,
                package=package
            )

            paypal_payload["returnUrl"] = f"{settings.PAYPAL_RETURN_URL}"
            paypal_payload["cancelUrl"] = f"{settings.PAYPAL_CANCEL_URL}"

            payment_client = PAYPALCLIENTAPI(paypal_payload)
            payment_response = payment_client.online_payment()
            print("PAYMENT RESPONSE", payment_response)
            # returns status, payment_url, payment_id
            if payment_response.get("successful"):
                payment.upstream_reference = payment_response.get("paypal_id")
                payment.payment_status = payment_response.get("status").title(
                ) if payment_response.get("status") else "Failed"
                payment.upstream_response = payment_response.get("response")
                payment.save()
                message = f"*📜 Payment Order Created*\n\nPlease follow the link below to complete your payment\n\n{payment_response.get('url')}"
            else:
                payment.upstream_response = payment_response.get("response")
                payment.save()
                message = "*Payment Order Failed*\n\nPlease try again later"
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "exclude_back": True,
                    "response_type": "button",
                    "text": message,
                }
            }
        elif session["data"].get("action") == "assignment_payment" and message == "handle_payment":
            # pylint: disable=no-member
            payment_id = session["data"].get("payment_id")
            package = Package.objects.get(
                id=session["data"].get("selected_package"))
            payment = Payment.objects.get(id=payment_id)
            payment.package = package
            assignment = Assignment.objects.get(payment=payment)
            paypal_payload['name'] = f"Assignment {assignment.id}"
            paypal_payload['description'] = f"Assignment {assignment.id}"
            paypal_payload['amount'] = float(payment.amount)

            paypal_payload["returnUrl"] = f"{settings.PAYPAL_RETURN_URL_ASSIGNMENT}"
            paypal_payload["cancelUrl"] = f"{settings.PAYPAL_CANCEL_URL}"

            payment_client = PAYPALCLIENTAPI(paypal_payload)
            payment_response = payment_client.online_payment()
            print("PAYMENT RESPONSE", payment_response)
            # returns status, payment_url, payment_id
            if payment_response.get("successful"):
                payment.upstream_reference = payment_response.get("paypal_id")
                payment.payment_status = payment_response.get("status").title(
                ) if payment_response.get("status") else "Failed"
                payment.upstream_response = payment_response.get("response")
                payment.save()
                message = f"*📜 Payment Order Created*\n\nPlease follow the link below to complete your payment\n\n{payment_response.get('url')}"
            else:
                payment.upstream_response = payment_response.get("response")
                payment.save()
                message = "*Payment Order Failed*\n\nPlease try again later"
            return {
                "is_valid": False,
                "data": user,
                "message": {
                    "exclude_back": True,
                    "response_type": "button",
                    "text": message,
                }
            }
        return {
            "is_valid": False,
            "data": user,
            "message": {
                "exclude_back": True,
                "response_type": "button",
                "text": "*Payment Failed*\n\nPlease try again later",
            }
        }

    def join_class(self, phone_number, message, session, payload=dict):
        """Join a class"""
        user = User.objects.get(phone_number=phone_number)
        return {
            "is_valid": True,
            "data": user,
            "message": {
                "exclude_back": True,
                "response_type": "text",
                "text": f"*🙏 Thank you {user.first_name}*\n\nPlease wait while we process your payment, you will be notified once we receive confirmation for your payment. _Confirmation usually takes about 30 seconds_\n\nThank you",
            }
        }

    def cancel_payment(self, phone_number, message, session, payload=dict):
        """Cancel payment"""
        user = User.objects.get(phone_number=phone_number)
        return {
            "is_valid": True,
            "data": user,
            "message": {
                "exclude_back": True,
                "response_type": "button",
                "text": f"Hi {user.first_name},\n\nYour payment has been cancelled.\n\n",
            }
        }
