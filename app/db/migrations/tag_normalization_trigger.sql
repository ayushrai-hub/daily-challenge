-- Function to normalize tag names in the database
CREATE OR REPLACE FUNCTION normalize_tag_name_internal(input_name TEXT) 
RETURNS TEXT AS $$
DECLARE
    normalized TEXT;
BEGIN
    -- Basic normalization rules
    
    -- 1. Trim whitespace
    normalized = TRIM(input_name);
    
    -- 2. Title case for multi-word tags
    IF position(' ' in normalized) > 0 THEN
        -- Split into words and capitalize each
        normalized = initcap(normalized);
    END IF;
    
    -- 3. Special cases for technology names
    CASE lower(normalized)
        WHEN 'javascript' THEN normalized := 'JavaScript';
        WHEN 'typescript' THEN normalized := 'TypeScript';
        WHEN 'python' THEN normalized := 'Python';
        WHEN 'java' THEN normalized := 'Java';
        WHEN 'c++' THEN normalized := 'C++';
        WHEN 'c#' THEN normalized := 'C#';
        WHEN 'golang' THEN normalized := 'Go';
        WHEN 'go' THEN normalized := 'Go';
        WHEN 'rust' THEN normalized := 'Rust';
        WHEN 'php' THEN normalized := 'PHP';
        WHEN 'html' THEN normalized := 'HTML';
        WHEN 'css' THEN normalized := 'CSS';
        WHEN 'sql' THEN normalized := 'SQL';
        WHEN 'react' THEN normalized := 'React';
        WHEN 'angular' THEN normalized := 'Angular';
        WHEN 'vue' THEN normalized := 'Vue.js';
        WHEN 'vue.js' THEN normalized := 'Vue.js';
        WHEN 'node.js' THEN normalized := 'Node.js';
        WHEN 'nodejs' THEN normalized := 'Node.js';
        WHEN 'next.js' THEN normalized := 'Next.js';
        WHEN 'nextjs' THEN normalized := 'Next.js';
        WHEN 'redux' THEN normalized := 'Redux';
        ELSE 
            -- Keep existing normalization for cases not covered
            NULL;
    END CASE;
    
    RETURN normalized;
END;
$$ LANGUAGE plpgsql;

-- Create trigger function for tag normalization
CREATE OR REPLACE FUNCTION normalize_tag_name_trigger()
RETURNS TRIGGER AS $$
BEGIN
    -- Apply normalization to the tag name
    NEW.name = normalize_tag_name_internal(NEW.name);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS tag_normalize_trigger ON tags;
CREATE TRIGGER tag_normalize_trigger
BEFORE INSERT OR UPDATE ON tags
FOR EACH ROW
EXECUTE FUNCTION normalize_tag_name_trigger();

-- Add a comment explaining the trigger
COMMENT ON TRIGGER tag_normalize_trigger ON tags IS 
    'Automatically normalizes tag names when they are inserted or updated to ensure consistency.';
