---
title: Building a Foam-Style SSG
tags: [projects, web-development]
---

# Building a Foam-Style SSG

This project implements a static site generator inspired by [[tools/foam|Foam]] and [[tools/obsidian|Obsidian]].

## Features

### Graph Visualization

```mermaid
graph TD
    A[Markdown Files] --> B[Parser]
    B --> C[HTML Generator]
    B --> D[Graph Builder]
    C --> E[Static Site]
    D --> E
```

### Architecture

```plantuml
@startuml
class FoamSSG {
    - input_dir: Path
    - output_dir: Path
    - notes: dict
    - graph: DiGraph
    + build()
    + process_notes()
    + generate_html()
}

class Note {
    - id: str
    - title: str
    - content: str
    - links: list
    - backlinks: list
}

FoamSSG "1" -- "*" Note
@enduml
```

## Implementation Details

The system parses [[concepts/markdown]] files, extracts [[concepts/wiki-links]], and builds a graph of connections.

See [[programming/python-tips]] for implementation patterns used.