#!/usr/bin/env python
# coding: utf-8
import rdflib
import rdflib as r
from rdflib import RDF, RDFS, Graph

from krawl.serializer.rdf_serializer import OKH

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

    statements = [{"property": reconcile_property, "value": str(subject)}]
    predicates = g.predicate_objects(subject)
    namespaces_dict = dict(g.namespaces())
    predicates_dict = dict(predicates)

    if '' in namespaces_dict:
        base = namespaces_dict['']
    else:
        base = predicates_dict[
                   rdflib.term.URIRef(OKH + 'repo')] + "/" + \
               predicates_dict[
                   rdflib.term.URIRef(OKH + 'version')] + "/"

    for a in predicates_dict:
        v = predicates_dict[a]
        statement = None
        if a == RDFS.label:
            entity["label"] = v
        elif OKH in a:
            prop = a.replace(OKH, "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if isinstance(statement["value"], r.term.URIRef):
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if isinstance(statement["value"], r.term.Literal):
                statement["_datatype"] = "string"
            statements.append(statement)
        elif str(RDF) in a:
            prop = a.replace(str(RDF), "")
            statement = {
                "property": prop,
                "value": valuereps.get(v, v),
                "_datatype": DATATYPES.get(prop, "wikibase-item"),
            }
            if isinstance(statement["value"], r.term.URIRef):
                if base in statement["value"]:
                    # we got a sub item.. and keep the wikibase-item datatype
                    pass
                else:
                    statement["_datatype"] = "url"
            if isinstance(statement["value"], r.term.Literal):
                statement["_datatype"] = "text"
            statements.append(statement)
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
