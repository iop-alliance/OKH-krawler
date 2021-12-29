#!/usr/bin/env python
# coding: utf-8

import rdflib as r
from rdflib import RDF, RDFS, Graph

from krawl.serializer.rdf import OKH

# DATATYPES = {"timestamp": "time", "lastSeen": "time", "lastRequested": "time"}
# TODO make sure the datetimes are corect in the ttl
DATATYPES = {}


def makeentitylists(graph):
    entitiesurls = set(rec[0] for rec in graph)
    modules = set(list(graph.subjects(RDF.type, OKH.Module)))
    items = entitiesurls - modules
    return [list(items), list(modules)]


def makeentity(reconcile_property, subject, g, valuereps=None):
    if valuereps is None:
        valuereps = {}
    entity = {"label": None}
    base = dict(g.namespaces())['']
    statements = [{"property": reconcile_property, "value": str(subject)}]
    predicates = g.predicate_objects(subject)
    for i, pred in enumerate(predicates):
        print(pred)
        a, v = pred
        statement = None
        if pred:
            print("PRED: ", pred)
        if a == RDFS.label:
            if pred:
                print(f"{i} Label found", a == RDFS.label, v)
            entity["label"] = v
        elif OKH in a:
            if pred:
                print("  OKH in a")
            prop = a.replace(OKH, "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if isinstance(statement["value"], r.term.URIRef):
                if pred:
                    print("   url")
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if isinstance(statement["value"], r.term.Literal):
                if pred:
                    print("   literal")
                statement["_datatype"] = "string"
            statements.append(statement)
        elif str(RDF) in a:
            if pred:
                print("  RDF in a")
            prop = a.replace(str(RDF), "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if isinstance(statement["value"], r.term.URIRef):
                if pred:
                    print("   url")
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if isinstance(statement["value"], r.term.Literal):
                if pred:
                    print("   literal")
                statement["_datatype"] = "text"
            statements.append(statement)
        else:
            if pred:
                print("   else", a)
    entity["statements"] = statements
    return entity


def makeitems(reconcile_property, l, g):
    items = []
    for each in l:
        items.append(makeentity(reconcile_property, each, g))
    return items


def pushfile(reconcile_property, file):
    g = Graph()
    g.parse(file, format="ttl")
    items, modules = makeentitylists(g)
    items = [makeentity(reconcile_property, i, g) for i in items]
    itemids = api.push_many(items)
    module = makeentity(reconcile_property, modules[0], g, itemids)
    return api.push(module)
