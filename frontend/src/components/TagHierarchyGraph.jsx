import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';

/**
 * Component for visualizing tag hierarchy as a directed graph using D3.js
 * 
 * @param {Object} props
 * @param {Array} props.tags - Array of tag objects with id, name, tag_type, and parent_ids
 * @param {Function} props.onTagSelect - Callback function when a tag is selected
 * @param {String} props.selectedTagId - ID of the currently selected tag
 * @param {Number} props.width - Width of the graph container (default: 600)
 * @param {Number} props.height - Height of the graph container (default: 500)
 */
const TagHierarchyGraph = ({ 
  tags, 
  onTagSelect, 
  selectedTagId, 
  highlightedTagIds = [],
  width = 600, 
  height = 500
}) => {
  const svgRef = useRef(null);
  const [tooltip, setTooltip] = useState({ visible: false, x: 0, y: 0, content: '' });

  // Process the tags data into nodes and links format for D3
  const processData = () => {
    if (!tags || !Array.isArray(tags) || tags.length === 0) {
      return { nodes: [], links: [] };
    }

    // Create a map of all tags by ID for faster lookups
    const tagMap = {};
    tags.forEach(tag => {
      tagMap[tag.id] = tag;
    });

    const nodes = tags.map(tag => ({
      id: tag.id,
      name: tag.name || 'Unnamed Tag',
      tagType: tag.tag_type || 'unspecified',
      description: tag.description || '',
      parentIds: tag.parent_ids || [],
      parents: [], // Will be populated with actual parent tags
      children: [] // Will be populated with actual child tags
    }));

    // Create a node map for easier reference
    const nodeMap = {};
    nodes.forEach(node => {
      nodeMap[node.id] = node;
    });

    // Process parent-child relationships and populate the parents and children arrays
    tags.forEach(tag => {
      if (tag.parent_ids && Array.isArray(tag.parent_ids)) {
        // For each parent ID, find the corresponding parent node
        tag.parent_ids.forEach(parentId => {
          // Add parent to this tag's parents array
          if (nodeMap[tag.id] && nodeMap[parentId]) {
            nodeMap[tag.id].parents.push(nodeMap[parentId]);
            // Also add this tag as a child to the parent
            nodeMap[parentId].children.push(nodeMap[tag.id]);
          }
        });
      }
    });

    // Create links for all parent-child relationships
    const links = [];
    tags.forEach(tag => {
      if (tag.parent_ids && Array.isArray(tag.parent_ids)) {
        tag.parent_ids.forEach(parentId => {
          // Only create link if both parent and child exist in our nodes
          if (nodeMap[parentId] && nodeMap[tag.id]) {
            links.push({
              source: parentId,
              target: tag.id,
              // Source is parent, target is child
              relation: 'parent-child'
            });
          }
        });
      }
    });

    return { nodes, links, nodeMap };
  };

  useEffect(() => {
    if (!tags || tags.length === 0 || !svgRef.current) return;

    // Process data for D3
    const { nodes, links, nodeMap } = processData();
    if (nodes.length === 0) return;

    // Clear previous graph
    d3.select(svgRef.current).selectAll("*").remove();

    // Create SVG container
    const svg = d3.select(svgRef.current)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", [0, 0, width, height])
      .attr("style", "max-width: 100%; height: auto; font: 12px sans-serif;");

    // Add zoom and pan behavior
    const g = svg.append("g");
    svg.call(d3.zoom()
      .extent([[0, 0], [width, height]])
      .scaleExtent([0.5, 5])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      }));

    // Group nodes by type for better initial placement
    const nodesByType = {};
    nodes.forEach(node => {
      if (!nodesByType[node.tagType]) {
        nodesByType[node.tagType] = [];
      }
      nodesByType[node.tagType].push(node);
    });

    // Set initial positions based on node type to create a more organized layout
    const typeCount = Object.keys(nodesByType).length;
    let typeIndex = 0;
    
    Object.entries(nodesByType).forEach(([type, typeNodes]) => {
      const angleOffset = (2 * Math.PI * typeIndex) / typeCount;
      const radius = Math.min(width, height) * 0.35;
      
      typeNodes.forEach((node, i) => {
        const angle = angleOffset + (2 * Math.PI * i) / (typeNodes.length * 3);
        node.x = width / 2 + radius * Math.cos(angle);
        node.y = height / 2 + radius * Math.sin(angle);
      });
      
      typeIndex++;
    });

    // Create the force simulation with improved forces for better layout
    const simulation = d3.forceSimulation(nodes)
      // Link force with varying distances based on relationship type
      .force("link", d3.forceLink(links)
        .id(d => d.id)
        .distance(link => {
          // Make links between similar types shorter
          const sourceType = link.source.tagType;
          const targetType = link.target.tagType;
          return sourceType === targetType ? 70 : 120;
        })
      )
      // Stronger repulsion between nodes
      .force("charge", d3.forceManyBody()
        .strength(d => -300 - d.name.length * 10) // Longer names need more space
        .distanceMax(300) // Limit the repulsion distance
      )
      // Center force to keep the graph centered in the view
      .force("center", d3.forceCenter(width / 2, height / 2))
      // Collision detection to prevent node overlap
      .force("collision", d3.forceCollide().radius(30))
      // Weaker x/y forces to allow good clustering
      .force("x", d3.forceX(width / 2).strength(0.05))
      .force("y", d3.forceY(height / 2).strength(0.05));

    // Add arrows to links for directed graph
    svg.append("defs").selectAll("marker")
      .data(["arrow"])
      .enter().append("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", "#999")
      .attr("d", "M0,-5L10,0L0,5");

    // Add different arrow markers for parent and child relationships
    svg.append("defs").selectAll("marker")
      .data(["arrow-parent", "arrow-child"])
      .enter().append("marker")
      .attr("id", d => d)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("fill", d => d === "arrow-parent" ? "#4299e1" : "#f6ad55")
      .attr("d", "M0,-5L10,0L0,5");

    // Create links with different styling for parent vs child relationships
    // Using path elements instead of lines to support curved relationships
    const link = g.append("g")
      .selectAll("path")
      .data(links)
      .join("path")
      .attr("fill", "none")
      .attr("stroke", d => {
        // Get source and target nodes, handling both object and ID references
        const sourceId = d.source.id || d.source;
        const targetId = d.target.id || d.target;
        
        // If selected tag is involved, highlight the relationship
        if (sourceId === selectedTagId || targetId === selectedTagId) {
          // If selected tag is the source, it's a parent->child relationship
          // If selected tag is the target, it's a child->parent relationship
          return sourceId === selectedTagId ? "#f6ad55" : "#4299e1";
        }
        
        // Default coloring based on relationship direction
        return "#999";
      })
      .attr("stroke-opacity", d => {
        // Highlight selected tag's relationships
        return (d.source.id === selectedTagId || d.target.id === selectedTagId) ? 0.9 : 0.5;
      })
      .attr("stroke-width", d => {
        // Make selected tag's relationships thicker
        return (d.source.id === selectedTagId || d.target.id === selectedTagId) ? 2.0 : 1.5;
      })
      .attr("marker-end", d => {
        // Different arrow markers based on relationship to selected tag
        const sourceId = d.source.id || d.source;
        const targetId = d.target.id || d.target;
        
        if (sourceId === selectedTagId || targetId === selectedTagId) {
          return sourceId === selectedTagId ? "url(#arrow-parent)" : "url(#arrow-child)";
        }
        return "url(#arrow)";
      })
      .on("mouseover", (event, d) => {
        // Highlight on hover and show tooltip
        d3.select(event.target)
          .attr("stroke-width", 2.5)
          .attr("stroke-opacity", 1);
        
        // Get source and target node information
        const sourceId = d.source.id || d.source;
        const targetId = d.target.id || d.target;
        
        // Look up the node objects to get their names
        const sourceName = nodeMap[sourceId]?.name || sourceId;
        const targetName = nodeMap[targetId]?.name || targetId;
        
        // Set relationship type information for tooltip
        let relationshipType = '';
        if (sourceId === selectedTagId) {
          relationshipType = '(parent of)';
        } else if (targetId === selectedTagId) {
          relationshipType = '(child of)';
        }
        
        setTooltip({
          visible: true,
          x: event.pageX,
          y: event.pageY,
          content: `${sourceName} → ${targetName} ${relationshipType}`
        });
      })
      .on("mouseout", (event, d) => {
        // Restore original styling
        d3.select(event.target)
          .attr("stroke-width", (d.source.id === selectedTagId || d.target.id === selectedTagId) ? 2.0 : 1.5)
          .attr("stroke-opacity", (d.source.id === selectedTagId || d.target.id === selectedTagId) ? 0.9 : 0.5);
        
        setTooltip({ visible: false, x: 0, y: 0, content: '' });
      });

    // Create nodes
    const getNodeColor = (tagType) => {
      const colors = {
        'language': '#4299e1',    // blue
        'framework': '#68d391',   // green
        'concept': '#f6ad55',     // orange
        'domain': '#fc8181',      // red
        'skill_level': '#b794f4', // purple
        'tool': '#9ae6b4',        // green-lighter
        'topic': '#c6f6d5',       // green-lightest
        'library': '#90cdf4',     // blue-lighter
      };
      return colors[tagType] || '#cbd5e0'; // gray default
    };

    // Create node groups
    const node = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .join("g")
      .attr("cursor", "pointer")
      .attr("class", d => `node ${d.id === selectedTagId ? 'selected' : ''}`)
      .on("click", (event, d) => {
        event.stopPropagation();
        if (onTagSelect) onTagSelect(d);
      })
      .on("mouseover", (event, d) => {
        setTooltip({
          visible: true,
          x: event.pageX,
          y: event.pageY,
          content: d.description || d.name
        });
      })
      .on("mouseout", () => {
        setTooltip({ visible: false, x: 0, y: 0, content: '' });
      })
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended));

    // Add circle to nodes
    // Update node appearance, with enhanced highlighting for selected tag and its relationships
    node.append("circle")
      .attr("r", d => {
        // Priorities for node sizing:
        // 1. Selected tag (largest)  
        // 2. Search results (highlighted)
        // 3. Related to selected tag
        // 4. Normal nodes (smallest)
        
        if (d.id === selectedTagId) return 22; // Selected tag
        
        // Check if this is a search result
        const isSearchResult = highlightedTagIds && highlightedTagIds.length > 0 && 
          highlightedTagIds.includes(d.id);
        
        if (isSearchResult) return 21; // Search result
        
        // Check if this node is directly related to selected tag
        const isRelated = links.some(link => {
          const sourceId = link.source.id || link.source;
          const targetId = link.target.id || link.target;
          return (sourceId === selectedTagId && targetId === d.id) || 
                 (targetId === selectedTagId && sourceId === d.id);
        });
        
        return isRelated ? 20 : 18; // Larger for related nodes
      })
      .attr("fill", d => {
        // If it's a search result and not the selected tag, use a brighter variant of the node color
        const isSearchResult = highlightedTagIds && highlightedTagIds.length > 0 && 
          highlightedTagIds.includes(d.id);
          
        if (isSearchResult && d.id !== selectedTagId) {
          // Get base color and make it brighter for search results
          const baseColor = getNodeColor(d.tagType);
          return d3.color(baseColor).brighter(0.5);
        }
        
        return getNodeColor(d.tagType);
      })
      .attr("stroke", d => {
        // Highlight priorities:
        // 1. Selected tag
        // 2. Search result
        // 3. Relationship to selected tag (parent/child)
        // 4. Normal node
        
        if (d.id === selectedTagId) return "#2c5282"; // Selected tag
        
        // Check if this is a search result
        const isSearchResult = highlightedTagIds && highlightedTagIds.length > 0 && 
          highlightedTagIds.includes(d.id);
          
        if (isSearchResult) return "#ff6b6b"; // Highlight search results with a distinct color
        
        // Check if this is a parent of selected tag
        const isParent = links.some(link => {
          const sourceId = link.source.id || link.source;
          const targetId = link.target.id || link.target;
          return sourceId === d.id && targetId === selectedTagId;
        });
        
        // Check if this is a child of selected tag
        const isChild = links.some(link => {
          const sourceId = link.source.id || link.source;
          const targetId = link.target.id || link.target;
          return sourceId === selectedTagId && targetId === d.id;
        });
        
        if (isParent) return "#4299e1"; // Parent node
        if (isChild) return "#f6ad55"; // Child node
        return "#fff"; // Normal node
      })
      .attr("stroke-width", d => {
        // Make selected tag and related tags have thicker borders
        if (d.id === selectedTagId) return 3; // Selected tag
        
        // Check if this node is directly related to selected tag
        const isRelated = links.some(link => {
          const sourceId = link.source.id || link.source;
          const targetId = link.target.id || link.target;
          return (sourceId === selectedTagId && targetId === d.id) || 
                 (targetId === selectedTagId && sourceId === d.id);
        });
        
        return isRelated ? 2 : 1.5; // Thicker for related nodes
      });

    // Add text labels to nodes
    node.append("text")
      .attr("dy", 30)
      .attr("x", 0)
      .attr("text-anchor", "middle")
      .text(d => d.name)
      .attr("fill", "#4a5568")
      .attr("font-size", "10px")
      .attr("font-weight", d => d.id === selectedTagId ? "bold" : "normal");

    // Simulation tick function to update positions with curved paths
    simulation.on("tick", () => {
      // Update path positions based on node movements
      link.attr("d", d => {
        // Get source and target positions
        const sourceX = d.source.x;
        const sourceY = d.source.y;
        const targetX = d.target.x;
        const targetY = d.target.y;
        
        if (sourceX === undefined || sourceY === undefined || targetX === undefined || targetY === undefined) {
          return "";
        }
        
        // Calculate midpoint
        const midX = (sourceX + targetX) / 2;
        const midY = (sourceY + targetY) / 2;
        
        // Check if this is a bidirectional relationship (both parent and child)
        const sourceId = d.source.id || d.source;
        const targetId = d.target.id || d.target;
        
        const isBidirectional = links.some(l => {
          const s = l.source.id || l.source;
          const t = l.target.id || l.target;
          return s === targetId && t === sourceId;
        });
        
        if (isBidirectional) {
          // For bidirectional relationships, use a quadratic curve
          // Calculate normal vector for control point
          const dx = targetX - sourceX;
          const dy = targetY - sourceY;
          const length = Math.sqrt(dx * dx + dy * dy);
          
          if (length === 0) return `M${sourceX},${sourceY}L${targetX},${targetY}`;
          
          // Calculate perpendicular offset for curve control point
          const offsetX = -dy / length * 30; // Curve offset
          const offsetY = dx / length * 30;  // Curve offset
          
          // Control point position with offset
          const cpX = midX + offsetX;
          const cpY = midY + offsetY;
          
          // Return curved path
          return `M${sourceX},${sourceY} Q${cpX},${cpY} ${targetX},${targetY}`;
        } else {
          // For single direction relationships, use a slight curve
          // Small offset for visual appeal and to prevent overlapping paths
          const dx = targetX - sourceX;
          const dy = targetY - sourceY;
          const length = Math.sqrt(dx * dx + dy * dy);
          
          if (length === 0) return `M${sourceX},${sourceY}L${targetX},${targetY}`;
          
          // Small perpendicular offset
          const offsetX = -dy / length * 10;
          const offsetY = dx / length * 10;
          
          // Control point with small offset
          const cpX = midX + offsetX;
          const cpY = midY + offsetY;
          
          // Return slightly curved path
          return `M${sourceX},${sourceY} Q${cpX},${cpY} ${targetX},${targetY}`;
        }
      });

      // Update node positions
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    // Functions for drag behavior
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event, d) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Stop simulation after initial layout
    setTimeout(() => {
      simulation.stop();
    }, 2000);

  }, [tags, selectedTagId, width, height, onTagSelect]);

  return (
    <div className="tag-hierarchy-graph">
      <svg ref={svgRef}></svg>
      {tooltip.visible && (
        <div 
          className="tooltip" 
          style={{
            position: 'absolute',
            top: tooltip.y + 10 + 'px',
            left: tooltip.x + 10 + 'px',
            background: 'white',
            border: '1px solid #ddd',
            borderRadius: '4px',
            padding: '8px',
            pointerEvents: 'none',
            zIndex: 100,
            maxWidth: '200px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.1)'
          }}
        >
          {tooltip.content}
        </div>
      )}
    </div>
  );
};

export default TagHierarchyGraph;
