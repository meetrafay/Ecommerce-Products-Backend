from rest_framework_simplejwt.tokens import RefreshToken

def create_token(user):
    """
    Create or retrieve an authentication token for the user.
    """
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    return {
        'access_token': access_token,
        'refresh_token': refresh_token
        }