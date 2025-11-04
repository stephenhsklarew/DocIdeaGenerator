# Qwilo - Article Idea Generator

An interactive CLI tool that fetches Gemini conversation transcripts from Gmail and analyzes them to generate article content suggestions focused on AI strategy and innovation for business leaders.

## Features

- Fetches transcripts from Gmail with subject pattern: `Notes: "[Subject]" [MMM DD, YYYY]`
- Extracts full transcripts from Google Docs (prefers Transcript tab over Summary)
- Interactive CLI with ASCII art logo and rich terminal UI
- Label-based filtering to focus on specific conversations
- AI-powered content analysis using Claude API
- Generates:
  - Recommended article topics (2-4 topics)
  - Key insights specific to each topic
  - Notable verbatim quotes with speaker attribution
- Save analysis results to markdown files
- Batch processing support

## Prerequisites

- Python 3.8 or higher
- Gmail account
- Anthropic API key
- Google Cloud project with Gmail API, Google Docs API, and Google Drive API enabled

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/stephenhsklarew/article-idea-generator.git
cd article-idea-generator
```

### 2. Install Dependencies

Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

### 3. Set Up Google Cloud APIs

#### Enable Required APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable required APIs:
   - Go to "APIs & Services" > "Library"
   - Search for and enable **"Gmail API"**
   - Search for and enable **"Google Docs API"**
   - Search for and enable **"Google Drive API"**

#### Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "Internal" (if using Google Workspace) or "External"
   - Fill in app name: "Article Idea Generator"
   - Add your email as a developer contact
   - Add scopes: `gmail.readonly`, `drive.readonly`, `documents.readonly`
4. Choose "Desktop app" as application type
5. Download the credentials JSON file
6. **Save it as `credentials.json` in the project root directory**

**Important:** The `credentials.json` file is required for the application to authenticate with Google APIs. This file is automatically excluded from git via `.gitignore` to keep your credentials secure.

### 4. Set Up Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Anthropic API key:
   ```bash
   # Required: Your Anthropic API key
   ANTHROPIC_API_KEY=your_actual_api_key_here

   # Optional: Set a start date to only analyze transcripts from this date forward
   # Format: MMDDYYYY (e.g., 10232025 for October 23, 2025)
   # Leave blank to analyze all transcripts
   START_DATE=

   # Optional: Filter settings
   # Comma-separated list of people to exclude from analysis
   EXCLUDE_PEOPLE=

   # Comma-separated list of subject keywords to exclude
   EXCLUDE_SUBJECTS=
   ```

3. Get your Anthropic API key from [console.anthropic.com](https://console.anthropic.com/)

**Important:** The `.env` file contains sensitive API keys and is automatically excluded from git via `.gitignore`.

### 5. First Run Authentication

On your first run, the application will:
1. Open a browser window to authenticate with Google
2. Ask you to select your Gmail account
3. Request permission to read emails and documents
4. Save the authentication token as `token.pickle` for future use

**Important:** The `token.pickle` file is automatically generated after your first authentication and is excluded from git via `.gitignore`. If you encounter authentication issues, delete this file and re-run the application to re-authenticate.

## File Structure Overview

After setup, your project should have these sensitive files (all excluded from git):

```
article-idea-generator/
├── credentials.json       # Google OAuth credentials (you download)
├── token.pickle          # Google OAuth token (auto-generated on first run)
├── .env                  # Your API keys and config (you create from .env.example)
└── .env.save             # Backup of .env (optional)
```

## Usage

### Basic Usage

Run the interactive CLI:
```bash
python3 cli.py
```

Or make it executable:
```bash
chmod +x cli.py
./cli.py
```

### Command-Line Options

List all available transcripts:
```bash
python3 cli.py --list
```

Analyze a specific email by subject (supports partial matching):
```bash
python3 cli.py --email "Meeting Notes"
```

Filter by Gmail label:
```bash
python3 cli.py --label "blog-potential"
python3 cli.py --list --label "AIQ"
```

Filter by start date:
```bash
python3 cli.py --start-date 10232025
```

Combine filters:
```bash
python3 cli.py --label "blog-potential" --email "Strategy"
```

### Interactive Menu Options

Once the application starts, you'll see:

1. **List of available transcripts** - Shows all emails matching the subject pattern
2. **Analysis options:**
   - Enter a number (e.g., `1`) - Analyze a specific transcript
   - Enter `all` - Analyze all transcripts sequentially
   - Enter `range` (e.g., `1-5`) - Analyze a range of transcripts
   - Enter `q` - Quit the application

3. **After each analysis:**
   - View the results in formatted markdown
   - Choose to save the analysis to a file
   - Continue to the next transcript or return to the menu

### Date Filtering

You can filter transcripts by date in three ways:

**Option 1: Set in .env file**
```
START_DATE=10232025
```

**Option 2: Use command-line argument**
```bash
python3 cli.py --start-date 10232025
```

**Option 3: Interactive prompt**
If no START_DATE is configured and you're not using `--label`, you'll be prompted whether you want to set one.

The date format is `MMDDYYYY`:
- `10232025` = October 23, 2025
- `01152025` = January 15, 2025

**Note:** When using `--label` to filter by Gmail labels, the date filter is automatically disabled to show all emails with that label regardless of date.

### Output Format

Each analysis includes:

```markdown
**Source:** [Original email subject]

