"""
Functions for exporting comments to different formats.
"""
import json
import csv
import os
import datetime
from pathlib import Path


def get_default_filename(story_id, format_type, include_timestamp=True):
    """
    Generate a default filename for the exported comments.
    
    Args:
        story_id: The ID of the story
        format_type: 'json' or 'csv'
        include_timestamp: Whether to include a timestamp in the filename
        
    Returns:
        A string with the generated filename
    """
    base_name = f"hn_story_{story_id}_comments"
    
    if include_timestamp:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{base_name}_{timestamp}"
        
    return f"{base_name}.{format_type}"


def prepare_comment_for_export(comment, include_children=True, parent_id=None):
    """
    Prepare a comment for export by selecting relevant fields and flattening the structure.
    
    Args:
        comment: The comment object to prepare
        include_children: Whether to include child comments recursively
        parent_id: ID of the parent comment (if any)
        
    Returns:
        Dict with the prepared comment data
    """
    # Basic comment fields we want to preserve
    export_fields = [
        'id', 'text', 'by', 'time', 'deleted', 'dead'
    ]
    
    # Create a new dict with only the fields we want
    export_data = {field: comment.get(field) for field in export_fields if field in comment}
    
    # Add parent_id if it exists
    if parent_id:
        export_data['parent_id'] = parent_id
    
    # If we're including children, process them recursively
    if include_children and 'children' in comment and comment['children']:
        export_data['children'] = []
        for child in comment['children']:
            child_data = prepare_comment_for_export(
                child, 
                include_children=include_children,
                parent_id=comment.get('id')
            )
            export_data['children'].append(child_data)
            
    return export_data


def flatten_comments_for_csv(comments, parent_id=None, flattened_list=None):
    """
    Flatten the nested comment structure into a list for CSV export.
    
    Args:
        comments: List of comment objects with nested children
        parent_id: ID of the parent comment (if any)
        flattened_list: The running list of flattened comments
        
    Returns:
        List of flattened comment dictionaries
    """
    if flattened_list is None:
        flattened_list = []
        
    for comment in comments:
        # Basic comment fields
        flat_comment = {
            'id': comment.get('id'),
            'parent_id': parent_id,
            'by': comment.get('by', 'unknown'),
            'text': comment.get('text', ''),
            'time': comment.get('time', 0),
            'deleted': comment.get('deleted', False),
            'dead': comment.get('dead', False)
        }
        
        # Add to flattened list
        flattened_list.append(flat_comment)
        
        # Process children recursively
        if 'children' in comment and comment['children']:
            flatten_comments_for_csv(
                comment['children'], 
                parent_id=comment.get('id'), 
                flattened_list=flattened_list
            )
            
    return flattened_list


def export_comments_to_json(comments, story_info, output_file=None):
    """
    Export comments to a JSON file.
    
    Args:
        comments: List of comment objects with nested children
        story_info: Dictionary with story information
        output_file: Path to the output file (if None, a default name will be generated)
        
    Returns:
        The path to the created file
    """
    # Prepare story info
    story_id = story_info.get('id', 0)
    
    # Generate default filename if none provided
    if output_file is None:
        output_file = get_default_filename(story_id, 'json')
    
    # Prepare the export data structure
    export_data = {
        'story': {
            'id': story_id,
            'title': story_info.get('title', 'Unknown'),
            'by': story_info.get('by', 'Unknown'),
            'time': story_info.get('time', 0),
            'url': story_info.get('url', ''),
            'score': story_info.get('score', 0),
            'export_time': datetime.datetime.now().isoformat(),
        },
        'comments': []
    }
    
    # Process all comments for export
    for comment in comments:
        export_data['comments'].append(
            prepare_comment_for_export(comment)
        )
    
    # Fix: Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or '.', exist_ok=True)
    
    # Write the data to the JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
        
    return os.path.abspath(output_file)


def export_comments_to_csv(comments, story_info, output_file=None):
    """
    Export comments to a CSV file.
    
    Args:
        comments: List of comment objects with nested children
        story_info: Dictionary with story information
        output_file: Path to the output file (if None, a default name will be generated)
        
    Returns:
        The path to the created file
    """
    # Prepare story info
    story_id = story_info.get('id', 0)
    
    # Generate default filename if none provided
    if output_file is None:
        output_file = get_default_filename(story_id, 'csv')
    
    # Flatten the comment hierarchy for CSV format
    flattened_comments = flatten_comments_for_csv(comments)
    
    # CSV field names
    fieldnames = ['id', 'parent_id', 'by', 'text', 'time', 'deleted', 'dead']
    
    # Fix: Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or '.', exist_ok=True)
    
    # Write to CSV file
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        # First write story info as a special row
        story_row = {
            'id': story_id,
            'parent_id': None,
            'by': story_info.get('by', 'Unknown'),
            'text': f"STORY: {story_info.get('title', 'Unknown')}",
            'time': story_info.get('time', 0),
            'deleted': False,
            'dead': False
        }
        writer.writerow(story_row)
        
        # Then write all the comments
        for comment in flattened_comments:
            writer.writerow(comment)
    
    return os.path.abspath(output_file)