-- Active: 1757750462586@@localhost@5432@combiphar-db
ALTER TABLE documents DROP COLUMN IF EXISTS chat_detail_id;
ALTER TABLE documents ADD COLUMN chat_id UUID DEFAULT NULL REFERENCES chats(id) ON DELETE CASCADE;
