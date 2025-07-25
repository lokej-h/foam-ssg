#!/usr/bin/env python3
"""
Foam-style Static Site Generator
A Python-based static site generator with graph visualization, search, and diagram support.
"""

import os
import re
import json
import shutil
import argparse
import subprocess
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import markdown
from markdown.extensions import fenced_code
import frontmatter
from jinja2 import Environment, FileSystemLoader
import networkx as nx
from bs4 import BeautifulSoup

class FoamSSG:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.notes = {}
        self.graph = nx.DiGraph()
        self.backlinks = defaultdict(list)
        self.md = markdown.Markdown(extensions=[
            'fenced_code',
            'tables',
            'toc',
            'meta',
            'codehilite'
        ])
        
    def build(self):
        """Main build process"""
        print("🚀 Starting Foam SSG build...")
        
        # Clean output directory
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)
        self.output_dir.mkdir(parents=True)
        
        # Process all markdown files
        self.process_notes()
        
        # Generate site
        self.generate_html()
        self.generate_search_index()
        self.copy_assets()
        
        print("✅ Build complete!")
        
    def process_notes(self):
        """Process all markdown files and build graph"""
        # First pass: Load all notes without processing wiki links
        for md_file in self.input_dir.rglob("*.md"):
            relative_path = md_file.relative_to(self.input_dir)
            note_id = str(relative_path.with_suffix(''))
            
            # Read frontmatter and content
            with open(md_file, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
            
            # Extract links but don't process wiki links yet
            content = post.content
            links = self.extract_links(content)
            
            # Store note data with raw content
            self.notes[note_id] = {
                'id': note_id,
                'title': post.get('title', md_file.stem),
                'content': content,
                'html': '',  # Will be populated in second pass
                'metadata': post.metadata,
                'links': links,
                'backlinks': [],
                'path': str(relative_path),
                'url': f"{note_id}.html"
            }
            
            # Add to graph
            self.graph.add_node(note_id)
            for link in links:
                self.graph.add_edge(note_id, link)
                self.backlinks[link].append(note_id)
        
        # Second pass: Process wiki links and generate HTML now that all notes are loaded
        for note_id, note in self.notes.items():
            html_content = self.process_markdown(note['content'], note_id)
            note['html'] = html_content
        
        # Update backlinks
        for note_id, note in self.notes.items():
            note['backlinks'] = self.backlinks.get(note_id, [])
    
    def extract_links(self, content):
        """Extract wiki-style links from content"""
        # Match [[link]] and [[link|alias]] patterns
        wiki_link_pattern = r'\[\[([^\]]+)\]\]'
        links = []
        
        for match in re.finditer(wiki_link_pattern, content):
            link = match.group(1).strip()
            
            # Handle pipe syntax for aliases
            if '|' in link:
                link = link.split('|', 1)[0].strip()
            
            # Handle title#heading syntax - extract just the title part for graph links
            if '#' in link:
                link = link.split('#', 1)[0].strip()
            
            # Normalize link (remove .md extension if present)
            if link.endswith('.md'):
                link = link[:-3]
            links.append(link)
        
        return list(set(links))  # Remove duplicates
    
    def remove_link_reference_sections(self, content):
        """Remove [//begin] and [//end] sections used for other parsers"""
        lines = content.split('\n')
        result_lines = []
        inside_reference_section = False
        
        for line in lines:
            # Check if this line starts a reference section
            if line.strip().startswith('[//begin]'):
                inside_reference_section = True
                continue  # Skip this line
            
            # Check if this line ends a reference section
            if line.strip().startswith('[//end]'):
                inside_reference_section = False
                continue  # Skip this line
            
            # If we're not inside a reference section, keep the line
            if not inside_reference_section:
                result_lines.append(line)
        
        return '\n'.join(result_lines).strip()
    
    def process_markdown(self, content, note_id):
        """Process markdown with special handling for diagrams and links"""
        # Remove [//begin] and [//end] sections for markdown compatibility
        content = self.remove_link_reference_sections(content)
        
        # Process wiki links
        content = self.process_wiki_links(content, note_id)
        
        # Process diagrams
        content = self.process_diagrams(content, note_id)
        
        # Convert to HTML
        html = self.md.convert(content)
        
        return html
    
    def process_wiki_links(self, content, current_note_id):
        """Convert wiki links to HTML links"""
        def replace_link(match):
            full_match = match.group(0)
            link = match.group(1).strip()
            alias = None
            anchor = None
            
            # Handle pipe syntax for aliases
            if '|' in link:
                parts = link.split('|', 1)
                link = parts[0].strip()
                alias = parts[1].strip()
            
            # Handle title#heading syntax
            if '#' in link:
                link_parts = link.split('#', 1)
                link = link_parts[0].strip()
                anchor = link_parts[1].strip()
            
            if not alias:
                alias = full_match[2:-2]  # Use original text as alias
            
            # Normalize link
            if link.endswith('.md'):
                link = link[:-3]
            
            # Check if target exists
            if link in self.notes:
                # Calculate relative path from current note to target
                relative_path = self.get_relative_path(current_note_id, link)
                # Add anchor if present
                if anchor:
                    # Convert heading to URL-friendly anchor
                    anchor_id = anchor.lower().replace(' ', '-').replace('/', '').replace('\\', '')
                    # Remove non-alphanumeric characters except hyphens and underscores
                    anchor_id = re.sub(r'[^a-zA-Z0-9\-_]', '', anchor_id)
                    relative_path += f'#{anchor_id}'
                return f'<a href="{relative_path}" class="wiki-link">{alias}</a>'
            else:
                return f'<span class="wiki-link broken" title="Note not found: {link}">{alias}</span>'
        
        # Match [[link]] and [[link|alias]] patterns
        wiki_link_pattern = r'\[\[([^\]]+)\]\]'
        return re.sub(wiki_link_pattern, replace_link, content)
    
    def get_relative_path(self, from_note_id, to_note_id):
        """Calculate relative path from one note to another"""
        from pathlib import Path
        
        # Convert note IDs to paths
        from_path = Path(from_note_id + '.html')
        to_path = Path(to_note_id + '.html')
        
        # Calculate relative path
        try:
            # Get the relative path from from_path to to_path
            relative_path = Path('..') / to_path if from_path.parent != Path('.') else to_path
            
            # Handle different directory levels
            from_parts = from_path.parts[:-1]  # Exclude filename
            to_parts = to_path.parts[:-1]      # Exclude filename
            
            # Count how many levels to go up
            up_levels = len(from_parts)
            
            # Build the relative path
            if up_levels == 0:
                # Both in root
                return str(to_path)
            else:
                # Need to go up and then down
                up_dirs = '../' * up_levels
                return f"{up_dirs}{to_note_id}.html"
                
        except Exception:
            # Fallback to absolute-style path
            return f"{to_note_id}.html"
    
    def get_relative_diagram_path(self, from_note_id, img_filename):
        """Calculate relative path from a note to a diagram image"""
        from pathlib import Path
        
        # Convert note ID to path
        from_path = Path(from_note_id + '.html')
        
        # Calculate relative path from note to diagrams directory
        try:
            # Calculate the path from the note's location to the root diagrams directory
            # For projects/foam-ssg.html -> ../diagrams/...
            # For index.html -> diagrams/...
            from_dir = from_path.parent
            
            # Build the relative path by going up the necessary levels
            if from_dir == Path('.'):
                # Note is in root directory
                return f"diagrams/{img_filename}"
            else:
                # Note is in a subdirectory, need to go up to root
                levels_up = len(from_dir.parts)
                up_path = '../' * levels_up
                return f"{up_path}diagrams/{img_filename}"
        
        except Exception:
            # Fallback to absolute-style path
            return f"diagrams/{img_filename}"
    
    def process_diagrams(self, content, note_id):
        """Process Mermaid and PlantUML diagrams"""
        # Process Mermaid
        mermaid_pattern = r'```mermaid\n(.*?)\n```'
        content = re.sub(mermaid_pattern, self.render_mermaid, content, flags=re.DOTALL)
        
        # Process PlantUML
        plantuml_pattern = r'```plantuml\s*\n(.*?)\n```'
        content = re.sub(plantuml_pattern, lambda m: self.render_plantuml(m, note_id), content, flags=re.DOTALL)
        
        return content
    
    def render_mermaid(self, match):
        """Render Mermaid diagrams (client-side)"""
        diagram_code = match.group(1)
        return f'<div class="mermaid">\n{diagram_code}\n</div>'
    
    def render_plantuml(self, match, note_id):
        """Render PlantUML diagrams (pre-rendered at build time)"""
        diagram_code = match.group(1)
        
        # Create diagrams directory
        diagrams_dir = self.output_dir / 'diagrams'
        diagrams_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename including theme version to force regeneration
        theme_version = "dark_v5"  # Increment when theme changes
        combined_content = f"{diagram_code}_{theme_version}"
        diagram_hash = hashlib.md5(combined_content.encode()).hexdigest()
        img_filename = f'plantuml_{note_id}_{diagram_hash}.png'
        img_path = diagrams_dir / img_filename
        
        # Try to render with PlantUML if available
        try:
            # Write PlantUML code to temp file with dark theme
            # Add comprehensive dark theme directives to match CSS styles
            dark_theme_code = f'''@startuml
skinparam backgroundColor #1e1e1e
skinparam defaultTextColor #d4d4d4
skinparam shadowing false

' Class diagrams
skinparam classBackgroundColor #252526
skinparam classBorderColor #3e3e42
skinparam classArrowColor #d4d4d4
skinparam classHeaderBackgroundColor #2d2d30
skinparam classAttributeIconSize 0
skinparam classAttributeFontColor #d4d4d4
skinparam classStereotypeFontColor #cccccc

' Sequence diagrams
skinparam sequenceParticipantBackgroundColor #252526
skinparam sequenceParticipantBorderColor #3e3e42
skinparam sequenceLifeLineBackgroundColor #1e1e1e
skinparam sequenceLifeLineBorderColor #3e3e42
skinparam sequenceArrowColor #d4d4d4
skinparam sequenceGroupBackgroundColor #2d2d30
skinparam sequenceGroupBorderColor #3e3e42
skinparam sequenceBoxBackgroundColor #252526
skinparam sequenceBoxBorderColor #3e3e42

' Activity diagrams
skinparam activityBackgroundColor #252526
skinparam activityBorderColor #3e3e42
skinparam activityArrowColor #d4d4d4
skinparam activityStartColor #007acc
skinparam activityEndColor #f48771
skinparam activityBarColor #3e3e42
skinparam activityDiamondBackgroundColor #2d2d30
skinparam activityDiamondBorderColor #3e3e42

' Use case diagrams
skinparam usecaseBackgroundColor #252526
skinparam usecaseBorderColor #3e3e42
skinparam actorBackgroundColor #252526
skinparam actorBorderColor #3e3e42

' State diagrams
skinparam stateBackgroundColor #252526
skinparam stateBorderColor #3e3e42
skinparam stateArrowColor #d4d4d4
skinparam stateStartColor #007acc
skinparam stateEndColor #f48771

' Component diagrams
skinparam componentBackgroundColor #252526
skinparam componentBorderColor #3e3e42
skinparam componentArrowColor #d4d4d4
skinparam interfaceBackgroundColor #2d2d30
skinparam interfaceBorderColor #3e3e42

' Package diagrams
skinparam packageBackgroundColor #252526
skinparam packageBorderColor #3e3e42

' Notes and text
skinparam noteBackgroundColor #3c3c3c
skinparam noteBorderColor #3e3e42
skinparam noteFontColor #d4d4d4
skinparam titleFontColor #cccccc
skinparam footerFontColor #cccccc
skinparam headerFontColor #cccccc

' Objects
skinparam objectBackgroundColor #252526
skinparam objectBorderColor #3e3e42
skinparam objectArrowColor #d4d4d4

' Rectangles and other shapes
skinparam rectangleBackgroundColor #252526
skinparam rectangleBorderColor #3e3e42
skinparam circleBackgroundColor #252526
skinparam circleBorderColor #3e3e42

' Stereotypes
skinparam stereotypeCBackgroundColor #2d2d30
skinparam stereotypeABackgroundColor #2d2d30
skinparam stereotypeIBackgroundColor #2d2d30
skinparam stereotypeEBackgroundColor #2d2d30

{diagram_code}
@enduml'''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False) as temp_file:
                temp_file.write(dark_theme_code)
                temp_file.flush()  # Ensure content is written
                temp_filename = temp_file.name
            
            # Run PlantUML (try different common commands)
            import os
            env = os.environ.copy()
            
            for cmd in ['plantuml', 'java -jar plantuml.jar']:
                try:
                    result = subprocess.run(
                        f'{cmd} -tpng -o "{diagrams_dir.absolute()}" "{temp_filename}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        env=env
                    )
                    if result.returncode == 0:
                        break
                except Exception as e:
                    continue
            
            # Check if image was generated (PlantUML generates with temp filename in output directory)
            generated_img = diagrams_dir / f'{Path(temp_filename).stem}.png'
            if generated_img.exists():
                # Ensure the parent directory exists for the target path
                img_path.parent.mkdir(parents=True, exist_ok=True)
                # Rename to our desired filename
                generated_img.rename(img_path)
                # Clean up temp file
                Path(temp_filename).unlink(missing_ok=True)
                # Calculate relative path to diagrams directory from current note
                relative_img_path = self.get_relative_diagram_path(note_id, img_filename)
                return f'<img src="{relative_img_path}" alt="PlantUML diagram" class="plantuml-diagram">'
                
            # Clean up temp file
            Path(temp_filename).unlink(missing_ok=True)
            
        except Exception as e:
            print(f"Warning: Could not render PlantUML diagram: {e}")
        
        # Fallback: render as code block with note to install PlantUML
        return f'''<div class="plantuml-fallback">
<p><em>PlantUML diagram (install PlantUML to see rendered image):</em></p>
<pre><code class="language-plantuml">{diagram_code}</code></pre>
</div>'''
    
    def generate_html(self):
        """Generate HTML files for all notes"""
        # Create template
        template = self.create_template()
        
        # Generate individual note pages
        for note_id, note in self.notes.items():
            output_path = self.output_dir / f"{note_id}.html"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Get graph data with relative URLs for this specific page
            graph_data = self.get_graph_data_for_page(note_id)
            
            # Generate relative URLs for all notes from this page
            link_urls = {}
            for other_note_id in self.notes:
                link_urls[other_note_id] = self.get_relative_path(note_id, other_note_id)
            
            # Render template with graph data specific to current page
            html = template.render(
                note=note,
                all_notes=self.notes,
                graph_data=json.dumps(graph_data),
                current_note_id=note_id,
                search_data=json.dumps(self.get_search_data_for_page(note_id)),
                file_tree_data=json.dumps(self.get_file_tree_data(note_id)),
                link_urls=link_urls,
                is_index=False
            )
            
            output_path.write_text(html)
        
        # Generate index page
        self.generate_index_page(template)
    
    def get_graph_data_for_page(self, current_note_id):
        """Get graph data with relative URLs for a specific page"""
        nodes = []
        edges = []
        
        # Add all nodes with relative URLs from current page
        for note_id, note in self.notes.items():
            relative_url = self.get_relative_path(current_note_id, note_id)
            nodes.append({
                'id': note_id,
                'label': note['title'],
                'url': relative_url
            })
        
        # Add all edges
        edge_set = set()  # To avoid duplicates
        for note_id, note in self.notes.items():
            for link in note['links']:
                if link in self.notes:
                    edge_key = (note_id, link)
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({'source': note_id, 'target': link})
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_full_graph_data(self):
        """Get complete graph data with all nodes (for index page)"""
        nodes = []
        edges = []
        
        # Add all nodes (for index page, use direct URLs)
        for note_id, note in self.notes.items():
            nodes.append({
                'id': note_id,
                'label': note['title'],
                'url': note['url']
            })
        
        # Add all edges
        edge_set = set()  # To avoid duplicates
        for note_id, note in self.notes.items():
            for link in note['links']:
                if link in self.notes:
                    edge_key = (note_id, link)
                    if edge_key not in edge_set:
                        edge_set.add(edge_key)
                        edges.append({'source': note_id, 'target': link})
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_search_data(self):
        """Prepare search index data"""
        search_data = []
        for note_id, note in self.notes.items():
            search_data.append({
                'id': note_id,
                'title': note['title'],
                'content': note['content'][:500],  # First 500 chars for preview
                'url': note['url']
            })
        return search_data
    
    def get_search_data_for_page(self, current_note_id):
        """Prepare search index data with relative URLs for a specific page"""
        search_data = []
        for note_id, note in self.notes.items():
            relative_url = self.get_relative_path(current_note_id, note_id)
            search_data.append({
                'id': note_id,
                'title': note['title'],
                'content': note['content'][:500],  # First 500 chars for preview
                'url': relative_url
            })
        return search_data
    
    def generate_file_tree(self, current_note_id=None):
        """Generate hierarchical file tree structure"""
        tree = {}
        
        # Build tree structure from file paths
        for note_id, note in self.notes.items():
            path_parts = Path(note['path']).parts
            current_level = tree
            
            # Navigate/create the tree structure
            for i, part in enumerate(path_parts):
                if i == len(path_parts) - 1:
                    # This is the file
                    if part not in current_level:
                        current_level[part] = {
                            'type': 'file',
                            'note_id': note_id,
                            'title': note['title'],
                            'url': self.get_relative_path(current_note_id, note_id) if current_note_id else note['url']
                        }
                else:
                    # This is a directory
                    if part not in current_level:
                        current_level[part] = {
                            'type': 'directory',
                            'children': {}
                        }
                    current_level = current_level[part]['children']
        
        return tree
    
    def get_file_tree_data(self, current_note_id=None):
        """Get file tree data for template rendering"""
        return self.generate_file_tree(current_note_id)
    
    def generate_search_index(self):
        """Generate search index file"""
        search_index = {
            'notes': self.get_search_data()
        }
        
        index_path = self.output_dir / 'search-index.json'
        index_path.write_text(json.dumps(search_index))
    
    def generate_index_page(self, template):
        """Generate main index page"""
        # Get full graph data
        graph_data = self.get_full_graph_data()
        
        html = template.render(
            is_index=True,
            notes=self.notes,
            graph_data=json.dumps(graph_data),
            current_note_id=None,
            search_data=json.dumps(self.get_search_data()),
            file_tree_data=json.dumps(self.get_file_tree_data())
        )
        
        (self.output_dir / 'index.html').write_text(html)
    
    def create_template(self):
        """Create HTML template"""
        template_str = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% if is_index %}Foam Notes{% else %}{{ note.title }} - Foam Notes{% endif %}</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1e1e1e; color: #d4d4d4; }
        
        .container { display: flex; height: 100vh; }
        
        /* Sidebar */
        .sidebar { 
            width: 300px; 
            background: #252526; 
            border-right: 1px solid #3e3e42; 
            display: flex; 
            flex-direction: column; 
            position: relative;
            min-width: 200px;
            max-width: 600px;
            transition: width 0.3s ease;
        }
        
        .sidebar.resizing {
            transition: none; /* Disable transition during manual resize */
        }
        
        /* Collapse functionality removed for desktop */
        
        .sidebar-header {
            display: none; /* Hidden on desktop */
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: #2d2d30;
            border-bottom: 1px solid #3e3e42;
        }
        
        .sidebar-title {
            font-weight: bold;
            color: #cccccc;
            font-size: 14px;
        }
        
        .sidebar-toggle-btn {
            background: none;
            border: none;
            color: #cccccc;
            cursor: pointer;
            font-size: 16px;
            padding: 4px;
            border-radius: 3px;
            transition: background-color 0.2s ease;
        }
        
        .sidebar-toggle-btn:hover {
            background-color: #3e3e42;
        }
        
        .sidebar-resizer {
            position: absolute;
            top: 0;
            right: 0;
            width: 4px;
            height: 100%;
            background: transparent;
            cursor: col-resize;
            transition: background-color 0.2s ease;
        }
        
        .sidebar-resizer:hover {
            background-color: #007acc;
        }
        
        /* Collapse resizer styles removed for desktop */
        .sidebar-tabs { display: flex; background: #2d2d30; transition: opacity 0.3s ease; }
        .sidebar-tab { flex: 1; padding: 10px; text-align: center; cursor: pointer; border-bottom: 2px solid transparent; font-size: 12px; }
        .sidebar-tab.active { border-bottom-color: #007acc; }
        .sidebar-content { flex: 1; overflow-y: auto; padding: 20px; transition: opacity 0.3s ease; }
        
        /* Collapse styles removed for desktop */
        
        /* Graph */
        #graph { width: 100%; height: 400px; background: #1e1e1e; position: relative; border-radius: 4px; overflow: hidden; }
        .graph-node { cursor: pointer; }
        .graph-node:hover { stroke-width: 3px !important; }
        .graph-link { stroke: #666; stroke-opacity: 0.6; }
        .graph-controls { display: flex; gap: 5px; }
        .graph-controls button { 
            background: #3c3c3c; 
            border: 1px solid #555; 
            color: #d4d4d4; 
            padding: 5px 10px; 
            cursor: pointer; 
            border-radius: 3px;
            font-size: 12px;
        }
        .graph-controls button:hover { background: #484848; }
        
        /* Search */
        .search-box { width: 100%; padding: 10px; background: #3c3c3c; border: 1px solid #3e3e42; color: #d4d4d4; margin-bottom: 20px; }
        .search-results { list-style: none; }
        .search-result { padding: 10px; cursor: pointer; border-bottom: 1px solid #3e3e42; }
        .search-result:hover { background: #2a2d2e; }
        
        /* Links */
        .links-section { margin-bottom: 30px; }
        .links-section h3 { margin-bottom: 10px; color: #cccccc; }
        .link-list { list-style: none; }
        .link-item { padding: 8px 0; }
        .link-item a { color: #3794ff; text-decoration: none; }
        .link-item a:hover { text-decoration: underline; }
        
        /* File Tree */
        .file-tree { font-family: 'Courier New', monospace; font-size: 13px; }
        .file-tree-item { 
            padding: 2px 0; 
            cursor: pointer; 
            white-space: nowrap; 
            overflow: hidden; 
            text-overflow: ellipsis;
        }
        .file-tree-item:hover { background: #2a2d2e; }
        .file-tree-folder { 
            color: #cccccc; 
            font-weight: bold; 
            padding: 4px 0; 
            cursor: pointer;
        }
        .file-tree-folder:hover { background: #2a2d2e; }
        .file-tree-folder .folder-icon { 
            display: inline-block; 
            width: 16px; 
            margin-right: 4px;
            transition: transform 0.2s ease;
        }
        .file-tree-folder.expanded .folder-icon { transform: rotate(90deg); }
        .file-tree-file { 
            color: #d4d4d4; 
            padding-left: 20px; 
            text-decoration: none; 
            display: block;
        }
        .file-tree-file:hover { color: #3794ff; }
        .file-tree-children { 
            margin-left: 16px; 
            border-left: 1px solid #3e3e42; 
            padding-left: 8px; 
            display: none;
        }
        .file-tree-children.expanded { display: block; }
        
        /* Main content */
        .main-content { flex: 1; overflow-y: auto; padding: 40px; }
        .note-content { max-width: 800px; margin: 0 auto; }
        .note-content h1 { margin-bottom: 30px; }
        .note-content h2 { margin: 30px 0 15px; }
        .note-content p { margin-bottom: 15px; line-height: 1.6; }
        .note-content code { background: #3c3c3c; padding: 2px 4px; border-radius: 3px; }
        .note-content pre { background: #1e1e1e; border: 1px solid #3e3e42; padding: 15px; margin: 15px 0; overflow-x: auto; }
        
        /* List styling for proper indentation */
        .note-content ul, .note-content ol { margin: 10px 0; padding-left: 20px; }
        .note-content ul ul, .note-content ol ol, .note-content ul ol, .note-content ol ul { margin: 5px 0; }
        .note-content li { margin: 5px 0; line-height: 1.6; }
        
        /* Wiki links */
        .wiki-link { color: #3794ff; text-decoration: none; }
        .wiki-link:hover { text-decoration: underline; }
        .wiki-link.broken { color: #f48771; text-decoration: line-through; }
        
        /* Diagrams */
        .mermaid { margin: 20px 0; text-align: center; }
        .plantuml-diagram { max-width: 100%; margin: 20px auto; display: block; }
        
        /* Mobile Toggle Button */
        .sidebar-toggle { 
            display: none; 
            position: fixed; 
            top: 20px; 
            left: 20px; 
            z-index: 1000; 
            background: #007acc; 
            color: white; 
            border: none; 
            padding: 10px; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px;
        }
        
        /* Overlay for mobile */
        .sidebar-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 998;
        }
        
        /* Mobile Styles */
        @media (max-width: 768px) {
            .sidebar-toggle { display: block; }
            
            .sidebar {
                position: fixed;
                top: 0;
                left: 0;
                height: 100vh;
                z-index: 999;
                transform: translateX(-100%);
                transition: transform 0.3s ease;
                box-shadow: 2px 0 10px rgba(0,0,0,0.5);
                width: 300px !important; /* Override any resize width on mobile */
            }
            
            .sidebar.open {
                transform: translateX(0);
            }
            
            /* Mobile collapse handled by transform instead of width */
            
            .sidebar-overlay.active {
                display: block;
            }
            
            .main-content {
                width: 100%;
                padding: 80px 20px 20px 20px;
            }
            
            .note-content h1 { font-size: 2em; }
            .note-content h2 { font-size: 1.5em; }
            .note-content h3 { font-size: 1.2em; }
            
            #graph { height: 300px; }
            
            .sidebar-content { padding: 15px; }
            
            .sidebar-resizer { display: none; } /* Hide resizer on mobile */
            
            .sidebar-header { display: flex; } /* Show header on mobile for collapse button */
        }
    </style>
</head>
<body>
    <button class="sidebar-toggle" onclick="toggleSidebar()">☰</button>
    <div class="sidebar-overlay" onclick="closeSidebar()"></div>
    
    <div class="container">
        <div class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-title">Navigation</div>
                <button class="sidebar-toggle-btn" onclick="toggleSidebarCollapse()" title="Toggle sidebar">
                    <span id="sidebar-toggle-icon">‹</span>
                </button>
            </div>
            
            <div class="sidebar-tabs">
                <div class="sidebar-tab active" onclick="showTab('graph')">Graph</div>
                <div class="sidebar-tab" onclick="showTab('search')">Search</div>
                <div class="sidebar-tab" onclick="showTab('files')">Files</div>
                <div class="sidebar-tab" onclick="showTab('links')">Links</div>
            </div>
            
            <div class="sidebar-resizer" id="sidebar-resizer"></div>
            
            <div class="sidebar-content">
                <div id="graph-tab" class="tab-content">
                    <div id="graph"></div>
                    <div id="graph-info"></div>
                </div>
                
                <div id="search-tab" class="tab-content" style="display: none;">
                    <input type="text" class="search-box" placeholder="Search notes..." id="search-input">
                    <ul class="search-results" id="search-results"></ul>
                </div>
                
                <div id="files-tab" class="tab-content" style="display: none;">
                    <div id="file-tree" class="file-tree"></div>
                </div>
                
                <div id="links-tab" class="tab-content" style="display: none;">
                    {% if not is_index %}
                    <div class="links-section">
                        <h3>Outgoing Links ({{ note.links|length }})</h3>
                        <ul class="link-list">
                            {% for link in note.links %}
                                {% if link in all_notes %}
                                <li class="link-item">
                                    <a href="{{ link_urls[link] }}">{{ all_notes[link].title }}</a>
                                </li>
                                {% endif %}
                            {% endfor %}
                        </ul>
                    </div>
                    
                    <div class="links-section">
                        <h3>Incoming Links ({{ note.backlinks|length }})</h3>
                        <ul class="link-list">
                            {% for backlink in note.backlinks %}
                                {% if backlink in all_notes %}
                                <li class="link-item">
                                    <a href="{{ link_urls[backlink] }}">{{ all_notes[backlink].title }}</a>
                                </li>
                                {% endif %}
                            {% endfor %}
                        </ul>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <div class="main-content">
            {% if is_index %}
                <div class="note-content">
                    <h1>Foam Notes</h1>
                    <p>Welcome to your Foam knowledge base. Select a note from the graph or search to get started.</p>
                    
                    <h2>All Notes</h2>
                    <ul>
                        {% for note_id, note in notes.items() %}
                        <li><a href="{{ note.url }}">{{ note.title }}</a></li>
                        {% endfor %}
                    </ul>
                </div>
            {% else %}
                <div class="note-content">
                    {{ note.html|safe }}
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        // Initialize Mermaid
        mermaid.initialize({ theme: 'dark', startOnLoad: true });
        
        // Tab switching
        function showTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            document.querySelectorAll('.sidebar-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            document.getElementById(tabName + '-tab').style.display = 'block';
            event.target.classList.add('active');
        }
        
        // Graph visualization
        const graphData = {{ graph_data|safe }};
        const currentNoteId = {% if is_index %}null{% else %}"{{ current_note_id }}"{% endif %};
        
        // Get dynamic dimensions
        function getGraphDimensions() {
            const graphContainer = document.getElementById('graph');
            const containerRect = graphContainer.getBoundingClientRect();
            return {
                width: containerRect.width - 20, // Account for padding
                height: 380 // Keep height fixed for now
            };
        }
        
        let { width, height } = getGraphDimensions();
        
        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        // Add zoom behavior
        const g = svg.append("g");
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });
        svg.call(zoom);
        
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.edges).id(d => d.id).distance(50))
            .force("charge", d3.forceManyBody().strength(-150))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(25))
            .force("x", d3.forceX(width / 2).strength(0.02))
            .force("y", d3.forceY(height / 2).strength(0.02));
        
        const link = g.append("g")
            .selectAll("line")
            .data(graphData.edges)
            .enter().append("line")
            .attr("class", "graph-link")
            .attr("stroke-width", 1);
        
        const node = g.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("r", d => d.id === currentNoteId ? 8 : 5)
            .attr("fill", d => {
                if (d.id === currentNoteId) return "#007acc";
                // Color connected nodes differently
                const isConnected = graphData.edges.some(e => 
                    (e.source.id || e.source) === currentNoteId && (e.target.id || e.target) === d.id ||
                    (e.target.id || e.target) === currentNoteId && (e.source.id || e.source) === d.id
                );
                return isConnected ? "#4CAF50" : "#cccccc";
            })
            .attr("class", "graph-node")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .on("click", (event, d) => {
                window.location.href = d.url;
            })
            .on("mouseover", function(event, d) {
                // Show tooltip
                const tooltip = d3.select("body").append("div")
                    .attr("class", "graph-tooltip")
                    .style("position", "absolute")
                    .style("background", "#333")
                    .style("color", "#fff")
                    .style("padding", "5px 10px")
                    .style("border-radius", "3px")
                    .style("font-size", "12px")
                    .style("pointer-events", "none")
                    .text(d.label);
                
                tooltip.style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 10) + "px");
            })
            .on("mouseout", function() {
                d3.selectAll(".graph-tooltip").remove();
            })
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        simulation.on("tick", () => {
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
        });
        
        // Zoom controls
        d3.select("#graph").append("div")
            .attr("class", "graph-controls")
            .style("position", "absolute")
            .style("bottom", "10px")
            .style("right", "10px")
            .html(`
                <button onclick="zoomIn()">+</button>
                <button onclick="zoomOut()">-</button>
                <button onclick="resetZoom()">Reset</button>
            `);
        
        function zoomIn() {
            svg.transition().call(zoom.scaleBy, 1.3);
        }
        
        function zoomOut() {
            svg.transition().call(zoom.scaleBy, 0.7);
        }
        
        function resetZoom() {
            svg.transition().call(zoom.transform, d3.zoomIdentity);
        }
        
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
        
        // Graph resize function
        function resizeGraph() {
            const newDimensions = getGraphDimensions();
            width = newDimensions.width;
            height = newDimensions.height;
            
            // Update SVG dimensions
            svg.attr("width", width).attr("height", height);
            
            // Update simulation center force
            simulation.force("center", d3.forceCenter(width / 2, height / 2));
            
            // Restart simulation with new dimensions
            simulation.alpha(0.3).restart();
        }
        
        // Search functionality
        const searchData = {{ search_data|safe }};
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');
        
        searchInput?.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            if (query.length < 2) {
                searchResults.innerHTML = '';
                return;
            }
            
            const results = searchData.filter(note => 
                note.title.toLowerCase().includes(query) || 
                note.content.toLowerCase().includes(query)
            );
            
            searchResults.innerHTML = results.slice(0, 10).map(note => `
                <li class="search-result" onclick="window.location.href='${note.url}'">
                    <strong>${note.title}</strong><br>
                    <small>${note.content.substring(0, 100)}...</small>
                </li>
            `).join('');
        });
        
        // File tree functionality
        const fileTreeData = {{ file_tree_data|safe }};
        const fileTreeContainer = document.getElementById('file-tree');
        
        function renderFileTree(tree, container, level = 0) {
            for (const [name, item] of Object.entries(tree)) {
                const element = document.createElement('div');
                element.className = 'file-tree-item';
                
                if (item.type === 'directory') {
                    element.className += ' file-tree-folder';
                    element.innerHTML = `
                        <span class="folder-icon">▶</span>
                        <span class="folder-name">${name}</span>
                    `;
                    
                    const childrenContainer = document.createElement('div');
                    childrenContainer.className = 'file-tree-children';
                    
                    // Add click handler for folder toggle
                    element.addEventListener('click', (e) => {
                        e.stopPropagation();
                        element.classList.toggle('expanded');
                        childrenContainer.classList.toggle('expanded');
                    });
                    
                    // Render children
                    if (item.children && Object.keys(item.children).length > 0) {
                        renderFileTree(item.children, childrenContainer, level + 1);
                    }
                    
                    container.appendChild(element);
                    container.appendChild(childrenContainer);
                } else if (item.type === 'file') {
                    element.innerHTML = `
                        <a href="${item.url}" class="file-tree-file" title="${item.title}">
                            📄 ${item.title}
                        </a>
                    `;
                    container.appendChild(element);
                }
            }
        }
        
        // Initialize file tree
        if (fileTreeContainer && fileTreeData) {
            renderFileTree(fileTreeData, fileTreeContainer);
        }
        
        // Mobile sidebar toggle functionality
        function toggleSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        }
        
        function closeSidebar() {
            const sidebar = document.getElementById('sidebar');
            const overlay = document.querySelector('.sidebar-overlay');
            
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        }
        
        // Close sidebar when clicking on a link (mobile)
        document.querySelectorAll('.sidebar a').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth <= 768) {
                    closeSidebar();
                }
            });
        });
        
        // Mobile sidebar collapse/expand functionality (hidden on desktop)
        function toggleSidebarCollapse() {
            // Only works on mobile - button is hidden on desktop
            if (window.innerWidth <= 768) {
                toggleSidebar();
            }
        }
        
        // Sidebar resizing functionality
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;
        
        const sidebar = document.getElementById('sidebar');
        const resizer = document.getElementById('sidebar-resizer');
        
        resizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(window.getComputedStyle(sidebar).width, 10);
            
            // Disable transition during resize for accurate calculations
            sidebar.classList.add('resizing');
            
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
            
            // Add a class to prevent text selection during resize
            document.body.style.userSelect = 'none';
            document.body.style.cursor = 'col-resize';
        });
        
        function handleMouseMove(e) {
            if (!isResizing) return;
            
            const deltaX = e.clientX - startX;
            const newWidth = startWidth + deltaX;
            
            // Enforce min/max width constraints
            if (newWidth >= 200 && newWidth <= 600) {
                sidebar.style.width = newWidth + 'px';
                // Resize graph immediately since transition is disabled
                resizeGraph();
            }
        }
        
        function handleMouseUp() {
            isResizing = false;
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
            
            // Re-enable transition after resize is complete
            sidebar.classList.remove('resizing');
            
            // Remove the styles added during resize
            document.body.style.userSelect = '';
            document.body.style.cursor = '';
        }
        
        // Keyboard shortcuts removed for desktop collapse
        
        // Handle window resize
        window.addEventListener('resize', () => {
            requestAnimationFrame(resizeGraph);
        });
    </script>
</body>
</html>'''
        
        env = Environment(loader=FileSystemLoader('.'))
        return env.from_string(template_str)
    
    def copy_assets(self):
        """Copy any additional assets"""
        # This is where you'd copy CSS, JS, images, etc.
        pass

def main():
    parser = argparse.ArgumentParser(description='Foam-style Static Site Generator')
    parser.add_argument('input', help='Input directory containing markdown files')
    parser.add_argument('-o', '--output', default='_site', help='Output directory (default: _site)')
    parser.add_argument('--serve', action='store_true', help='Start local server after build')
    
    args = parser.parse_args()
    
    # Build site
    ssg = FoamSSG(args.input, args.output)
    ssg.build()
    
    # Serve if requested
    if args.serve:
        import http.server
        import socketserver
        
        os.chdir(args.output)
        PORT = 8000
        Handler = http.server.SimpleHTTPRequestHandler
        
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"🌐 Serving at http://localhost:{PORT}")
            httpd.serve_forever()

if __name__ == '__main__':
    main()

# Requirements:
# pip install markdown frontmatter jinja2 networkx beautifulsoup4

# Usage:
# python foam_ssg.py /path/to/notes -o /path/to/output
# python foam_ssg.py /path/to/notes --serve  # Build and serve locally