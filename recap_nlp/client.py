from __future__ import annotations

import typing as t
from dataclasses import dataclass, field
from enum import Enum

import grpc
import numpy as np
import spacy
from arg_services.nlp.v1 import nlp_pb2
from scipy.spatial import distance
from spacy.tokens import Doc, DocBin, Span, Token  # type: ignore

from recap_nlp import similarity

Doc.set_extension("vector", default=None)
Span.set_extension("vector", default=None)
Token.set_extension("vector", default=None)


def docbin2doc(docbin_bytes: bytes) -> t.Tuple[Doc, ...]:
    nlp = spacy.blank("en")
    inject_pipes(nlp)
    docbin = DocBin().from_bytes(docbin_bytes)

    return tuple(docbin.get_docs(nlp.vocab))


def list2array(values: t.Iterable[float]) -> np.ndarray:
    return np.array(values)


def inject_vectors(
    doc: Doc,
    res: nlp_pb2.VectorResponse,
) -> None:
    if res.document:
        doc._.set("vector", list2array(res.document.vector))

    if res.sentences:
        for sent, sent_res in zip(doc.sents, res.sentences):
            sent._.set("vector", list2array(sent_res.vector))

    if res.tokens:
        for token, token_res in zip(doc, res.tokens):
            token._.set("vector", list2array(token_res.vector))


def inject_pipes(
    nlp: spacy.Language, similarity_method: int = nlp_pb2.SIMILARITY_METHOD_COSINE
) -> None:
    nlp.add_pipe("vector", last=True)
    nlp.add_pipe("similarity", last=True, config={"method": similarity_method})


@spacy.Language.component("vector")
def _vector_component(doc):
    func = lambda x: x._.vector

    doc.user_hooks["vector"] = func
    doc.user_span_hooks["vector"] = func
    doc.user_token_hooks["vector"] = func

    return doc


@spacy.Language.factory("similarity")
def _similarity_factory(doc, method):
    func = similarity.mapping[method]

    doc.user_hooks["similarity"] = func
    doc.user_span_hooks["similarity"] = func
    doc.user_token_hooks["similarity"] = func

    return doc
