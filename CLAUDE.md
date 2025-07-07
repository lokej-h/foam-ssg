# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based static site generator inspired by Foam, designed to create knowledge bases with graph visualization, full-text search, and bidirectional linking from markdown files.

## Core Commands

### Build Site
```bash
python foam-ssg.py /path/to/notes -o /path/to/output
```

### Build and Serve Locally
```bash
python foam-ssg.py /path/to/notes --serve
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Setup PlantUML (Optional)
```bash
chmod +x plantuml-setup.sh
./plantuml-setup.sh
```

## Architecture

The project is built around the `FoamSSG` class in `foam-ssg.py` with these key components:

### Core Processing Pipeline
1. **Note Processing** (`process_notes`): Parses markdown files with frontmatter, extracts wiki-style links `[[note]]` and `[[note|alias]]`
2. **Graph Building**: Uses NetworkX to create bidirectional link graph
3. **Content Transformation**: Converts markdown to HTML with special handling for diagrams and wiki links
4. **Template Rendering**: Uses Jinja2 to generate HTML pages with embedded D3.js graph visualization

### Key Methods
- `extract_links()`: Parses `[[wiki-link]]` syntax from markdown content
- `process_wiki_links()`: Converts wiki links to HTML, marks broken links
- `process_diagrams()`: Handles Mermaid (client-side) and PlantUML (pre-rendered) diagrams
- `get_full_graph_data()`: Generates complete graph data for D3.js visualization

### Template Architecture
The HTML template includes:
- **Sidebar with 3 tabs**: Graph (D3.js force-directed), Search (client-side), Links (bidirectional)
- **Main content area**: Rendered markdown with processed wiki links
- **Embedded JavaScript**: D3.js for graph, search functionality, Mermaid for diagrams

## File Structure

```
foam-ssg/
├── foam-ssg.py           # Main static site generator
├── foam-ssg-extended.py  # Extended version with additional features
├── requirements.txt      # Python dependencies
├── plantuml-setup.sh    # PlantUML installation script
├── foam-ssg-readme.md   # Full documentation
└── example-notes.md     # Example note structure
```

## Development Notes

- **Dependencies**: markdown, frontmatter, jinja2, networkx, beautifulsoup4, pygments
- **Diagram Support**: Mermaid renders client-side, PlantUML pre-renders at build time as PNG images
- **Link Processing**: Wiki links are bidirectional - `[[target]]` creates both outgoing link from source and backlink to target
- **Search**: Client-side search using JavaScript, index generated at build time
- **Graph Visualization**: D3.js force-directed graph showing all notes, current note highlighted in blue, connected notes in green

## Wiki Link Format

- `[[Note Title]]` - Basic wiki link
- `[[Note Title|Display Text]]` - Wiki link with custom display text
- Links automatically create bidirectional relationships in the graph

## Diagram Support

### Mermaid (Client-side)
```markdown
```mermaid
graph LR
    A[Start] --> B[End]
```
```

### PlantUML (Pre-rendered)
```markdown
```plantuml
@startuml
Alice -> Bob: Hello
@enduml
```
```