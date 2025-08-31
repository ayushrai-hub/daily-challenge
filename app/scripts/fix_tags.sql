-- Fix Tags SQL Script
-- This script fixes duplicate JavaScript/TypeScript tags and ensures problem associations are updated

-- 1. Start a transaction so we can roll back if anything goes wrong
BEGIN;

-- 2. Set the properly formatted JavaScript tag as the canonical one
DO $$
DECLARE
    javascript_proper_id UUID := '3bf63c91-80e5-4d4a-b5fa-aa7873d83458'; -- The properly formatted "JavaScript" tag
    javascript_lower_id UUID := '356b1060-9e3d-40d0-86a5-9b345be55b1d'; -- The lowercase "javascript" tag
    javascript_cap_id UUID := '9c8e0ebc-cf55-4b74-8aa6-4a3a1c6fd0d4'; -- The "Javascript" tag
    
    typescript_proper_id UUID := '110462d0-5156-4d3a-98ec-8a527c5e0a6c'; -- The properly formatted "TypeScript" tag
    typescript_lower_id UUID := '91434fd0-264f-477e-8035-63422fb4a909'; -- The lowercase "typescript" tag
    
    languages_id UUID := '8c8af688-1d28-4495-94ef-7bcd77c1960b'; -- The Languages parent category
    
    problem_tag_relation RECORD;
BEGIN
    -- Log the start of the process
    RAISE NOTICE 'Starting tag normalization process...';
    
    -- Update the lowercase "javascript" tag associations to use the proper JavaScript tag
    FOR problem_tag_relation IN 
        SELECT problem_id FROM problem_tags WHERE tag_id = javascript_lower_id
    LOOP
        -- Check if the problem already has the proper JavaScript tag
        IF NOT EXISTS (SELECT 1 FROM problem_tags WHERE problem_id = problem_tag_relation.problem_id AND tag_id = javascript_proper_id) THEN
            -- If not, insert the association with the proper tag
            INSERT INTO problem_tags (problem_id, tag_id) 
            VALUES (problem_tag_relation.problem_id, javascript_proper_id);
            RAISE NOTICE 'Updated problem % to use proper JavaScript tag', problem_tag_relation.problem_id;
        END IF;
    END LOOP;
    
    -- Update the "Javascript" tag associations to use the proper JavaScript tag
    FOR problem_tag_relation IN 
        SELECT problem_id FROM problem_tags WHERE tag_id = javascript_cap_id
    LOOP
        -- Check if the problem already has the proper JavaScript tag
        IF NOT EXISTS (SELECT 1 FROM problem_tags WHERE problem_id = problem_tag_relation.problem_id AND tag_id = javascript_proper_id) THEN
            -- If not, insert the association with the proper tag
            INSERT INTO problem_tags (problem_id, tag_id) 
            VALUES (problem_tag_relation.problem_id, javascript_proper_id);
            RAISE NOTICE 'Updated problem % to use proper JavaScript tag', problem_tag_relation.problem_id;
        END IF;
    END LOOP;
    
    -- Update the lowercase "typescript" tag associations to use the proper TypeScript tag
    FOR problem_tag_relation IN 
        SELECT problem_id FROM problem_tags WHERE tag_id = typescript_lower_id
    LOOP
        -- Check if the problem already has the proper TypeScript tag
        IF NOT EXISTS (SELECT 1 FROM problem_tags WHERE problem_id = problem_tag_relation.problem_id AND tag_id = typescript_proper_id) THEN
            -- If not, insert the association with the proper tag
            INSERT INTO problem_tags (problem_id, tag_id) 
            VALUES (problem_tag_relation.problem_id, typescript_proper_id);
            RAISE NOTICE 'Updated problem % to use proper TypeScript tag', problem_tag_relation.problem_id;
        END IF;
    END LOOP;
    
    -- Now that all problems have been associated with the proper tags, remove the old associations
    DELETE FROM problem_tags WHERE tag_id IN (javascript_lower_id, javascript_cap_id, typescript_lower_id);
    
    -- Update the parent category for the TypeScript tag if needed
    UPDATE tags 
    SET parent_tag_id = languages_id 
    WHERE id = typescript_proper_id AND (parent_tag_id IS NULL OR parent_tag_id != languages_id);
    
    -- Ensure the JavaScript tag has the correct tag_type
    UPDATE tags
    SET tag_type = 'language'
    WHERE id = javascript_proper_id AND (tag_type IS NULL OR tag_type != 'language');
    
    -- Ensure the TypeScript tag has the correct tag_type
    UPDATE tags
    SET tag_type = 'language'
    WHERE id = typescript_proper_id AND (tag_type IS NULL OR tag_type != 'language');
    
    -- Now delete the duplicate tags
    DELETE FROM tags WHERE id IN (javascript_lower_id, javascript_cap_id, typescript_lower_id);
    
    RAISE NOTICE 'Tag normalization complete!';
END $$;

-- 3. Fix other inconsistent tags (Empty tag_type values)
UPDATE tags 
SET tag_type = 'concept' 
WHERE tag_type IS NULL;

-- 4. Commit the transaction
COMMIT;
