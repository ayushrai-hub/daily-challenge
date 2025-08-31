-- Fix Tag Categories SQL Script
-- This script updates language tags to have the correct tag_type
-- and ensures proper parent-child relationships

BEGIN;

-- 1. Update common programming languages to have the correct tag_type
UPDATE tags
SET tag_type = 'language'
WHERE name IN (
  'JavaScript', 'Python', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 
  'PHP', 'Swift', 'Kotlin', 'TypeScript', 'Scala', 'Perl', 'Haskell',
  'Clojure', 'Erlang', 'Elixir', 'F#', 'R', 'MATLAB', 'Dart'
) AND tag_type != 'language';

-- 2. Update parent categories to have domain tag type (since there's no 'category' tag_type)
UPDATE tags
SET tag_type = 'domain'
WHERE name IN ('Languages', 'Data Structures', 'Algorithms', 'Design Patterns', 'Frameworks', 'Databases')
AND tag_type NOT IN ('domain', 'topic');

-- 3. Make sure all language tags have Languages as parent
DO $$
DECLARE
  languages_id UUID;
  lang_record RECORD;
  updated_count INT := 0;
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
  
  -- For each language tag, set Languages as the parent if not already set
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
    RAISE NOTICE 'Updated parent for % to Languages category', lang_record.name;
  END LOOP;
  
  RAISE NOTICE 'Updated % language tags to have Languages as parent', updated_count;
END $$;

-- 4. Set all parent category tags as featured for better navigation
UPDATE tags
SET is_featured = true
WHERE id IN (
  SELECT DISTINCT parent_tag_id FROM tags WHERE parent_tag_id IS NOT NULL
) AND is_featured = false;

-- 5. Set is_featured for other important categories
UPDATE tags
SET is_featured = true
WHERE name IN ('Languages', 'Data Structures', 'Algorithms', 'Frameworks', 'Databases')
AND is_featured = false;

COMMIT;
