import json
import re

import requests
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session


class API:

    def __init__(
        self,
        url,
        reconcile_prop_id,
        client_id,
        client_secret,
        token_url,
    ):
        self.reconciler_url = f"{url}/rest.php/wikibase-reconcile-edit/v0/edit"
        self.api_url = f"{url}/api.php"

        self.reconcile_prop_id = reconcile_prop_id

        self.session = requests.Session()
        self.session.mount(
            "https://",
            requests.adapters.HTTPAdapter(
                pool_maxsize=4,
                max_retries=3,
                pool_block=True,
            ),
        )
        self._login_oauth2(client_id, client_secret, token_url)
        self._create_csrf_token()

    def _login_oauth2(self, client_id: str, client_secret: str, token_url: str) -> None:
        """Login using OAuth v2 protocol and add auth information to the session
        for future requests.

        This actually requires a refresh of access tokens every 3600 seconds, so
        a proper request handler needs to be implemented to handle the token
        refresh.

        Args:
            client_id (str): OAuth v2 ID of the client. In WB referred to as
                client key.
            client_secret (str): OAuth v2 secret of the client.
            token_url (str): REST endpoint for requesting new access tokens.
                See: https://www.mediawiki.org/wiki/Extension:OAuth#OAuth_2.0_REST_endpoints
        """
        # using client_credentials grant to get access tokens
        client = BackendApplicationClient(client_id=client_id)
        oauth = OAuth2Session(client=client)
        token = oauth.fetch_token(token_url=token_url, client_id=client_id, client_secret=client_secret)

        # add access token to every request
        self.session.headers.update({"Authorization": f"Bearer {token['access_token']}"})

    def _create_csrf_token(self):
        # Step 3: GET request to fetch CSRF token
        PARAMS_2 = {"action": "query", "meta": "tokens", "format": "json"}

        R = self.session.get(url=self.api_url, params=PARAMS_2)
        DATA = R.json()

        CSRF_TOKEN = DATA["query"]["tokens"]["csrftoken"]
        self.CSRF_TOKEN = CSRF_TOKEN

    def _login_username_password(self, username, password):
        # https://www.mediawiki.org/wiki/API:Login#Python

        # Step 1: GET request to fetch login token
        PARAMS_0 = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }

        R = self.session.get(url=self.api_url, params=PARAMS_0)
        DATA = R.json()

        LOGIN_TOKEN = DATA["query"]["tokens"]["logintoken"]

        # Step 2: POST request to log in. Use of main account for login is not
        # supported. Obtain credentials via Special:BotPasswords
        # (https://www.mediawiki.org/wiki/Special:BotPasswords) for lgname & lgpassword
        PARAMS_1 = {
            "action": "login",
            "lgname": username,
            "lgpassword": password,
            "lgtoken": LOGIN_TOKEN,
            "format": "json",
        }

        R = self.session.post(self.api_url, data=PARAMS_1)

        # Step 3: GET request to fetch CSRF token
        PARAMS_2 = {"action": "query", "meta": "tokens", "format": "json"}

        R = self.session.get(url=self.api_url, params=PARAMS_2)
        DATA = R.json()

        CSRF_TOKEN = DATA["query"]["tokens"]["csrftoken"]
        print("Got CSRF_TOKEN: ", CSRF_TOKEN)
        self.CSRF_TOKEN = CSRF_TOKEN

    def setlabel(self, entityid, entity):
        value = entity["label"]
        data = {
            "action": "wbsetlabel",
            "id": entityid,
            "format": "json",
            "language": "en",
            "value": value,
            "token": self.CSRF_TOKEN,
        }

        R = self.session.post(self.api_url, data=data)
        if R.ok and not R.json().get("error"):
            print(f"set label of {entityid} to {value}")
            return True
        else:
            raise Exception(f"Couldnt set label of {entityid} to {value}")

    @staticmethod
    def getprop(prop, statements):
        for each in statements:
            if each["property"] == prop:
                return each

    @staticmethod
    def replaceprop(old, new, statements):
        new_statements = []
        for each in statements:
            if each["property"] == old:
                new_statements.append({"property": new, "value": each["value"]})
            else:
                new_statements.append(each)
        return new_statements

    def createprop(self, prop):
        label = prop["property"]
        datatype = prop.get("_datatype", "string")
        print("will try to create prop")
        prop = json.dumps({"labels": {"en": {"language": "en", "value": label}}, "datatype": datatype})
        e = self.session.post(
            self.api_url,
            data=dict(
                action="wbeditentity",
                new="property",
                data=prop,
                format="json",
                token=self.CSRF_TOKEN,
            ),
        )
        res = e.json()
        if "error" in res.keys():
            message = res["error"]["messages"][0]
            if message["name"] == "wikibase-validator-label-conflict":
                entityid = str(message["parameters"][2].split("|")[1][:-2])
                return (True, entityid)
            else:
                return (False, res)
        else:
            return (True, res["entity"]["id"])

    def push(self, entity):
        entityid = self._reconcile(entity)
        self.setlabel(entityid, entity)
        return entityid

    def push_many(self, entities):
        items = {}
        for each in entities:
            entity_id = self.push(each)
            items[entity_id] = each
        return items

    def _reconcile(self, entity, attempt=1):
        MAX_ATTEMPTS = 40
        if attempt > MAX_ATTEMPTS:
            print(
                f"Tried more than {MAX_ATTEMPTS} times to reconcile self entity.. will abort",
                entity,
            )
            return False, None
        data = {
            "reconcile": {
                "wikibasereconcileedit-version": "0.0.1",
                "urlReconcile": self.reconcile_prop_id,  # the url property
            },
            "entity": {
                "wikibasereconcileedit-version": "0.0.1/minimal",
                "statements": entity["statements"],
            },
        }
        print("Sending request: ", entity['label'])
        res = self.session.post(
            url=self.reconciler_url,
            params={"format": "json"},
            json=data,
            headers={"Content-Type": "application/json"},
        )

        if res.status_code == 200:
            resbody = res.json()
            if resbody["success"]:
                return resbody["entityId"]

        elif res.status_code == 400:
            resbody = res.json()
            # We are probably missing a property in wikibase
            msg = resbody["messageTranslations"]["en"]
            if "Could not find property" in msg:
                print("could not find property")
                print("  ", msg)
                match = re.match(".*'(.*)'", msg)
                propname = match.group(1)
                print("  ", propname)
                prop = API.getprop(propname, entity["statements"])
                ok, propid = self.createprop(prop)
                if ok:
                    print("created or found prop: ", propid)
                else:
                    print("tried to create prop but faild: ", propname, type(propid))
                entity["statements"] = API.replaceprop(propname, propid, entity["statements"])
                return self._reconcile(entity, attempt + 1)
            print(f"Reconcile status code: {res.status_code}")

        print(f"Error {res.status_code} when reconciling")
        print("   ", res.content.decode("utf8"))

        raise requests.RequestException(response=res)
