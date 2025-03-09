# Blog Post Generator

A powerful AI-powered blog post generator with chat-style history, real-time cost reporting, and comprehensive blog analysis.

## Features

- **Chat-Style Post History**: View and edit previously generated blog posts
- **Real-Time Cost Reporting**: Monitor API costs as they occur
- **TLDR Summaries**: Automatically generated summaries for each blog post
- **Dynamic Blog Analysis**: Get detailed analysis of your content's structure, accessibility, and empathy
- **Agent Collaboration**: Watch as multiple AI agents work together to create your content
- **Physical File Saving**: Automatically saves posts as both JSON and Markdown files

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_api_key
   ```

## Running Locally

Run the app with:

```bash
streamlit run unified_app.py
```

## Deployment

### Streamlit Cloud Deployment

1. Push your code to a GitHub repository
2. Log in to [Streamlit Cloud](https://streamlit.io/cloud)
3. Create a new app and select your repository
4. Set the main file to `unified_app.py`
5. Add your API keys as secrets in the Streamlit Cloud dashboard
6. Deploy!

### Environment Variables for Deployment

Make sure to set these environment variables in your deployment platform:

- `OPENAI_API_KEY`: Your OpenAI API key

## Directory Structure

- `unified_app.py`: Main application file
- `.streamlit/config.toml`: Streamlit configuration
- `requirements.txt`: Python dependencies
- `generated_posts/`: Directory for saved blog posts
  - `markdown/`: Directory for markdown versions of posts
- `utils/`: Utility functions
- `src/`: Source code for agents and models

## Troubleshooting Deployment

If you encounter issues with deployment:

1. Check that all dependencies are in `requirements.txt`
2. Verify that your API keys are correctly set as environment variables
3. Make sure the `.streamlit/config.toml` file is properly configured

## License

MIT
