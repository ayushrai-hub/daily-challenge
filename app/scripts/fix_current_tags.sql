-- Fix Current Tags SQL Script
-- This script fixes the specific duplicate tags identified in our recent analysis
-- and ensures proper hierarchical relationships

-- 1. Start a transaction so we can roll back if anything goes wrong
BEGIN;

-- 2. Set up tag merging for our specific duplicates
DO $$
DECLARE
    -- JavaScript tags we found in our analysis
    javascript_proper_id UUID := 'a1323225-5439-4fd0-abe5-ceadfb8c91bf'; -- The "JavaScript" tag
    javascript_lower_id UUID := '1dc54a66-1980-4f20-984e-41633dfa324e'; -- The "javascript" tag (lowercase)
    
    -- Languages tags we found in our analysis
    languages_proper_id UUID := '8c8af688-1d28-4495-94ef-7bcd77c1960b'; -- The "Languages" tag
    languages_lower_id UUID := '821c874f-715e-4c3e-b268-9ee77cbbccba'; -- The "languages" tag (lowercase)
    
    problem_tag_relation RECORD;
    related_problem_count INT;
    updated_problem_count INT := 0;
BEGIN
    -- Log the start of the process
    RAISE NOTICE 'Starting tag merging process for current state...';
    
    -- 1. First handle javascript/JavaScript
    -- Count how many problems are associated with the lowercase javascript tag
    SELECT COUNT(*) INTO related_problem_count FROM problem_tags WHERE tag_id = javascript_lower_id;
    RAISE NOTICE 'Found % problems associated with lowercase "javascript" tag', related_problem_count;
    
    -- Associate all problems from lowercase javascript with proper JavaScript
    FOR problem_tag_relation IN 
        SELECT problem_id FROM problem_tags WHERE tag_id = javascript_lower_id
    LOOP
        -- Check if the problem already has the proper JavaScript tag
        IF NOT EXISTS (SELECT 1 FROM problem_tags WHERE problem_id = problem_tag_relation.problem_id AND tag_id = javascript_proper_id) THEN
            -- If not, insert the association with the proper tag
            INSERT INTO problem_tags (problem_id, tag_id) 
            VALUES (problem_tag_relation.problem_id, javascript_proper_id);
            updated_problem_count := updated_problem_count + 1;
        END IF;
    END LOOP;
    
    RAISE NOTICE 'Updated % problem associations for JavaScript', updated_problem_count;
    
    -- 2. Set the parent-child relationship between Languages and JavaScript if not already set
    IF (SELECT parent_tag_id FROM tags WHERE id = javascript_proper_id) IS DISTINCT FROM languages_proper_id THEN
        UPDATE tags 
        SET parent_tag_id = languages_proper_id 
        WHERE id = javascript_proper_id;
        RAISE NOTICE 'Set Languages as parent for JavaScript tag';
    ELSE
        RAISE NOTICE 'JavaScript already has Languages as parent';
    END IF;
    
    -- 3. Now delete the lowercase tags after moving all relationships
    -- First remove all problem associations with the lowercase tags
    DELETE FROM problem_tags WHERE tag_id = javascript_lower_id;
    DELETE FROM problem_tags WHERE tag_id = languages_lower_id;
    
    -- Now delete the duplicate tags
    DELETE FROM tags WHERE id = javascript_lower_id;
    RAISE NOTICE 'Deleted lowercase javascript tag';
    
    DELETE FROM tags WHERE id = languages_lower_id;
    RAISE NOTICE 'Deleted lowercase languages tag';
    
    -- 4. Set tag_type for all remaining tags without a type
    UPDATE tags 
    SET tag_type = 'concept' 
    WHERE tag_type IS NULL;
    
    RAISE NOTICE 'Tag normalization complete!';
END $$;

-- 5. Commit the transaction
COMMIT;
