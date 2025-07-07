#!/usr/bin/env python3
"""
Extended Foam SSG with additional features:
- Tag support and filtering
- RSS feed generation  
- Site configuration file
- Syntax highlighting
- Table of contents
"""

import yaml
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from feedgen.feed import FeedGenerator
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
import urllib.parse

# Import base SSG
from foam_ssg import FoamSSG

class ExtendedFoamSSG(FoamSSG):
    def __init__(self, input_dir, output_dir, config_file=None):
        super().__init__(input_dir, output_dir)
        
        # Load configuration
        self.config = self.load_config(config_file)
        
        # Tag index
        self.tags = defaultdict(list)
        
        # Add syntax highlighting support
        self.md.preprocessors.deregister('fenced_code_block')
        self.md.preprocessors.register(
            SyntaxHighlightPreprocessor(self.md), 
            'fenced_code_block', 
            25
        )
    
    def load_config(self, config_file):
        """Load site configuration"""
        default_config = {
            'site_title': 'Foam Notes',
            'site_description': 'A knowledge base built with Foam SSG',
            'site_url': 'http://localhost:8000',
            'author': 'Anonymous',
            'enable_rss': True,
            'enable_tags': True,
            'graph_depth': 2,
            'search_preview_length': 200,
            'theme': {
                'primary_color': '#007acc',
                'background': '#1e1e1e',
                'text_color': '#d4d4d4'
            }
        }
        
        if config_file and Path(config_file).exists():
            with open(config_file, 'r') as f:
                user_config = yaml.safe_load(f)
                default_config.update(user_config)
        
        return default_config
    
    def process_notes(self):
        """Extended note processing with tags"""
        super().process_notes()
        
        # Build tag index
        if self.config['enable_tags']:
            for note_id, note in self.notes.items():
                tags = note['metadata'].get('tags', [])
                if isinstance(tags, str):
                    tags = [tags]
                
                note['tags'] = tags
                for tag in tags:
                    self.tags[tag].append(note_id)
    
    def generate_html(self):
        """Extended HTML generation"""
        super().generate_html()
        
        # Generate tag pages
        if self.config['enable_tags']:
            self.generate_tag_pages()
        
        # Generate RSS feed
        if self.config['enable_rss']:
            self.generate_rss_feed()
        
        # Generate sitemap
        self.generate_sitemap()
    
    def generate_tag_pages(self):
        """Generate pages for each tag"""
        template = self.create_extended_template()
        
        # Generate tag index page
        tags_data = {
            'tags': dict(self.tags),
            'config': self.config
        }
        
        html = template.render(
            is_tag_index=True,
            tags_data=tags_data,
            all_notes=self.notes
        )
        
        (self.output_dir / 'tags.html').write_text(html)
        
        # Generate individual tag pages
        for tag, note_ids in self.tags.items():
            tag_notes = {nid: self.notes[nid] for nid in note_ids}
            
            html = template.render(
                is_tag_page=True,
                tag=tag,
                tag_notes=tag_notes,
                all_notes=self.notes,
                config=self.config
            )
            
            tag_slug = urllib.parse.quote(tag.lower().replace(' ', '-'))
            (self.output_dir / 'tags' / f'{tag_slug}.html').write_text(html)
    
    def generate_rss_feed(self):
        """Generate RSS feed"""
        fg = FeedGenerator()
        fg.title(self.config['site_title'])
        fg.description(self.config['site_description'])
        fg.link(href=self.config['site_url'], rel='alternate')
        fg.language('en')
        
        # Sort notes by date
        sorted_notes = sorted(
            self.notes.items(),
            key=lambda x: x[1]['metadata'].get('date', datetime.min),
            reverse=True
        )
        
        # Add entries
        for note_id, note in sorted_notes[:20]:  # Last 20 notes
            fe = fg.add_entry()
            fe.title(note['title'])
            fe.link(href=f"{self.config['site_url']}/{note['url']}")
            fe.description(note['content'][:500])
            
            if 'date' in note['metadata']:
                fe.published(note['metadata']['date'])
        
        # Write feed
        fg.rss_file(str(self.output_dir / 'feed.xml'))
    
    def generate_sitemap(self):
        """Generate XML sitemap"""
        sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for note_id, note in self.notes.items():
            sitemap += f'''  <url>
    <loc>{self.config['site_url']}/{note['url']}</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>weekly</changefreq>
  </url>\n'''
        
        sitemap += '</urlset>'
        
        (self.output_dir / 'sitemap.xml').write_text(sitemap)
    
    def create_extended_template(self):
        """Create extended template with tag support"""
        # This would be an extended version of the base template
        # with additional features for tags, RSS, etc.
        # For brevity, returning the base template
        return self.create_template()


class SyntaxHighlightPreprocessor:
    """Preprocessor for syntax highlighting"""
    def __init__(self, md):
        self.md = md
    
    def run(self, lines):
        """Process code blocks for syntax highlighting"""
        text = '\n'.join(lines)
        
        # Pattern for fenced code blocks
        import re
        pattern = r'```(\w+)\n(.*?)\n```'
        
        def highlight_code(match):
            lang = match.group(1)
            code = match.group(2)
            
            try:
                lexer = get_lexer_by_name(lang)
                formatter = HtmlFormatter(style='monokai')
                return highlight(code, lexer, formatter)
            except:
                return f'<pre><code class="language-{lang}">{code}</code></pre>'
        
        text = re.sub(pattern, highlight_code, text, flags=re.DOTALL)
        return text.split('\n')


# Configuration file example (config.yaml):
"""
site_title: My Foam Knowledge Base
site_description: Personal notes and thoughts
site_url: https://mynotes.example.com
author: John Doe

enable_rss: true
enable_tags: true

graph_depth: 3
search_preview_length: 250

theme:
  primary_color: '#00a86b'
  background: '#1a1a1a'
  text_color: '#e0e0e0'
  
markdown_extensions:
  - tables
  - footnotes
  - attr_list
  - def_list
"""

# Usage:
# python foam_ssg_extended.py /path/to/notes -c config.yaml