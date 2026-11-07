# Retrieval-Augmented Generation (RAG)

## Definition

Retrieval-Augmented Generation (RAG) is a method that combines information retrieval with text generation by a large language model. Before producing an answer, a RAG system retrieves relevant information from an external knowledge source and supplies it as context to the model.

## How it works

A typical RAG workflow has three steps: retrieve relevant passages, add the passages to the model's context, and generate a response grounded in those passages. Some RAG systems use embeddings to find semantically similar passages, but embeddings are not mandatory for every retrieval method.

## Why it matters

RAG can help a model answer questions about documents that were not part of its training data. Its reliability still depends on retrieval quality, source relevance, and how faithfully the generated answer uses the retrieved evidence.

## Entity alignment test instructions

This document deliberately uses the full name **Retrieval-Augmented Generation (RAG)** so that Evolving Self AI can compare a new candidate concept with an existing graph node named **RAG**. They refer to the same concept. The expected action is to **propose reusing the existing RAG node**, not to create a second node automatically. Keep this as external knowledge pending review.
