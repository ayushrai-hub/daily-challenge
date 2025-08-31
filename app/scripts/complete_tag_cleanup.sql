-- Complete Tag Cleanup SQL Script
-- This script handles all tag cleanup requirements:
-- 1. Fix case-sensitive duplicates (JavaScript/javascript)
-- 2. Update tag types to be consistent (language tags should have tag_type='language')
-- 3. Establish proper parent-child relationships
-- 4. Mark parent category tags as featured for better navigation

-- Start a transaction so we can roll back if anything goes wrong
BEGIN;

-- 1. First fix the tag_type values for all language tags
UPDATE tags
SET tag_type = 'language'
WHERE name IN (
  'JavaScript', 'Python', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 
  'PHP', 'Swift', 'Kotlin', 'TypeScript', 'Scala', 'Perl', 'Haskell',
  'Clojure', 'Erlang', 'Elixir', 'F#', 'R', 'MATLAB', 'Dart'
) AND tag_type != 'language';

-- 2. Fix top-level category tag types
UPDATE tags
SET tag_type = 'domain'
WHERE name IN ('Languages', 'Data Structures', 'Algorithms', 'Design Patterns', 'Frameworks', 'Databases')
AND tag_type NOT IN ('domain', 'topic');

-- 3. Make Languages the parent of all language tags
DO $$
DECLARE
  languages_id UUID;
  lang_record RECORD;
  updated_count INTEGER := 0;
BEGIN
  -- Find the Languages category ID
  SELECT id INTO languages_id FROM tags WHERE name = 'Languages' LIMIT 1;
  
  IF languages_id IS NULL THEN
    -- Create the Languages category if it doesn't exist
    INSERT INTO tags (id, name, tag_type, is_featured)
    VALUES (gen_random_uuid(), 'Languages', 'domain', true)
    RETURNING id INTO languages_id;
    
    RAISE NOTICE 'Created Languages category with ID %', languages_id;
  END IF;
  
  -- For all language tags, set Languages as the parent
  FOR lang_record IN
    SELECT id, name FROM tags 
    WHERE tag_type = 'language' 
    AND parent_tag_id IS NULL
    AND name != 'Languages'
  LOOP
    UPDATE tags
    SET parent_tag_id = languages_id
    WHERE id = lang_record.id;
    
    updated_count := updated_count + 1;
    RAISE NOTICE 'Set parent for % to Languages category', lang_record.name;
  END LOOP;
  
  RAISE NOTICE 'Updated % language tags to have Languages as parent', updated_count;
END $$;

-- 4. Set is_featured for all parent category tags
UPDATE tags
SET is_featured = true
WHERE id IN (
  SELECT DISTINCT parent_tag_id FROM tags WHERE parent_tag_id IS NOT NULL
) AND is_featured = false;

-- 5. Clean up test tags and placeholder tags
DELETE FROM tags 
WHERE name LIKE 'test-%' 
AND id NOT IN (SELECT tag_id FROM problem_tags);

DELETE FROM tags 
WHERE name LIKE 'New-Tag-%' 
AND id NOT IN (SELECT tag_id FROM problem_tags);

DELETE FROM tags 
WHERE (name LIKE 'Temp%' OR name LIKE 'temp%' OR name LIKE '%_temp' OR name LIKE '%_TEMP') 
AND id NOT IN (SELECT tag_id FROM problem_tags);

-- 6. Delete empty tags
DELETE FROM tags 
WHERE (name = '' OR name IS NULL) 
AND id NOT IN (SELECT tag_id FROM problem_tags);

-- 7. Merge case-sensitive duplicates (find pairs with same lowercase name)
DO $$
DECLARE
  primary_tag_id UUID;
  duplicate_tag_id UUID;
  tag_pair RECORD;
  problem_record RECORD;
  affected_problems INTEGER := 0;
  merged_tags INTEGER := 0;
BEGIN
  -- Find tag pairs with the same lowercase name
  FOR tag_pair IN
    SELECT 
      t1.id AS primary_id, 
      t2.id AS duplicate_id,
      t1.name AS primary_name,
      t2.name AS duplicate_name
    FROM tags t1
    JOIN tags t2 ON LOWER(t1.name) = LOWER(t2.name) AND t1.id != t2.id
    WHERE 
      -- Primary should be the one with proper case (first letter uppercase)
      (t1.name ~ '^[A-Z]' AND t2.name ~ '^[a-z]')
      -- And primary should have more problem associations or be featured
      OR (
        (SELECT COUNT(*) FROM problem_tags WHERE tag_id = t1.id) > 
        (SELECT COUNT(*) FROM problem_tags WHERE tag_id = t2.id)
      )
      OR (t1.is_featured AND NOT t2.is_featured)
    ORDER BY t1.name
  LOOP
    primary_tag_id := tag_pair.primary_id;
    duplicate_tag_id := tag_pair.duplicate_id;
    
    RAISE NOTICE 'Merging duplicate tag: % (%) into % (%)', 
      tag_pair.duplicate_name, duplicate_tag_id, 
      tag_pair.primary_name, primary_tag_id;
      
    -- Move all problem associations from the duplicate to the primary tag
    FOR problem_record IN
      SELECT problem_id FROM problem_tags WHERE tag_id = duplicate_tag_id
    LOOP
      -- Only insert if the problem doesn't already have the primary tag
      IF NOT EXISTS (
        SELECT 1 FROM problem_tags 
        WHERE problem_id = problem_record.problem_id AND tag_id = primary_tag_id
      ) THEN
        INSERT INTO problem_tags (problem_id, tag_id)
        VALUES (problem_record.problem_id, primary_tag_id);
        
        affected_problems := affected_problems + 1;
      END IF;
    END LOOP;
    
    -- Delete the problem-tag associations for the duplicate
    DELETE FROM problem_tags WHERE tag_id = duplicate_tag_id;
    
    -- Update any tags that had the duplicate as parent to point to the primary
    UPDATE tags
    SET parent_tag_id = primary_tag_id
    WHERE parent_tag_id = duplicate_tag_id;
    
    -- Finally delete the duplicate tag
    DELETE FROM tags WHERE id = duplicate_tag_id;
    
    merged_tags := merged_tags + 1;
  END LOOP;
  
  RAISE NOTICE 'Merged % duplicate tags, affecting % problem associations', 
    merged_tags, affected_problems;
END $$;

-- 8. Fix other inconsistent tags (Empty tag_type values)
UPDATE tags 
SET tag_type = 'concept' 
WHERE tag_type IS NULL;

-- Commit the transaction
COMMIT;
