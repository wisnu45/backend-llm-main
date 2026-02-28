-- Active: 1757750462586@@localhost@5432@combiphar-db
ALTER TABLE public.chats ADD COLUMN IF NOT EXISTS options jsonb DEFAULT NULL; -- added on init.sql