-- Begin transaction
BEGIN;

-- First remove related records in problem_tags table
DELETE FROM problem_tags 
WHERE problem_id IN (
    SELECT id FROM problems 
    WHERE title LIKE '%Test%' OR title LIKE '%test%'
);

-- Then remove related records in delivery_logs table
DELETE FROM delivery_logs 
WHERE problem_id IN (
    SELECT id FROM problems 
    WHERE title LIKE '%Test%' OR title LIKE '%test%'
);

-- Finally remove the test problems themselves
DELETE FROM problems 
WHERE title LIKE '%Test%' OR title LIKE '%test%';

-- Commit transaction if everything goes well
COMMIT;
