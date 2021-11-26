#!/usr/bin/env python
# coding: utf-8
import argparse
from krawl.config import ACCESS_SECRET, ACCESS_TOKEN, CONSUMER_KEY, CONSUMER_SECRET, N_THREADS, PASSWORD, USER
from rdflib import Graph, RDF, RDFS
import rdflib as r
from krawl.wikibase.api import API
from krawl.namespaces import OKH
from concurrent.futures import ThreadPoolExecutor
import os

# DATATYPES = {"timestamp": "time", "lastSeen": "time", "lastRequested": "time"}
# TODO make sure the datetimes are corect in the ttl
DATATYPES= {}


def makeentitylists(graph):
    entitiesurls = set(rec[0] for rec in graph)
    modules = set(list(graph.subjects(RDF.type, OKH.Module)))
    items = entitiesurls - modules
    return [list(items), list(modules)]


def makeentity(subject, g, valuereps=None):
    p = False
    if valuereps is None:
        valuereps = {}
    entity = {"label": None}
    base = dict(g.namespaces())['']
    statements = [{"property": RECONCILEPROPID, "value": str(subject)}]
    predicates = g.predicate_objects(subject)
    for i, pred in enumerate(predicates):
        print(pred)
        a, v = pred
        statement = None
        if p: print("PRED: ", pred)
        if a == RDFS.label:
            if p: print(f"{i} Label found", a == RDFS.label, v)
            entity["label"] = v
        elif OKH in a:
            if p: print("  OKH in a")
            prop = a.replace(OKH, "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if type(statement["value"]) == r.term.URIRef:
                if p: print("   url")
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if type(statement["value"]) == r.term.Literal:
                if p:print("   literal")
                statement["_datatype"] = "string"
            statements.append(statement)
        elif str(RDF) in a:
            if p: print("  RDF in a")
            prop = a.replace(str(RDF), "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if type(statement["value"]) == r.term.URIRef:
                if p: print("   url")
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if type(statement["value"]) == r.term.Literal:
                if p: print("   literal")
                statement["_datatype"] = "text"
            statements.append(statement)
        else:
            if p: print("   else", a)
    entity["statements"] = statements
    return entity


def makeitems(l, g):
    items = []
    for each in l:
        items.append(makeentity(each, g))
    return items

def pushfile(file):
    g = Graph()
    g.parse(file, format="ttl")
    items, modules = makeentitylists(g)
    items = [makeentity(i,g) for i in items]
    itemids = api.push_many(items)
    module = makeentity(modules[0], g, itemids)
    return api.push(module)

if __name__ == "__main__":
    URL = os.environ.get("KRAWLER_WB_HOST", "https://losh.ose-germany.de")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "files", metavar="files", help="filepaths to process", nargs="+"
    )
    args = parser.parse_args()
    print('got n files: ', len(args.files))
    api = API(
            URL,
            USER,
            PASSWORD,
            CONSUMER_KEY,
            CONSUMER_SECRET,
            ACCESS_TOKEN,
            ACCESS_SECRET,
            RECONCILEPROPID,
        )
    with ThreadPoolExecutor(max_workers=N_THREADS) as executor:
        for created_id in list(executor.map(pushfile, args.files)):
            print(f"{URL}/index.php?title=Item:{created_id}")