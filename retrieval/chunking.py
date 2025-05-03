"""
Smart document chunking strategies for improved retrieval
"""
import re
from typing import List, Optional, Dict, Any

def adaptive_text_splitter(
    text: str, 
    chunk_size: int = 4000, 
    chunk_overlap: int = 400,
    separator: str = "\n\n"
) -> List[str]:
    """
    Split text with adaptive chunking based on content structure
    
    Args:
        text: Text to split
        chunk_size: Target size of each chunk
        chunk_overlap: Amount of overlap between chunks
        separator: Primary separator for initial splitting
        
    Returns:
        List of text chunks
    """
    # Try to split on paragraph breaks first
    paragraphs = re.split(r'\n\s*\n', text)
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        # If adding this paragraph exceeds chunk size, start a new chunk
        if len(current_chunk) + len(para) > chunk_size - chunk_overlap:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
        else:
            if current_chunk:
                current_chunk += separator + para
            else:
                current_chunk = para
    
    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append(current_chunk)
    
    # Handle overlaps
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if i > 0 and len(chunks[i-1]) > chunk_overlap:
            # Add some content from the previous chunk for context
            prev_end = chunks[i-1][-chunk_overlap:] if len(chunks[i-1]) > chunk_overlap else chunks[i-1]
            chunk = prev_end + separator + chunk
        final_chunks.append(chunk)
    
    return final_chunks

def semantic_chunking(
    text: str,
    chunk_size: int = 4000,
    chunk_overlap: int = 400
) -> List[Dict[str, Any]]:
    """
    Advanced chunking that detects topic changes and keeps related content together
    
    Args:
        text: Text to split
        chunk_size: Target size of each chunk
        chunk_overlap: Amount of overlap between chunks
        
    Returns:
        List of dictionaries with chunk content and metadata
    """
    # Simple heuristic to detect topic changes: look for headings or significant paragraph breaks
    topic_boundary_pattern = r'(?:\n\s*#{1,3}\s+.+)|(?:\n\s*\n\s*\n)'
    
    # Split by potential topic boundaries
    topic_sections = re.split(topic_boundary_pattern, text)
    
    # Extract matched headings/boundaries to preserve them
    boundaries = re.findall(topic_boundary_pattern, text)
    
    # Reconstruct with boundaries
    sections = []
    for i, section in enumerate(topic_sections):
        if i > 0 and i-1 < len(boundaries):
            # Add back the boundary before the section
            sections.append(boundaries[i-1] + section)
        else:
            sections.append(section)
    
    # Process sections for size
    chunks = []
    current_chunk = ""
    current_topics = []
    
    for section in sections:
        # Extract potential topic name (heading)
        section_topic = None
        heading_match = re.match(r'\s*#+\s+(.+)', section)
        if heading_match:
            section_topic = heading_match.group(1).strip()
        
        # If adding this section exceeds chunk size, start a new chunk
        if len(current_chunk) + len(section) > chunk_size:
            if current_chunk:
                chunks.append({
                    "content": current_chunk,
                    "topics": current_topics.copy()
                })
            current_chunk = section
            current_topics = [section_topic] if section_topic else []
        else:
            if current_chunk:
                current_chunk += "\n\n" + section
            else:
                current_chunk = section
            if section_topic and section_topic not in current_topics:
                current_topics.append(section_topic)
    
    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append({
            "content": current_chunk,
            "topics": current_topics.copy()
        })
    
    # Process overlaps
    final_chunks = []
    for i, chunk in enumerate(chunks):
        if i > 0 and len(chunks[i-1]["content"]) > chunk_overlap:
            # Add overlap content
            overlap_content = chunks[i-1]["content"][-chunk_overlap:]
            augmented_content = overlap_content + "\n\n" + chunk["content"]
            
            # Combine topics lists
            combined_topics = list(set(chunks[i-1]["topics"] + chunk["topics"]))
            
            final_chunks.append({
                "content": augmented_content,
                "topics": combined_topics
            })
        else:
            final_chunks.append(chunk)
    
    return final_chunks
