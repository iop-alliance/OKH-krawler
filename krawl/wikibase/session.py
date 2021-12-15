from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class WikibaseSession():

    def __init__(self, client_id, client_secret, token_url):
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url

    def _login(self,):
        # displayed as "Client application key"
        client_id = r"7e6cac4be7fb86248645f1e18d111be8"

        # displayed as "Client application secret"
        client_secret = r"cee281805907c2e0e9ec4400c0730eb663500254"

        # TODO: make sure only this part is provided
        token_url = "https://losh.ose-germany.de/rest.php/oauth2/access_token"

        # # authorize client
        # oauth = OAuth2Session(client_id)
        # authorization_url, state = oauth.authorization_url(auth_url)

        # # fetch an access token

        # # State is used to prevent CSRF, keep this for later.
        # session['oauth_state'] = state

        # using client_credentials grant to get access tokens
        client = BackendApplicationClient(client_id=self._client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(token_url=self._token_url,
                                  client_id=self._client_id,
                                  client_secret=self._client_secret)

    def _request(self,):
        pass

    def post(self,):
        pass

    def get(self,):
        pass

        # retry on transient errors
        # retry on token expiration errors


# api -> session -> request something
#        handle transient errors and auth
#        session might have other auth methods
#
# create session
# add auth to session
# auth must also be able to handle requests errors: LoginRequired, TokenExpiredError, InvalidTokenError, MissingTokenError
#   ServerError
#   TemporarilyUnavailableError
#
# custom auth error? - wrap OAuth2Error ?
#
# session Error -> temporary retry
#               -> auth error (what type is that) -> delegate to auth
#               -> delegation of other errors?
#
# SessionErrorHandler() interface
#   handle_error(request, exception)
#
# Session()
#   post()
#   get()
#   handle_error(request, exception)
#
# SessionAuth Interface - OAuth2 as an implementation
#   auth()
#   handle_error(request, exception)
#     if some kind of token error -> auth again
#