## TOPIC 1: [Topic Title]

**Description:** [1-2 sentences on why this would make a good article]

**Key Insights:**
• [Insight 1 related to this topic]
• [Insight 2 related to this topic]
• [Insight 3 related to this topic]

**Notable Quotes:**
> **[Speaker Name]:** "[Exact verbatim quote from transcript]"

> **[Speaker Name]:** "[Another exact quote]"

---

## TOPIC 2: [Topic Title]
...
```

### Saved Files

Analysis files are automatically named:
```
analysis_[topic]_[timestamp].md
```

Example: `analysis_AI_Strategy_Implementation_20251104_143022.md`

## Transcript Tab Detection

The tool intelligently extracts content from Google Docs:

- ✅ **Prefers "Transcript" tab** - Contains full conversation with timestamps and speakers
- ⚠️ **Falls back to "Notes" tab** - If no Transcript tab exists (summary content only)
- 📊 **Reports tab selection** - Shows which tab is being used during processing

For best results with verbatim quotes, use recordings that have a full Transcript tab. The tool will indicate when it's using a summary instead of a full transcript.

## Project Structure

```
article-idea-generator/
├── cli.py                     # Main interactive CLI application
├── gmail_client.py            # Gmail API integration with label filtering
├── google_docs_client.py      # Google Docs API for transcript extraction
├── content_analyzer.py        # Claude API integration for analysis
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules (protects sensitive files)
├── README.md                 # This file
├── qwilo_logo.png            # Application logo
├── credentials.json          # Google OAuth credentials (you provide, not in git)
├── token.pickle             # Google OAuth token (auto-generated, not in git)
└── .env                     # Your environment variables (you create, not in git)
```

## Troubleshooting

### "credentials.json not found"
**Solution:** Download OAuth credentials from Google Cloud Console:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Download your OAuth 2.0 Client ID credentials
4. Save the file as `credentials.json` in the project root directory

### "ANTHROPIC_API_KEY not found"
**Solution:** Create a `.env` file:
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Edit `.env` and add your Anthropic API key
3. Get your API key from [console.anthropic.com](https://console.anthropic.com/)

### "No transcripts found"
**Solution:** Verify that your emails have the correct subject format:
```
Notes: "Your Topic Here" Jan 15, 2025
```
The tool supports both straight quotes (") and curly quotes ("").

### Authentication issues
**Solution:** Delete `token.pickle` and re-run the application:
```bash
rm token.pickle
python3 cli.py
```
This will trigger a new authentication flow.

### Import errors
**Solution:** Ensure you've activated your virtual environment and installed dependencies:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Label filtering returns wrong results
**Solution:**
- Make sure you're using the exact label name from Gmail (case-insensitive)
- Spaces, hyphens, and underscores are normalized (e.g., "blog-potential" matches "Blog Potential")
- The label is filtered at the Gmail API level, not post-processing

### "Cannot provide verbatim quotes" error
**Solution:** This occurs when the document only has a "Notes" (summary) tab instead of a full "Transcript" tab. Select a different transcript that has the full conversation recorded, or use the analysis for insights rather than quotes.

## Tips for Best Results

1. **Choose transcripts with full Transcript tabs** - These contain speaker names and verbatim dialogue
2. **Use label filtering** - Tag important conversations in Gmail with labels like "Blog potential"
3. **Review transcripts before analyzing** - The quality of analysis depends on transcript quality
4. **Save important analyses** - Use the save feature to keep analyses you want to reference
5. **Batch process related topics** - Use the range feature to analyze related conversations together
6. **Refine topics** - The AI suggestions are starting points; use your editorial judgment

## Security Notes

- ✅ Never commit `credentials.json`, `token.pickle`, or `.env` to version control
- ✅ All sensitive files are automatically excluded via `.gitignore`
- ✅ Keep your API keys secure and rotate them periodically
- ✅ The application only reads emails (readonly scope)
- ✅ Authentication tokens are stored locally on your machine

## Support

For issues related to:
- Gmail API: [Google Gmail API Documentation](https://developers.google.com/gmail/api)
- Google Docs API: [Google Docs API Documentation](https://developers.google.com/docs/api)
- Claude API: [Anthropic Documentation](https://docs.anthropic.com/)
- Application bugs: [GitHub Issues](https://github.com/stephenhsklarew/article-idea-generator/issues)

## License

This project is provided as-is for personal use.
