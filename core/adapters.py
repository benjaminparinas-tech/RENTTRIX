from allauth.account.adapter import DefaultAccountAdapter


class RentrixAccountAdapter(DefaultAccountAdapter):
    """
    Disable public signups; tenants are created by landlords from the dashboard.
    """

    def is_open_for_signup(self, request):
        return False


