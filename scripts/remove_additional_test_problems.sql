-- Begin transaction
BEGIN;

-- Remove the additional test problems 
DELETE FROM problems 
WHERE title LIKE 'Read Problem%' OR title LIKE 'New Problem%';

-- Commit transaction if everything goes well
COMMIT;
