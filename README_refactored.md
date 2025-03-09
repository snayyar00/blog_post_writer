# Blog Post Writer - Refactored

This is a refactored version of the Blog Post Writer application. The original monolithic application has been split into smaller, more manageable modules to improve maintainability and readability.

## Project Structure

The refactored application has the following structure:

```
blog_post_writer/
├── app.py                  # Main application entry point
├── agents/                 # Agent-related functionality
│   ├── __init__.py
│   └── orchestrator.py     # Agent orchestration logic
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── post_manager.py     # Post management (save, load, update)
│   ├── session_manager.py  # Session state management
│   └── ui_components.py    # UI components for Streamlit
├── context/                # Context files for blog generation
├── generated_posts/        # Directory for generated blog posts
│   └── markdown/           # Markdown versions of generated posts
└── src/                    # Original source code (imported by refactored modules)
```

## Modules

### app.py

The main application file that imports and uses all the other modules. It contains the Streamlit UI and the main application logic.

### agents/orchestrator.py

Contains the agent orchestration logic for generating blog posts. It coordinates the different agents involved in the blog post generation process.

### utils/post_manager.py

Handles post management functions such as saving, loading, and updating blog posts.

### utils/session_manager.py

Manages the Streamlit session state, including initialization and updates.

### utils/ui_components.py

Contains UI components for the Streamlit application, such as rendering post cards, displaying blog analysis, and showing agent activities.

## How to Run

To run the refactored application, use the following command:

```bash
streamlit run app.py
```

## Features

- **Auto Mode**: Automatically extracts business context and keywords from context files
- **Manual Mode**: Uses default business context and automatically selects keywords
- **Post History**: View and edit previously generated blog posts
- **Blog Analysis**: Analyze the quality of generated blog posts
- **Agent Activity**: View the activities of different agents involved in the blog post generation process

## Improvements from Refactoring

1. **Modularity**: The code is now split into smaller, more focused modules
2. **Maintainability**: Each module has a single responsibility, making it easier to maintain
3. **Readability**: The code is now more organized and easier to understand
4. **Testability**: Each module can be tested independently
5. **Extensibility**: New features can be added more easily by extending existing modules or adding new ones

## Migration from Original Code

The refactored code maintains all the functionality of the original code but with a more organized structure. If you were using the original code, you can switch to the refactored version by:

1. Running `app.py` instead of `unified_app.py`
2. Updating any imports to point to the new module structure

The refactored code is fully compatible with the original data files and will continue to work with existing context files and generated posts.