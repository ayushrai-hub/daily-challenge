import React, { useState, useEffect, useRef } from 'react';
import { tagApi } from '../../lib/api';
import { tagHierarchyApi } from '../../lib/adminApi';
import TagHierarchyGraph from '../../components/TagHierarchyGraph';
import './admin.css';

// For the hierarchy visualization
// Note: In a real implementation, you would need to install a package like react-d3-tree or reactflow
// For this implementation, we'll create a simplified version using custom components

const TagHierarchyManagement = () => {
  // State for tags
  const [tags, setTags] = useState([]);
  const [tagHierarchy, setTagHierarchy] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);
  
  // Auto-dismiss notifications after 5 seconds
  useEffect(() => {
    let errorTimer;
    if (error) {
      errorTimer = setTimeout(() => {
        setError(null);
      }, 5000);
    }
    return () => clearTimeout(errorTimer);
  }, [error]);
  
  // Auto-dismiss success messages after 3 seconds
  useEffect(() => {
    let messageTimer;
    if (message) {
      messageTimer = setTimeout(() => {
        setMessage(null);
      }, 3000);
    }
    return () => clearTimeout(messageTimer);
  }, [message]);
  
  // State for search and filtering
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('name'); // 'name', 'type', 'relationship'
  const [selectedTagType, setSelectedTagType] = useState(''); // For type filtering
  const [searchRelationshipType, setSearchRelationshipType] = useState('any'); // 'parent', 'child', 'any'
  const [advancedSearchOpen, setAdvancedSearchOpen] = useState(false);
  const [filteredTags, setFilteredTags] = useState([]);
  const [highlightedTagIds, setHighlightedTagIds] = useState([]);
  
  // State for hierarchy operations
  const [selectedTag, setSelectedTag] = useState(null);
  const [selectedParent, setSelectedParent] = useState(null);
  const [newRelationship, setNewRelationship] = useState({
    child_id: '',
    parent_id: '',
    relationship_type: 'parent_child'
  });
  
  // Refs for visualization container
  const hierarchyContainer = useRef(null);
  
  // Generate mock tag data for development when API is not available
  const generateMockTags = (count = 30) => {
    console.log('Generating rich mock tags for development');
    
    // Define actual tag types from the backend TagType enum
    const tagTypes = ['language', 'framework', 'concept', 'domain', 'skill_level', 'tool', 'topic', 'library'];
    
    // Create a more structured set of mock tags with realistic names and relationships
    const tagNamesByType = {
      language: ['JavaScript', 'Python', 'Java', 'C++', 'TypeScript', 'Go', 'Rust', 'PHP', 'Swift', 'Kotlin'],
      framework: ['React', 'Angular', 'Vue', 'Next.js', 'Express', 'Django', 'Spring', 'Laravel', 'Flask', 'Ruby on Rails'],
      concept: ['Algorithms', 'Data Structures', 'Design Patterns', 'OOP', 'Functional Programming', 'Concurrency', 'Recursion', 'Dynamic Programming', 'Sorting', 'Graph Theory'],
      domain: ['Web Development', 'Mobile Development', 'Backend Systems', 'DevOps', 'Machine Learning', 'Database', 'Cloud Computing', 'Security', 'Game Development', 'IoT'],
      skill_level: ['Beginner', 'Intermediate', 'Advanced', 'Expert'],
      tool: ['VS Code', 'Git', 'Docker', 'Kubernetes', 'Webpack', 'Jest', 'GitHub', 'Jenkins', 'Postman', 'Figma'],
      topic: ['Frontend', 'Backend', 'Full Stack', 'Security', 'Performance', 'Testing', 'Accessibility', 'Deployment', 'CI/CD', 'Microservices'],
      library: ['Redux', 'Axios', 'Lodash', 'NumPy', 'Pandas', 'D3.js', 'TensorFlow', 'jQuery', 'Moment.js', 'Material UI']
    };
    
    // Predefined relationships that make logical sense in software development
    const predefinedRelationships = [
      // Web development ecosystem
      { parent: 'Web Development', children: ['Frontend', 'Backend', 'Full Stack', 'Performance', 'Accessibility'] },
      { parent: 'Frontend', children: ['JavaScript', 'React', 'Vue', 'Angular', 'CSS', 'HTML'] },
      { parent: 'Backend', children: ['Python', 'Node.js', 'Java', 'Express', 'Django', 'Spring', 'Database'] },
      { parent: 'JavaScript', children: ['React', 'Vue', 'Angular', 'Node.js', 'Express', 'Redux', 'Axios'] },
      { parent: 'Python', children: ['Django', 'Flask', 'NumPy', 'Pandas', 'TensorFlow'] },
      { parent: 'React', children: ['Redux', 'Material UI', 'Next.js'] },
      
      // DevOps ecosystem
      { parent: 'DevOps', children: ['Docker', 'Kubernetes', 'CI/CD', 'Cloud Computing', 'Jenkins', 'Git'] },
      { parent: 'Cloud Computing', children: ['AWS', 'Azure', 'Google Cloud', 'Serverless'] },
      
      // Mobile development ecosystem
      { parent: 'Mobile Development', children: ['iOS', 'Android', 'React Native', 'Flutter', 'Swift', 'Kotlin'] },
      
      // Data science ecosystem
      { parent: 'Machine Learning', children: ['Python', 'TensorFlow', 'NumPy', 'Pandas', 'Data Structures', 'Algorithms'] },
      
      // Cross-cutting concepts
      { parent: 'Performance', children: ['Algorithms', 'Concurrency', 'Database'] },
      { parent: 'Testing', children: ['Jest', 'Cypress', 'Postman'] },
      { parent: 'Design Patterns', children: ['OOP', 'Functional Programming', 'Microservices'] },
      
      // Skill levels (these apply to many other tags)
      { parent: 'Beginner', children: [] },  // We'll fill this with random selections later
      { parent: 'Intermediate', children: [] },
      { parent: 'Advanced', children: [] },
      { parent: 'Expert', children: [] }
    ];
    
    // Create a map to store all the mock tags by name for easy lookup
    const tagsByName = {};
    let tagIdCounter = 0;
    
    // Helper function to get or create a tag
    const getOrCreateTag = (name, type) => {
      if (tagsByName[name]) {
        return tagsByName[name];
      }
      
      // Determine the correct tag type
      let tagType = type;
      if (!tagType) {
        // Try to infer the tag type from the name
        for (const [type, names] of Object.entries(tagNamesByType)) {
          if (names.includes(name)) {
            tagType = type;
            break;
          }
        }
        // Default to 'concept' if we couldn't determine the type
        if (!tagType) tagType = 'concept';
      }
      
      const tag = {
        id: `tag-${tagIdCounter++}`,
        name: name,
        tag_type: tagType,
        description: `${name} is a ${tagType} used in software development.`,
        parent_ids: [], // IDs of parent tags
        child_ids: []    // IDs of child tags (for bidirectional tracking)
      };
      
      tagsByName[name] = tag;
      return tag;
    };
    
    // First, create all the tags mentioned in the predefined relationships
    predefinedRelationships.forEach(rel => {
      // Create the parent tag if it doesn't exist
      getOrCreateTag(rel.parent);
      
      // Create all the child tags if they don't exist
      rel.children.forEach(childName => {
        getOrCreateTag(childName);
      });
    });
    
    // Now create any additional tags to reach our desired count
    const createdTagCount = Object.keys(tagsByName).length;
    if (createdTagCount < count) {
      const remainingCount = count - createdTagCount;
      for (let i = 0; i < remainingCount; i++) {
        // Choose a tag type
        const tagType = tagTypes[Math.floor(Math.random() * tagTypes.length)];
        
        // Choose a name from that type's list
        const typeNames = tagNamesByType[tagType];
        const name = typeNames[Math.floor(Math.random() * typeNames.length)] + ` ${i}`; // Make unique
        
        getOrCreateTag(name, tagType);
      }
    }
    
    // Convert the tags map to an array
    const allTags = Object.values(tagsByName);
    
    // Now establish the relationships based on our predefined structure
    predefinedRelationships.forEach(rel => {
      const parentTag = tagsByName[rel.parent];
      if (!parentTag) return; // Skip if parent tag doesn't exist
      
      rel.children.forEach(childName => {
        const childTag = tagsByName[childName];
        if (!childTag) return; // Skip if child tag doesn't exist
        
        // Add the parent-child relationship bidirectionally
        
        // Add parent ID to child's parent_ids array
        if (!childTag.parent_ids.includes(parentTag.id)) {
          childTag.parent_ids.push(parentTag.id);
        }
        
        // Add child ID to parent's child_ids array
        if (!parentTag.child_ids.includes(childTag.id)) {
          parentTag.child_ids.push(childTag.id);
        }
      });
    });
    
    // Add random skill level relationships to make the graph more interconnected
    const skillLevelTags = allTags.filter(t => t.tag_type === 'skill_level');
    if (skillLevelTags.length > 0) {
      // Beginner tags (basic concepts and tools)
      const beginnerTag = tagsByName['Beginner'];
      const beginnerTargets = allTags.filter(t => 
        ['HTML', 'CSS', 'Git', 'VS Code'].some(name => t.name.includes(name)) ||
        t.name.includes('Introduction') || 
        Math.random() > 0.8 // Add some randomness
      );
      
      beginnerTargets.forEach(target => {
        if (target.tag_type !== 'skill_level' && !target.parent_ids.includes(beginnerTag.id)) {
          // Add parent-child relationship bidirectionally
          target.parent_ids.push(beginnerTag.id);
          // Also add child ID to parent's child_ids array
          if (!beginnerTag.child_ids.includes(target.id)) {
            beginnerTag.child_ids.push(target.id);
          }
        }
      });
      
      // Intermediate tags
      const intermediateTag = tagsByName['Intermediate'];
      const intermediateTargets = allTags.filter(t => 
        ['JavaScript', 'Python', 'React', 'Express', 'Django'].some(name => t.name.includes(name)) ||
        Math.random() > 0.8
      );
      
      intermediateTargets.forEach(target => {
        if (target.tag_type !== 'skill_level' && !target.parent_ids.includes(intermediateTag.id)) {
          // Add parent-child relationship bidirectionally
          target.parent_ids.push(intermediateTag.id);
          // Also add child ID to parent's child_ids array
          if (!intermediateTag.child_ids.includes(target.id)) {
            intermediateTag.child_ids.push(target.id);
          }
        }
      });
      
      // Advanced tags (frameworks, advanced concepts)
      const advancedTag = tagsByName['Advanced'];
      const advancedTargets = allTags.filter(t => 
        ['Design Patterns', 'Microservices', 'Performance', 'Security'].some(name => t.name.includes(name)) ||
        Math.random() > 0.8
      );
      
      advancedTargets.forEach(target => {
        if (target.tag_type !== 'skill_level' && !target.parent_ids.includes(advancedTag.id)) {
          // Add parent-child relationship bidirectionally
          target.parent_ids.push(advancedTag.id);
          // Also add child ID to parent's child_ids array
          if (!advancedTag.child_ids.includes(target.id)) {
            advancedTag.child_ids.push(target.id);
          }
        }
      });
      
      // Expert tags (deep specialization areas)
      const expertTag = tagsByName['Expert'];
      const expertTargets = allTags.filter(t => 
        ['Architecture', 'AI', 'Distributed Systems'].some(name => t.name.includes(name)) ||
        Math.random() > 0.9
      );
      
      expertTargets.forEach(target => {
        if (target.tag_type !== 'skill_level' && !target.parent_ids.includes(expertTag.id)) {
          // Add parent-child relationship bidirectionally
          target.parent_ids.push(expertTag.id);
          // Also add child ID to parent's child_ids array
          if (!expertTag.child_ids.includes(target.id)) {
            expertTag.child_ids.push(target.id);
          }
        }
      });
    }
    
    // Create a few cross-domain relationships to make the graph more interesting
    // For example, connect Machine Learning with Web Development via specific technologies
    if (tagsByName['Machine Learning'] && tagsByName['Web Development']) {
      const mlTag = tagsByName['Machine Learning'];
      const webDevTag = tagsByName['Web Development'];
      
      // Create some tags that bridge domains
      const bridgeTags = [
        getOrCreateTag('TensorFlow.js', 'library'),
        getOrCreateTag('ML Ops', 'domain'),
        getOrCreateTag('Data Visualization', 'topic')
      ];
      
      // Connect bridge tags to both domains
      bridgeTags.forEach(bridge => {
        if (!bridge.parent_ids.includes(mlTag.id)) {
          bridge.parent_ids.push(mlTag.id);
        }
        if (!bridge.parent_ids.includes(webDevTag.id)) {
          bridge.parent_ids.push(webDevTag.id);
        }
      });
    }
    
    // Ensure we don't have orphan tags
    allTags.forEach(tag => {
      // If a tag has no parents and it's not a top-level domain or skill
      if (tag.parent_ids.length === 0 && 
          !['domain', 'skill_level'].includes(tag.tag_type) &&
          !['Web Development', 'Mobile Development', 'DevOps', 'Machine Learning', 'Beginner', 'Intermediate', 'Advanced', 'Expert'].includes(tag.name)) {
        
        // Find a suitable parent
        const potentialParents = allTags.filter(p => 
          p.id !== tag.id && // Not self
          ['domain', 'topic'].includes(p.tag_type) // Domains or topics make good parents
        );
        
        if (potentialParents.length > 0) {
          const randomParent = potentialParents[Math.floor(Math.random() * potentialParents.length)];
          tag.parent_ids.push(randomParent.id);
        }
      }
    });
    
    return allTags;
  };
  
  // Fetch all tags
  const fetchTags = async () => {
    try {
      const response = await tagApi.getTags({
        include_hierarchy: true,
        page_size: 1000
      });
      
      // Check for both possible API response formats
      // Format 1: { items: [...], total: X } (paginated)
      // Format 2: [...] (direct array)
      const tagsData = response.data && response.data.items ? response.data.items : 
                     (Array.isArray(response.data) ? response.data : []);
      
      if (tagsData.length > 0) {
        console.log('Successfully loaded', tagsData.length, 'tags from API');
        setTags(tagsData);
        setFilteredTags(tagsData);
      } else {
        // Only use mock data if the API returned an empty array
        console.log('API returned empty tag data, using mock data');
        const mockTags = generateMockTags(10);
        setTags(mockTags);
        setFilteredTags(mockTags);
      }
      setLoading(false);
    } catch (err) {
      console.error('Error fetching tags:', err);
      console.log('Using mock tag data for development');
      
      // In development, use mock data if the API fails
      const mockTags = generateMockTags(10);
      setTags(mockTags);
      setFilteredTags(mockTags);
      setLoading(false);
    }
  };
  
  // Fetch tag hierarchy data
  const fetchTagHierarchy = async () => {
    try {
      const response = await tagHierarchyApi.getTagHierarchy();
      
      if (response && response.data) {
        console.log('Successfully loaded', response.data.length, 'tag hierarchy relationships from API');
        setTagHierarchy(response.data || []);
      } else {
        // Handle empty response
        console.log('API returned empty tag hierarchy data');
        setTagHierarchy([]);
      }
    } catch (err) {
      console.error('Error fetching tag hierarchy:', err);
      setError('Failed to load tag hierarchy. Please try again later.');
      // Initialize with empty array to prevent further errors
      setTagHierarchy([]);
    }
  };
  
  // Effect to load data on component mount
  useEffect(() => {
    // Initialize with empty arrays to prevent errors before data loads
    setTags([]);
    setFilteredTags([]);
    setTagHierarchy([]);
    
    // Fetch actual data
    fetchTags();
    fetchTagHierarchy();
  }, []);
  
  // Process tag relationships whenever tag hierarchy data changes
  useEffect(() => {
    // Process the actual tag hierarchy data from the API
    if (tagHierarchy && tagHierarchy.length > 0 && tags && tags.length > 0) {
      console.log('Processing tag relationships from API data:', tagHierarchy.length, 'relationships');
      
      // Create a map of tags by ID for quick lookups
      const tagMap = new Map();
      tags.forEach(tag => tagMap.set(tag.id, tag));
      
      // Create a new array to track processed relationships
      const processedRelationships = tagHierarchy.map(relation => {
        const parentTag = tagMap.get(relation.parent_tag_id);
        const childTag = tagMap.get(relation.child_tag_id);
        
        return {
          ...relation,
          parent_name: parentTag ? parentTag.name : 'Unknown Parent',
          child_name: childTag ? childTag.name : 'Unknown Child'
        };
      });
      
      // Update tag objects with their parent and child IDs
      const updatedTags = [...tags];
      
      // Initialize parent_ids and child_ids arrays if they don't exist
      updatedTags.forEach(tag => {
        if (!tag.parent_ids) tag.parent_ids = [];
        if (!tag.child_ids) tag.child_ids = [];
      });
      
      // Populate parent-child relationships
      processedRelationships.forEach(relation => {
        const childTag = updatedTags.find(t => t.id === relation.child_tag_id);
        const parentTag = updatedTags.find(t => t.id === relation.parent_tag_id);
        
        if (childTag && !childTag.parent_ids.includes(relation.parent_tag_id)) {
          childTag.parent_ids.push(relation.parent_tag_id);
        }
        
        if (parentTag && !parentTag.child_ids.includes(relation.child_tag_id)) {
          parentTag.child_ids.push(relation.child_tag_id);
        }
      });
      
      // Update the tags state with the enriched relationship data
      setTags(updatedTags);
      
      console.log('Tag relationships processed:', processedRelationships.length, 'total relationships');
    }
  }, [tagHierarchy, tags.length]);
  
  // Reset relationship filter when selected tag changes
  useEffect(() => {
    if (selectedTag) {
      // Force relationship dropdown to reset when tag changes
      setSearchRelationshipType('any');
    }
  }, [selectedTag]);
  
  // Filter tags based on enhanced search criteria
  useEffect(() => {
    // If tags is undefined or empty, set filteredTags to empty array
    if (!tags || !Array.isArray(tags)) {
      setFilteredTags([]);
      setHighlightedTagIds([]);
      return;
    }
    
    // If no search query and no filters active, show all tags
    if (!searchQuery.trim() && !selectedTagType && !advancedSearchOpen) {
      setFilteredTags(tags);
      setHighlightedTagIds([]);
      return;
    }
    
    // Apply filters based on search criteria
    let filtered = [...tags];
    
    // Text search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      
      if (searchType === 'name') {
        // Filter by name
        filtered = filtered.filter(tag => 
          tag && tag.name && typeof tag.name === 'string' && 
          tag.name.toLowerCase().includes(query)
        );
      } else if (searchType === 'type') {
        // Filter by tag type
        filtered = filtered.filter(tag => 
          tag && tag.tag_type && typeof tag.tag_type === 'string' && 
          tag.tag_type.toLowerCase().includes(query)
        );
      } else if (searchType === 'description') {
        // Filter by description
        filtered = filtered.filter(tag => 
          tag && tag.description && typeof tag.description === 'string' && 
          tag.description.toLowerCase().includes(query)
        );
      }
    }
    
    // Tag type filter
    if (selectedTagType) {
      filtered = filtered.filter(tag => 
        tag && tag.tag_type === selectedTagType
      );
    }
    
    // Relationship filter (if a tag is selected and advanced search is enabled)
    if (advancedSearchOpen && selectedTag && searchRelationshipType !== 'any') {
      if (searchRelationshipType === 'parent') {
        // Find tags that are parents of the selected tag
        filtered = filtered.filter(tag => 
          selectedTag.parent_ids && 
          Array.isArray(selectedTag.parent_ids) && 
          selectedTag.parent_ids.includes(tag.id)
        );
      } else if (searchRelationshipType === 'child') {
        // Find tags that are children of the selected tag
        filtered = filtered.filter(tag => 
          tag.parent_ids && 
          Array.isArray(tag.parent_ids) && 
          tag.parent_ids.includes(selectedTag.id)
        );
      } else if (searchRelationshipType === 'sibling') {
        // Find tags that share parents with the selected tag
        const selectedTagParents = selectedTag.parent_ids || [];
        filtered = filtered.filter(tag => 
          tag.id !== selectedTag.id && // Not the same tag
          tag.parent_ids && 
          Array.isArray(tag.parent_ids) && 
          // Has at least one parent in common
          tag.parent_ids.some(parentId => selectedTagParents.includes(parentId))
        );
      }
    }
    
    // Store IDs of filtered tags for highlighting in the graph
    const highlightIds = filtered.map(tag => tag.id);
    
    setFilteredTags(filtered);
    setHighlightedTagIds(highlightIds);
  }, [searchQuery, searchType, selectedTagType, searchRelationshipType, advancedSearchOpen, tags, selectedTag]);
  
  // Function to build a hierarchical tree structure from flat data
  const buildHierarchyTree = () => {
    if (!tags || !Array.isArray(tags) || tags.length === 0) return [];
    
    let tagMap = new Map();
    
    try {
      console.log('Building hierarchy tree with:', tags.length, 'tags and', tagHierarchy.length, 'relationships');
      
      // Create a map of all tags for quick lookup
      tagMap = new Map();
      tags.forEach(tag => {
        if (tag && tag.id) {
          tagMap.set(tag.id, { 
            ...tag, 
            children: [], 
            parent_ids: [] 
          });
        }
      });
      
      // Process relationships from API if available
      if (tagHierarchy && tagHierarchy.length > 0) {
        tagHierarchy.forEach(relation => {
          const parentId = relation.parent_tag_id;
          const childId = relation.child_tag_id;
          
          if (parentId && childId) {
            const parent = tagMap.get(parentId);
            const child = tagMap.get(childId);
            
            if (parent && child) {
              // Add child to parent's children if not already there
              if (!parent.children.includes(childId)) {
                parent.children.push(childId);
              }
              
              // Add parent to child's parent_ids if not already there
              if (!child.parent_ids.includes(parentId)) {
                child.parent_ids.push(parentId);
              }
            }
          }
        });
      }
    } catch (error) {
      console.error('Error building hierarchy tree:', error);
      // Return empty array on error
      return [];
    }
    
    // Find root nodes (tags without parents)
    const rootTags = [];
    tagMap.forEach(tag => {
      if (!tag.parent_ids || !Array.isArray(tag.parent_ids) || tag.parent_ids.length === 0) {
        rootTags.push(tag);
      }
    });
    
    console.log('Found', rootTags.length, 'root tags without parents');
    return rootTags;
  };
  
  // Helper for cycle detection in tag hierarchies
  const checkForCycle = (parentId, childId, tagsList) => {
    // If they're the same, it's a direct cycle
    if (parentId === childId) {
      const selfTag = tagsList.find(t => t.id === parentId);
      const tagName = selfTag ? selfTag.name : 'Unknown';
      return {
        hasCycle: true,
        path: [tagName],
        message: `Self-referential cycle detected: ${tagName} cannot be its own parent/child`
      };
    }
    
    // Set to keep track of visited nodes
    const visited = new Set();
    // Path of the cycle if found (tag names)
    let cyclePath = [];
    
    // DFS to check for cycles
    const findCycle = (currentId, targetId, path = []) => {
      // Skip if already visited
      if (visited.has(currentId)) return false;
      visited.add(currentId);
      
      // Get the current tag
      const currentTag = tagsList.find(t => t.id === currentId);
      if (!currentTag) return false;
      
      // Get the current tag's name for the path
      const currentName = currentTag.name || 'Unknown';
      const currentPath = [...path, currentName];
      
      // Check if current node has the target as a parent (would create cycle)
      if (currentTag.parent_ids && currentTag.parent_ids.includes(targetId)) {
        const targetTag = tagsList.find(t => t.id === targetId);
        cyclePath = [...currentPath, targetTag ? targetTag.name : 'Unknown'];
        return true;
      }
      
      // Check all parents of current node
      if (currentTag.parent_ids) {
        for (const pId of currentTag.parent_ids) {
          if (findCycle(pId, targetId, currentPath)) {
            return true;
          }
        }
      }
      
      return false;
    };
    
    // Start from the child and try to reach the parent
    const hasCycle = findCycle(childId, parentId);
    
    let message = '';
    if (hasCycle && cyclePath.length > 0) {
      message = `Cycle detected: ${cyclePath.join(' → ')}${cyclePath.length > 0 ? ' → ' + cyclePath[0] : ''}`;
    }
    
    return {
      hasCycle,
      path: cyclePath,
      message
    };
  };
  
  // Create parent-child relationship
  const createRelationship = async () => {
    // Validate inputs
    if (!newRelationship.child_id && !newRelationship.parent_id) {
      setError('At least one tag (parent or child) must be selected');
      return;
    }
    
    // Clear any previous messages before starting
    setMessage(null);
    setError(null);
    
    if (newRelationship.parent_id && newRelationship.child_id) {
      // Check if this relationship already exists
      const relationshipExists = tagHierarchy.some(rel => 
        rel.parent_tag_id === newRelationship.parent_id && 
        rel.child_tag_id === newRelationship.child_id
      );
      
      if (relationshipExists) {
        setError('This parent-child relationship already exists');
        // Reset the form on error
        setNewRelationship({
          parent_id: '',
          child_id: '',
          relationship_type: 'parent_child'
        });
        return;
      }
      
      // Find the parent and child tags
      const parentTag = tags.find(t => t.id === newRelationship.parent_id);
      const childTag = tags.find(t => t.id === newRelationship.child_id);
      
      if (parentTag && childTag) {
        // Check for the reverse relationship (which would create a direct cycle)
        const reverseRelationshipExists = tagHierarchy.some(rel => 
          rel.parent_tag_id === newRelationship.child_id && 
          rel.child_tag_id === newRelationship.parent_id
        );
        
        if (reverseRelationshipExists) {
          setError(`Cannot create this relationship as '${childTag.name}' is already a parent of '${parentTag.name}'`);
          // Reset the form on error
          setNewRelationship({
            parent_id: '',
            child_id: '',
            relationship_type: 'parent_child'
          });
          return;
        }
        
        // Check for transitive cycles using the checkForCycle function
        // This detects longer cycles like A→B→C→A
        const cycleResult = checkForCycle(parentTag.id, childTag.id, tags);
        
        if (cycleResult.hasCycle) {
          const cycleMsg = `Cannot create this relationship as '${cycleResult.path[0]}' is already a parent of '${cycleResult.path[cycleResult.path.length-1]}'`;
          console.error('Cycle detected:', cycleResult.path.join(' → '));
          
          // Set error using setTimeout to prevent UI blocking
          setTimeout(() => {
            setError(cycleMsg);
            // Reset the form on error
            setNewRelationship({
              parent_id: '',
              child_id: '',
              relationship_type: 'parent_child'
            });
          }, 0);
          return;
        }
      }
    }
    
    let relationshipCreated = false;
    
    try {
      // Try the regular API call
      await tagHierarchyApi.createHierarchyRelationship(
        newRelationship.parent_id,
        newRelationship.child_id,
        newRelationship.relationship_type
      );
      console.log('API call successful');
      relationshipCreated = true;
      
      // First fetch the tag hierarchy, then fetch tags
      await fetchTagHierarchy();
      await fetchTags();
      
      // Force a refresh of the component by updating the selected tag
      if (selectedTag) {
        const refreshedTag = tags.find(t => t.id === selectedTag.id);
        if (refreshedTag) {
          setSelectedTag(refreshedTag);
        }
      }
      
      // Set success message
      setMessage('Parent-child relationship created successfully');
      
      // Reset form after successful creation
      setNewRelationship({
        parent_id: '',
        child_id: '',
        relationship_type: 'parent_child'
      });
    } catch (apiError) {
      // Handle API errors (like cycle detection)
      if (apiError.response?.status === 400) {
        const errorMessage = apiError.response?.data?.detail || 'Failed to create relationship';
        console.error('API error:', errorMessage);
        
        // Use setTimeout to prevent UI blocking
        setTimeout(() => {
          setError(errorMessage);
          
          // Reset the form on error
          setNewRelationship({
            parent_id: '',
            child_id: '',
            relationship_type: 'parent_child'
          });
        }, 0);
        return;
      }
      
      // For development - if API endpoint doesn't exist, handle manually
      if (import.meta.env.DEV && (apiError.isEndpointMissing || apiError.response?.status === 404)) {
        console.warn('Using local mock implementation for relationship creation');
  
        // Get fresh copies to work with
        const tagsCopy = [...tags];
        
        // Find the parent and child tags in our tags copy
        const parentTag = newRelationship.parent_id ? tagsCopy.find(t => t.id === newRelationship.parent_id) : null;
        const childTag = newRelationship.child_id ? tagsCopy.find(t => t.id === newRelationship.child_id) : null;
        
        // Validate relationship before creating it
        if (parentTag && childTag) {
          // Check for cycles first
          const cycleResult = checkForCycle(parentTag.id, childTag.id, tagsCopy);
          
          if (cycleResult.hasCycle) {
            const errorMsg = `Cannot create this relationship as it would create a circular reference: ${cycleResult.path.join(' → ')}`;
            console.error(errorMsg);
            setError(errorMsg);
            // Reset the form on error
            setNewRelationship({
              parent_id: '',
              child_id: '',
              relationship_type: 'parent_child'
            });
            return;
          }
          
          // Update tags with the new relationship
          for (let i = 0; i < tagsCopy.length; i++) {
            // Update child tag with parent reference
            if (tagsCopy[i].id === childTag.id) {
              const updatedParentIds = [...(tagsCopy[i].parent_ids || [])];
              if (!updatedParentIds.includes(parentTag.id)) {
                updatedParentIds.push(parentTag.id);
                tagsCopy[i] = { ...tagsCopy[i], parent_ids: updatedParentIds };
              }
            }
            
            // Update parent tag with child reference
            if (tagsCopy[i].id === parentTag.id) {
              const updatedChildIds = [...(tagsCopy[i].child_ids || [])];
              if (!updatedChildIds.includes(childTag.id)) {
                updatedChildIds.push(childTag.id);
                tagsCopy[i] = { ...tagsCopy[i], child_ids: updatedChildIds };
              }
            }
          }
          
          console.log(`Created bidirectional relationship: ${parentTag.name} <-> ${childTag.name}`);
          relationshipCreated = true;
          
          // Update the state
          setTags(tagsCopy);
          
          // Update the hierarchy for visualization
          setTagHierarchy(prev => [
            ...prev,
            {
              parent_tag_id: parentTag.id,
              child_tag_id: childTag.id,
              relationship_type: newRelationship.relationship_type
            }
          ]);
        } else if (parentTag && !newRelationship.child_id) {
          // Handle parent-only relationship
            console.log(`Created parent-only relationship for tag: ${parentTag.name} (ID: ${parentTag.id})`);
            
            // Create a virtual child for visualization
            const mockChildId = `virtual-child-${Date.now()}`;
            const mockChildName = `Virtual Child of ${parentTag.name}`;
            
            // Find parent tag index
            const parentIndex = tagsCopy.findIndex(t => t.id === parentTag.id);
            if (parentIndex !== -1) {
              // Update parent tag to reference this virtual child
              const updatedChildIds = [...(tagsCopy[parentIndex].child_ids || [])];
              updatedChildIds.push(mockChildId);
              
              tagsCopy[parentIndex] = {
                ...tagsCopy[parentIndex],
                _is_root_parent: true,
                child_ids: updatedChildIds,
                _root_parent_for: [...(tagsCopy[parentIndex]._root_parent_for || []), mockChildId]
              };
            }
            
            // Add the virtual child tag
            tagsCopy.push({
              id: mockChildId,
              name: mockChildName,
              tag_type: 'virtual',
              parent_ids: [parentTag.id],
              _is_virtual: true,
              _virtual_parent: parentTag.id
            });
            
            relationshipCreated = true;
          }
          // Handle child-only relationship
          else if (childTag && !newRelationship.parent_id) {
            console.log(`Created child-only relationship for tag: ${childTag.name} (ID: ${childTag.id})`);
            
            // Create a virtual parent for visualization
            const mockParentId = `virtual-parent-${Date.now()}`;
            const mockParentName = `Virtual Parent of ${childTag.name}`;
            
            // Find child tag index
            const childIndex = tagsCopy.findIndex(t => t.id === childTag.id);
            if (childIndex !== -1) {
              // Update child tag to reference this virtual parent
              const updatedParentIds = [...(tagsCopy[childIndex].parent_ids || [])];
              updatedParentIds.push(mockParentId);
              
              tagsCopy[childIndex] = {
                ...tagsCopy[childIndex],
                _is_leaf_child: true,
                parent_ids: updatedParentIds,
                _leaf_child_for: [...(tagsCopy[childIndex]._leaf_child_for || []), mockParentId]
              };
            }
            
            // Add the virtual parent tag
            tagsCopy.push({
              id: mockParentId,
              name: mockParentName,
              tag_type: 'virtual',
              child_ids: [childTag.id],
              _is_virtual: true,
              _virtual_child: childTag.id
            });
            
            relationshipCreated = true;
          }
          
          // Now that we've updated our copy, set it as the new state
          if (relationshipCreated) {
            setTags(tagsCopy);
            
            // Force a refresh of the hierarchy visualization
            setTimeout(() => {
              console.log('Refreshing tag hierarchy after relationship update');
              if (tagHierarchy && Array.isArray(tagHierarchy)) {
                setTagHierarchy([...tagHierarchy]); // trigger re-render
              }
              
              // If we have a selected tag, refresh it with the latest data
              if (selectedTag) {
                const updatedTag = tagsCopy.find(t => t.id === selectedTag.id);
                if (updatedTag) {
                  setSelectedTag({...updatedTag});
                }
              }
            }, 100);
          }
        } else {
          // If not in development or not an API missing error, re-throw
          throw apiError;
        }
      }
      try{
      if (relationshipCreated) {
        // Always reset form completely after successful creation
        setNewRelationship({
          child_id: '',
          parent_id: '',
          relationship_type: 'parent_child'
        });
        
        // Set appropriate success message based on relationship type
        if (newRelationship.parent_id && newRelationship.child_id) {
          setMessage('Parent-child relationship created successfully');
        } else if (newRelationship.parent_id) {
          setMessage('Parent relationship created successfully');
        } else if (newRelationship.child_id) {
          setMessage('Child relationship created successfully');
        } else {
          setMessage('Relationship created successfully');
        }
        
        // Refresh the selected tag to reflect new relationships
        if (selectedTag) {
          // Find the updated version of the selected tag in the current tags array
          const refreshedTag = tags.find(t => t.id === selectedTag.id);
          if (refreshedTag) {
            // Update the selected tag state with the fresh data
            setSelectedTag({...refreshedTag});
          }
        }
      }
      
      // Set success message when done
      if (relationshipCreated) {
        setMessage('Parent-child relationship created successfully');
      }
    } catch (error) {
      console.error('Error creating tag relationship:', error);
      setError('Failed to create tag relationship. Please try again later.');
      
      // Reset the form on error
      setNewRelationship({
        parent_id: '',
        child_id: '',
        relationship_type: 'parent_child'
      });
    }
  };
  
  // Remove parent-child relationship
  const removeRelationship = async (parentId, childId) => {
    if (!parentId || !childId) {
      setError('Invalid relationship parameters');
      return;
    }
    
    if (!confirm('Are you sure you want to remove this relationship?')) {
      return;
    }
    
    try {
      // Clear any previous messages
      setMessage(null);
      setError(null);
      
      // Make a copy of the current states for potential rollback
      const previousTagHierarchy = [...tagHierarchy];
      const previousTags = [...tags];
      
      // Update tagHierarchy - remove the specific relationship
      setTagHierarchy(prevHierarchy => 
        prevHierarchy.filter(rel => 
          !(rel.parent_tag_id === parentId && rel.child_tag_id === childId)
        )
      );
      
      // Update tags state to remove the parent-child references in the tag objects
      // This is crucial for the graph visualization to update properly
      setTags(prevTags => 
        prevTags.map(tag => {
          // If this is the child tag, remove the parent from its parent_ids
          if (tag.id === childId) {
            return {
              ...tag,
              parent_ids: (tag.parent_ids || []).filter(pid => pid !== parentId)
            };
          }
          // If this is the parent tag, remove the child from its child_ids
          if (tag.id === parentId) {
            return {
              ...tag,
              child_ids: (tag.child_ids || []).filter(cid => cid !== childId)
            };
          }
          return tag;
        })
      );
      
      // Show success message immediately for better feedback
      setMessage('Tag relationship removed successfully');
      
      // Then make the API call without waiting for it to complete
      tagHierarchyApi.removeHierarchyRelationship(parentId, childId)
        .then(() => {
          console.log('Successfully removed relationship between', parentId, 'and', childId);
        })
        .catch(err => {
          // Only in case of error, revert to previous state
          console.error('Error removing tag relationship:', err);
          setError('Failed to remove tag relationship. Please try again later.');
          
          // Restore previous states
          setTagHierarchy(previousTagHierarchy);
          setTags(previousTags);
        });
    } catch (err) {
      console.error('Unexpected error in removeRelationship:', err);
      setError('An unexpected error occurred. Please try again later.');
    }
  };
  
  // Handle tag selection for hierarchy operations
  const handleTagSelect = (tag) => {
    setSelectedTag(tag);
  };
  
  // Handle parent tag selection
  const handleParentSelect = (tag) => {
    setSelectedParent(tag);
    setNewRelationship(prev => ({
      ...prev,
      parent_id: tag.id
    }));
  };
  
  // Handle child tag selection
  const handleChildSelect = (tag) => {
    setNewRelationship(prev => ({
      ...prev,
      child_id: tag.id
    }));
  };
  
  // Simplified Tag Node component for hierarchy visualization
  const TagNode = ({ tag, level = 0, onSelect }) => {
    const [expanded, setExpanded] = useState(level < 2);
    
    // Don't render if no tag
    if (!tag) return null;
    
    // Handle two possible children formats:
    // 1. An array of child objects (original format)
    // 2. An array of child IDs that need to be looked up (new mock data format)
    const getChildTags = () => {
      if (!tag.children || !Array.isArray(tag.children)) return [];
      
      // If the first child is an object with properties, assume we have full child objects
      if (tag.children.length > 0 && typeof tag.children[0] === 'object' && tag.children[0] !== null) {
        return tag.children;
      }
      
      // Otherwise, assume we have child IDs and need to look them up in the tags array
      return tag.children
        .map(childId => {
          if (!tags || !Array.isArray(tags)) return null;
          return tags.find(t => t && t.id === childId);
        })
        .filter(child => child !== null && child !== undefined);
    };
    
    // Get parents for this tag to display parent count
    const getParentCount = () => {
      if (!tag || !tag.id) return 0;
      
      // Count how many tags have this tag in their children
      return tagHierarchy.filter(rel => rel.child_tag_id === tag.id).length;
    };
    
    const childTags = getChildTags();
    const hasChildren = childTags.length > 0;
    const parentCount = getParentCount();
    const hasParents = parentCount > 0;
    
    // Determine if this tag is highlighted (searched) or selected
    const isHighlighted = highlightedTagIds.includes(tag.id);
    const isSelected = selectedTag?.id === tag.id;
    
    return (
      <div className={`tag-node ${isHighlighted ? 'highlighted' : ''}`} style={{ marginLeft: `${level * 20}px` }}>
        <div className="tag-node-header">
          {hasChildren && (
            <button className="expand-btn" onClick={() => setExpanded(!expanded)}>
              {expanded ? '▼' : '►'}
            </button>
          )}
          
          <div 
            className={`tag-label ${isSelected ? 'selected' : ''}`}
            onClick={() => onSelect(tag)}
          >
            {tag.name || 'Unnamed Tag'}
            {hasChildren && <span className="tag-count">({childTags.length})</span>}
            {tag.tag_type && <span className="tag-type">{tag.tag_type}</span>}
            {hasParents && <span className="parent-indicator" title={`Has ${parentCount} parent${parentCount > 1 ? 's' : ''}`}>↑{parentCount}</span>}
          </div>
        </div>
        
        {expanded && hasChildren && (
          <div className="tag-children">
            {childTags.map(childTag => (
              <TagNode 
                key={childTag?.id || Math.random().toString(36).substring(2, 9)} 
                tag={childTag} 
                level={level + 1}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>
    );
  };
  
  // Render tag hierarchy visualization
  const renderHierarchy = () => {
    return (
      <div className="tag-hierarchy">
        {loading ? (
          <div className="loading">
            <div className="loading-spinner"></div>
            <div style={{ marginLeft: '10px' }}>Loading tag hierarchy...</div>
          </div>
        ) : error ? (
          <div className="error-message">{error}</div>
        ) : !tags || !Array.isArray(tags) || tags.length === 0 ? (
          <div className="no-hierarchy">No tags available</div>
        ) : (
          <TagHierarchyGraph 
            tags={filteredTags.length > 0 && searchQuery ? filteredTags : tags}
            onTagSelect={handleTagSelect}
            selectedTagId={selectedTag?.id}
            highlightedTagIds={highlightedTagIds}
            width={500}
            height={400}
          />
        )}
      </div>
    );
  };
  
  // Render tag parent-child relation information when a tag is selected
  const renderTagRelations = () => {
    if (!selectedTag) return null;
    
    // Safety checks for the selected tag's properties
    if (!selectedTag.id) {
      console.warn('Selected tag missing ID');
      return null;
    }
    
    // Get actual relationships from the tag hierarchy data structure
    // This uses the source of truth (tagHierarchy) rather than the computed relationships
    const parentRelations = tagHierarchy.filter(rel => 
      rel.child_tag_id === selectedTag.id
    );
    
    const childRelations = tagHierarchy.filter(rel => 
      rel.parent_tag_id === selectedTag.id
    );
    
    // Map relationship IDs to actual tag objects
    let parents = parentRelations.map(rel => {
      const parentTag = tags.find(tag => tag.id === rel.parent_tag_id);
      return parentTag || { id: rel.parent_tag_id, name: 'Unknown Tag' };
    });
    
    let children = childRelations.map(rel => {
      const childTag = tags.find(tag => tag.id === rel.child_tag_id);
      return childTag || { id: rel.child_tag_id, name: 'Unknown Tag' };
    });
    
    // Remove any duplicate relationships (shouldn't happen, but just in case)
    parents = parents.filter((parent, index, self) => 
      index === self.findIndex(p => p.id === parent.id)
    );
    
    children = children.filter((child, index, self) => 
      index === self.findIndex(c => c.id === child.id)
    );
    
    // Debug logging
    console.log('Selected tag:', selectedTag.name, 'ID:', selectedTag.id);
    console.log('Parents found:', parents.map(p => p.name || 'Unknown'));
    console.log('Children found:', children.map(c => c.name || 'Unknown'));
    console.log('Parent relations:', parentRelations);
    console.log('Child relations:', childRelations);
    
    return (
      <div className="tag-relations">
        <h3>Tag Relationships for: {selectedTag.name || 'Selected Tag'}</h3>
        
        <div className="relations-grid">
          <div className="parents-section">
            <h4>Parent Tags ({parents.length})</h4>
            {!parents || parents.length === 0 ? (
              <div className="no-relations">No parent tags</div>
            ) : (
              <ul className="relation-list">
                {parents.map(parent => (
                  <li key={parent?.id || Math.random().toString(36).substring(2)} className="relation-item">
                    <span className="relation-name">{parent?.name || 'Unnamed Parent'}</span>
                    <button 
                      className="btn-remove-relation" 
                      onClick={() => removeRelationship(parent.id, selectedTag.id)}
                      title="Remove relationship"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
          
          <div className="children-section">
            <h4>Child Tags ({children.length})</h4>
            {!children || children.length === 0 ? (
              <div className="no-relations">No child tags</div>
            ) : (
              <ul className="relation-list">
                {children.map(child => (
                  <li key={child?.id || Math.random().toString(36).substring(2)} className="relation-item">
                    <span className="relation-name">{child?.name || 'Unnamed Child'}</span>
                    <button 
                      className="btn-remove-relation" 
                      onClick={() => removeRelationship(selectedTag.id, child.id)}
                      title="Remove relationship"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    );
  };
  
  // Render the tag management interface
  return (
    <div className="tag-hierarchy-management">
      <h1>Tag Hierarchy Management</h1>
      
      {error && (
        <div className="error-message toast-notification">
          <div className="toast-content">{error}</div>
          <button className="toast-close" onClick={() => setError(null)}>×</button>
        </div>
      )}
      {message && (
        <div className="success-message toast-notification">
          <div className="toast-content">{message}</div>
          <button className="toast-close" onClick={() => setMessage(null)}>×</button>
        </div>
      )}
      
      <div className="management-grid">
        {/* Left column: Tag hierarchy visualization */}
        <div className="hierarchy-column">
          <div className="search-container">
            <div className="search-bar">
              <input 
                type="text" 
                placeholder="Search tags..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <select 
                value={searchType}
                onChange={(e) => setSearchType(e.target.value)}
                className="search-type-selector"
              >
                <option value="name">By Name</option>
                <option value="type">By Type</option>
                <option value="description">By Description</option>
              </select>
              <button 
                className={`advanced-search-toggle ${advancedSearchOpen ? 'active' : ''}`}
                onClick={() => setAdvancedSearchOpen(!advancedSearchOpen)}
                title="Toggle advanced search options"
              >
                {advancedSearchOpen ? 'Hide Filters' : 'Show Filters'}
              </button>
            </div>
            
            {advancedSearchOpen && (
              <div className="advanced-search-options">
                <div className="filter-group">
                  <label>Tag Type:</label>
                  <select 
                    value={selectedTagType}
                    onChange={(e) => setSelectedTagType(e.target.value)}
                  >
                    <option value="">All Types</option>
                    <option value="language">Language</option>
                    <option value="framework">Framework</option>
                    <option value="concept">Concept</option>
                    <option value="library">Library</option>
                    <option value="tool">Tool</option>
                    <option value="domain">Domain</option>
                    <option value="skill_level">Skill Level</option>
                  </select>
                </div>
                
                {selectedTag && (
                  <div className="filter-group">
                    <label>Relationship to selected tag:</label>
                    <select
                      value={searchRelationshipType}
                      onChange={(e) => setSearchRelationshipType(e.target.value)}
                    >
                      <option value="any">Any Relationship</option>
                      <option value="parent">Parents of {selectedTag.name || 'selected tag'}</option>
                      <option value="child">Children of {selectedTag.name || 'selected tag'}</option>
                      <option value="sibling">Siblings of {selectedTag.name || 'selected tag'}</option>
                    </select>
                  </div>
                )}
                
                <div className="search-stats">
                  Found {filteredTags.length} matching tags
                </div>
              </div>
            )}
          </div>
          
          {loading ? (
            <div className="loading">Loading tag hierarchy...</div>
          ) : (
            renderHierarchy()
          )}
        </div>
        
        {/* Right column: Tag details and relationship management */}
        <div className="details-column">
          {/* Tag details and relations when a tag is selected */}
          {selectedTag ? (
            <>
              <div className="tag-details">
                <h2>{selectedTag.name}</h2>
                <div className="tag-info">
                  <p><strong>ID:</strong> {selectedTag.id}</p>
                  <p><strong>Type:</strong> {selectedTag.tag_type || 'Not specified'}</p>
                  <p><strong>Description:</strong> {selectedTag.description || 'No description'}</p>
                </div>
              </div>
              
              {renderTagRelations()}
            </>
          ) : (
            <div className="no-selection">
              <p>Select a tag from the hierarchy to view details</p>
            </div>
          )}
          
          {/* Form to create new relationships */}
          <div className="new-relationship-form relationship-creation-container">
            <h3>Create New Relationship</h3>
            <div className="form-info">
              <p className="helper-text"><strong>Important:</strong> To create a complete relationship, you need to select <em>both</em> a parent tag and a child tag below.</p>
              <p className="helper-text secondary">For a relationship to affect the database, both parent and child must be specified.</p>
            </div>
            
            <div className="relationship-selectors">
              <div className="form-group">
                <label>Step 1: Select Parent Tag</label>
                <select 
                  value={newRelationship.parent_id} 
                  onChange={(e) => setNewRelationship(prev => ({
                    ...prev,
                    parent_id: e.target.value
                  }))}
                  className="relationship-selector"
                >
                  <option value="">Choose a parent tag</option>
                  {tags && tags.length > 0 ? tags.map(tag => (
                    <option key={tag?.id || 'tag-' + Math.random()} value={tag?.id || ''}>{tag?.name || 'Unnamed Tag'}</option>
                  )) : <option disabled>No tags available</option>}
                </select>
              </div>
              
              <div className="relationship-direction">
                <span className="arrow-down">↓</span>
                <span className="relation-label">Parent-Child</span>
              </div>
              
              <div className="form-group">
                <label>Step 2: Select Child Tag</label>
                <select 
                  value={newRelationship.child_id} 
                  onChange={(e) => setNewRelationship(prev => ({
                    ...prev,
                    child_id: e.target.value
                  }))}
                  className="relationship-selector"
                >
                  <option value="">Choose a child tag</option>
                  {tags && tags.length > 0 ? tags.map(tag => (
                    <option key={tag?.id || 'tag-' + Math.random()} value={tag?.id || ''}>{tag?.name || 'Unnamed Tag'}</option>
                  )) : <option disabled>No tags available</option>}
                </select>
              </div>
            </div>
            
            <div className="form-validation">
              {!newRelationship.parent_id && !newRelationship.child_id && (
                <p className="validation-warning">Please select at least one tag</p>
              )}
              {newRelationship.parent_id && !newRelationship.child_id && (
                <p className="validation-notice">Only parent selected. Select a child tag to create a complete relationship.</p>
              )}
              {!newRelationship.parent_id && newRelationship.child_id && (
                <p className="validation-notice">Only child selected. Select a parent tag to create a complete relationship.</p>
              )}
              {newRelationship.parent_id && newRelationship.child_id && (
                <p className="validation-success">Ready to create a complete parent-child relationship!</p>
              )}
            </div>
            
            <div className="form-actions">
              <button 
                className={`btn ${newRelationship.parent_id && newRelationship.child_id ? 'btn-success' : 'btn-primary'}`}
                onClick={createRelationship}
                disabled={!newRelationship.parent_id && !newRelationship.child_id}
              >
                {newRelationship.parent_id && newRelationship.child_id 
                  ? 'Create Complete Relationship' 
                  : (newRelationship.parent_id || newRelationship.child_id) 
                    ? 'Create Partial Relationship' 
                    : 'Create Relationship'}
              </button>
            </div>
          </div>
          
          {/* Hierarchy Stats */}
          <div className="hierarchy-stats">
            <h3>Hierarchy Statistics</h3>
            <div className="stats-grid">
              <div className="stat-item">
                <div className="stat-label">Total Tags</div>
                <div className="stat-value">{tags && Array.isArray(tags) ? tags.length : 0}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Root Tags</div>
                <div className="stat-value">
                  {tags && Array.isArray(tags) ? 
                    tags.filter(tag => tag && (!tag.parent_ids || !Array.isArray(tag.parent_ids) || tag.parent_ids.length === 0)).length : 0}
                </div>
              </div>
              <div className="stat-item">
                <div className="stat-label">Relationships</div>
                <div className="stat-value">
                  {tagHierarchy && Array.isArray(tagHierarchy) ? tagHierarchy.length : 0}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TagHierarchyManagement;
