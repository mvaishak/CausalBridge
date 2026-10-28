"""Structural checks shared by contracts and the development adapter."""

import networkx as nx

from causalbridge.schemas import Query, RuntimeCase


def has_path(case: RuntimeCase, query: Query) -> bool:
    query.bind(case)
    return nx.has_path(case.graph(), query.cause, query.outcome)


def valid_adjustment(case: RuntimeCase, query: Query) -> bool:
    """Pearl's backdoor criterion, a sufficient (not exhaustive) adjustment rule."""
    query.bind(case)
    graph = case.graph()
    adjustment = set(query.adjustment_set)
    if adjustment & nx.descendants(graph, query.cause):
        return False
    graph.remove_edges_from(list(graph.out_edges(query.cause)))
    return nx.is_d_separator(graph, {query.cause}, {query.outcome}, adjustment)
