import json
from krawl.config import N_THREADS
import requests
from requests_oauthlib import OAuth1
import re


class API:
    CSRF_TOKEN = None
    S = None
    AUTH = None

    def __init__(
        self,
        url,
        username,
        password,
        consumer_key,
        consumer_secret,
        access_token,
        access_secret,
        reconcilepropid="P1344",
    ):
        self.reconcilepropid = reconcilepropid

        self.RECONCILER_URL = f"{url}/rest.php/wikibase-reconcile-edit/v0/edit"
        self.API_URL = f"{url}/api.php"
        self.AUTH = OAuth1(consumer_key, consumer_secret, access_token, access_secret)
        self._init_session(username, password)

    def _init_session(self, username, password):
        self.S = requests.Session()
        self.S.mount('https://', requests.adapters.HTTPAdapter(pool_maxsize=N_THREADS,
                                    max_retries=3,
                                    pool_block=True))

        # Step 1: GET request to fetch login token
        PARAMS_0 = {
            "action": "query",
            "meta": "tokens",
            "type": "login",
            "format": "json",
        }

        R = self.S.get(url=self.API_URL, params=PARAMS_0)
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

        R = self.S.post(self.API_URL, data=PARAMS_1)

        # Step 3: GET request to fetch CSRF token
        PARAMS_2 = {"action": "query", "meta": "tokens", "format": "json"}

        R = self.S.get(url=self.API_URL, params=PARAMS_2)
        DATA = R.json()

        CSRF_TOKEN = DATA["query"]["tokens"]["csrftoken"]
        print("Got CSRF_TOKEN: ", CSRF_TOKEN)
        self.CSRF_TOKEN = CSRF_TOKEN

    def setlabel(self, entityid, entity):
        value = entity["label"]
        data = {
            "action": "wbsetlabel",
            "id": entityid,
            "token": self.CSRF_TOKEN,
            "format": "json",
            "language": "en",
            "value": value,
        }
        R = self.S.post(self.API_URL, data=data)
        if R.ok:
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
        prop = json.dumps(
            {"labels": {"en": {"language": "en", "value": label}}, "datatype": datatype}
        )
        e = self.S.post(
            self.API_URL,
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
        ok, entityid = self._reconcile(entity)
        if ok:
            self.setlabel(entityid, entity)
        return entityid

    def push_many(self, entities):
        items = {}
        for each in entities:
            items[(self.push(each))] = each
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
                "urlReconcile": self.reconcilepropid,  # the url property
            },
            "entity": {
                "wikibasereconcileedit-version": "0.0.1/minimal",
                "statements": entity["statements"],
            },
        }
        print("Sending request: ", entity['label'])
        res = self.S.post(
            url=self.RECONCILER_URL,
            params={"format": "json"},
            json=data,
            auth=self.AUTH,
            headers={"Content-Type": "application/json"},
        )

        if res.status_code == 500:
            print("Error 500 when reconciling")
            print("   ", res.content.decode("utf8"))
            return False, None

        resbody = res.json()
        if res.status_code == 400:
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
                entity["statements"] = API.replaceprop(
                    propname, propid, entity["statements"]
                )
                return self._reconcile(entity, attempt + 1)
            print(f"Reconcile status code: {res.status_code}")
        resbody = res.json()
        if res.status_code == 200 and resbody["success"]:
            return True, resbody["entityId"]

        print("Got Status ", res.status_code)
        return False, resbody
