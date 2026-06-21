-- Private AI Platform — Supabase / Postgres migration for pgvector RAG.
-- Run once on your Supabase project (SQL editor or `supabase db push`).
-- The API also creates this automatically on first use when VECTOR_STORE=pgvector,
-- but applying it explicitly lets you tune the index for your data volume.

create extension if not exists vector;

create table if not exists rag_chunks (
  id            text primary key,
  tenant_id     text not null,
  document_id   text not null,
  chunk_index   int  not null,
  text          text not null,          -- ciphertext at rest (AES-256-GCM)
  sensitivity   text not null,
  embedding     vector(384)             -- must match EMBEDDINGS_DIM
);

create index if not exists rag_chunks_tenant on rag_chunks (tenant_id);

-- Approximate nearest-neighbour index (cosine). Tune `lists` to ~sqrt(rows).
create index if not exists rag_chunks_embedding
  on rag_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

-- Tenant isolation note: the API always filters by tenant_id. If you expose
-- this table via PostgREST/Supabase client, also enable RLS:
-- alter table rag_chunks enable row level security;
