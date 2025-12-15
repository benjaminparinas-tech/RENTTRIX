from django.shortcuts import redirect
from django.urls import resolve, Resolver404


class ForcePasswordChangeMiddleware:
    """
    Redirect authenticated tenants who still need to change their password
    to the password change page, unless they are already on an allowed path.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_staff:
            profile = getattr(user, "security_profile", None)
            if profile and profile.force_password_change:
                try:
                    match = resolve(request.path_info)
                    allowed = {
                        "force_password_change",
                        "account_logout",
                        "account_reset_password",
                        "account_reset_password_done",
                        "account_reset_password_from_key",
                        "account_reset_password_from_key_done",
                    }
                    if match.url_name not in allowed:
                        return redirect("force_password_change")
                except Resolver404:
                    # If resolver fails, continue; auth check will apply on next requests.
                    pass

        return self.get_response(request)


