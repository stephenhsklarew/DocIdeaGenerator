# DocIdeaGenerator

An interactive CLI tool that fetches Gemini conversation transcripts from Gmail or a Google Drive folder and analyzes them to generate content suggestions. The content focus is fully configurable - by default it targets AI strategy and innovation for business leaders, but can be customized for any domain.

## Features

- **Dual Source Modes** - Fetch content from Gmail emails OR scan Google Drive folders
- **Flexible AI Model Selection:**
  - **Test Mode (default):** Fast and economical with Gemini 1.5 Flash
  - **Production Mode:** High quality with GPT-4o
  - **Custom Models:** Override with any specific AI model (Claude, GPT, Gemini)
  - Supports OpenAI, Anthropic, and Google providers
- **Configurable Content Focus** - Customize the analysis angle for any domain (AI strategy, product management, marketing, DevOps, etc.)
- **Gmail Mode:**
  - Fetches transcripts from Gmail with subject pattern: `Notes: "[Subject]" [MMM DD, YYYY]`
  - Extracts full transcripts from Google Docs (prefers Transcript tab over Summary)
  - Label-based filtering to focus on specific conversations
- **Drive Mode:**
  - Scan any Google Drive folder for transcript documents
  - Recursive subfolder scanning (optional)
  - Date filtering and name pattern matching
- **Smart Output:**
  - **Default:** Saves analysis as Google Docs in configured folder (named MMDDYYYY)
  - **Optional:** Save as local markdown files with `--save-local` flag
  - Automatic folder organization in Google Drive
- Interactive CLI with ASCII art logo and rich terminal UI
- AI-powered content analysis
- Generates:
  - Recommended article topics (2-5 topics per analysis)
  - Compelling topic titles geared to target audience
  - 2-5 key insights specific to each topic
  - 1-3 notable verbatim quotes with speaker attribution
  - Optional evidence/data and statistics when mentioned
  - Optional real-world examples and case studies when shared
- Batch processing support with combined or separate file output

## Prerequisites

- Python 3.8 or higher
- Gmail account
- **AI Provider API key** (choose one):
  - **OpenAI** (default, most cost-effective): Get from [platform.openai.com](https://platform.openai.com/)
  - **Anthropic**: Get from [console.anthropic.com](https://console.anthropic.com/)
  - **Google Gemini** (FREE tier available): Get from [aistudio.google.com](https://aistudio.google.com/)
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

2. Edit `.env` and configure your AI provider:
   ```bash
   # ===== AI PROVIDER CONFIGURATION =====
   # Note: The default mode is TEST (uses Gemini 1.5 Flash - FREE)
   # You can override with --mode or --model command-line arguments

   # Choose: anthropic, openai, or google
   AI_PROVIDER=google

   # Add your API key (only need the one for your chosen provider)
   GOOGLE_API_KEY=your_google_key_here
   # OR
   # OPENAI_API_KEY=your_openai_api_key_here
   # OR
   # ANTHROPIC_API_KEY=your_anthropic_key_here

   # Optional: Override default model (usually not needed)
   # Command-line --mode and --model arguments are recommended instead
   # Defaults: gpt-4o-mini (openai), claude-3-5-haiku (anthropic), gemini-1.5-flash (google)
   # AI_MODEL=gemini-1.5-flash

   # Optional: Content focus for article generation
   # Default: AI strategy and innovation for business leaders
   # Customize this to change the angle/perspective of generated articles
   # Example: CONTENT_FOCUS=product management best practices for SaaS companies
   CONTENT_FOCUS=

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

3. Get your API key from your chosen provider (links above)

**Important:** The `.env` file contains sensitive API keys and is automatically excluded from git via `.gitignore`.

### AI Provider Cost Comparison

For a typical 12K-word transcript analysis:

| Mode | Provider | Model | Cost per Analysis | Monthly Cost (100 analyses) | Notes |
|------|----------|-------|-------------------|----------------------------|--------|
| **Test (default)** | Google | gemini-1.5-flash | FREE | FREE | 1,500 requests/day free tier |
| **Production** | OpenAI | gpt-4o | ~$0.10 | ~$10 | High quality, reasonable cost |
| Custom | OpenAI | gpt-4o-mini | ~$0.005 | ~$0.50 | Best value, excellent quality |
| Custom | OpenAI | gpt-4-turbo | ~$0.30 | ~$30 | Very high quality |
| Custom | Anthropic | claude-3-5-haiku | ~$0.035 | ~$3.50 | Premium quality, good value |
| Custom | Anthropic | claude-3-5-sonnet | ~$0.91 | ~$91 | Highest quality |
| Custom | Google | gemini-1.5-pro | ~$0.15 | ~$15 | Good quality, decent cost |

**Recommendations:**
- **For testing/development:** Use default **Test Mode** (Gemini 1.5 Flash) - completely free within generous limits
- **For production:** Use **Production Mode** (GPT-4o) - excellent quality at reasonable cost
- **For maximum value:** Use custom `--model gpt-4o-mini` - best cost/quality ratio
- **For highest quality:** Use custom `--model claude-3-5-sonnet-20241022` - best analysis quality

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

### Source Modes

Qwilo supports two source modes:

**Gmail Mode (Default):**
- Fetches emails from Gmail with specific subject patterns
- Requires Gmail authentication
- Supports label filtering

**Drive Mode:**
- Scans Google Drive folders for transcript documents
- Works with any plain Google Docs (no special formatting required)
- Supports recursive subfolder scanning

### Basic Usage

**Gmail Mode (default):**
```bash
python3 cli.py                    # Uses test mode (Gemini 1.5 Flash)
python3 cli.py --mode production  # Uses production mode (GPT-4o)
```

**Drive Mode:**
```bash
python3 cli.py --source drive                    # Test mode
python3 cli.py --source drive --mode production  # Production mode
```

Or make it executable:
```bash
chmod +x cli.py
./cli.py --source drive
```

### AI Model Selection

The tool supports three ways to select AI models:

**1. Test Mode (default) - Fast & Economical:**
```bash
python3 cli.py                    # Uses Gemini 1.5 Flash
python3 cli.py --mode test        # Explicit test mode
```

**2. Production Mode - High Quality:**
```bash
python3 cli.py --mode production  # Uses GPT-4o
```

**3. Custom Model - Override Any Model:**
```bash
# Auto-detect provider from model name
python3 cli.py --model gpt-4o-mini
python3 cli.py --model claude-3-5-sonnet-20241022
python3 cli.py --model gemini-1.5-pro

# Explicitly specify provider
python3 cli.py --model claude-3-opus-20240229 --provider anthropic
python3 cli.py --model gpt-4-turbo --provider openai

# Works with all other options
python3 cli.py --source drive --model claude-3-5-sonnet-20241022
python3 cli.py --email "Meeting" --model gpt-4o --separate-files
```

**Available Models:**

- **OpenAI:** gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo, o1-preview, o1-mini
- **Anthropic:** claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, claude-3-opus-20240229
- **Google:** gemini-1.5-flash, gemini-1.5-pro, gemini-2.0-flash-exp

### Gmail Mode Command-Line Options

List all available transcripts:
```bash
python3 cli.py --list
```

Analyze a specific email by subject (supports partial matching):
```bash
python3 cli.py --email "Meeting Notes"
```

Customize content focus (overrides CONTENT_FOCUS environment variable):
```bash
python3 cli.py --focus "product management for SaaS companies"
python3 cli.py --focus "DevOps best practices"
python3 cli.py --focus "marketing strategies for B2B"
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

Output options:
```bash
python3 cli.py --separate-files  # Save each analysis to separate file (default: combined)
```

Combine multiple options:
```bash
python3 cli.py --label "blog-potential" --email "Strategy" --mode production
python3 cli.py --focus "engineering leadership" --separate-files --model gpt-4o-mini
python3 cli.py --email "Product" --focus "product management" --label "priority"
python3 cli.py --model claude-3-5-sonnet-20241022 --email "Meeting" --separate-files
```

### Drive Mode Command-Line Options

Use a specific Google Drive folder:
```bash
python3 cli.py --source drive --folder-id 1a2b3c4d5e6f7g8h9i0j
```

**How to find your folder ID:**
1. Open the folder in Google Drive
2. Copy the ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID`
3. The FOLDER_ID is the long string after `/folders/`

Combine with content focus and AI models:
```bash
python3 cli.py --source drive --focus "product management best practices"
python3 cli.py --source drive --mode production
python3 cli.py --source drive --model claude-3-5-sonnet-20241022
python3 cli.py --source drive --model gpt-4o-mini --focus "DevOps practices"
```

Save to separate files:
```bash
python3 cli.py --source drive --separate-files
python3 cli.py --source drive --separate-files --model gpt-4o
```

**Configuration via .env:**
```bash
# Set default source mode and folder in .env
SOURCE_MODE=drive
DRIVE_FOLDER_ID=your_folder_id_here
DRIVE_RECURSIVE=true  # Enable recursive subfolder scanning
```

Then simply run:
```bash
python3 cli.py  # Will use Drive mode with configured folder
```

### Output Options

**Default: Google Docs (Automatic)**
```bash
python3 cli.py  # Saves to Google Doc in OUTPUT_FOLDER_ID
python3 cli.py --source drive  # Same for Drive mode
```
- Analysis saved as Google Doc with name: `MMDDYYYY` (e.g., `11062024`)
- Automatically placed in configured output folder
- Returns clickable URL to view document

**Optional: Local Markdown Files**
```bash
python3 cli.py --save-local  # Saves as .md file locally
python3 cli.py --source drive --save-local
```
- Analysis saved as `analysis_TopicName_YYYYMMDD_HHMMSS.md`
- Stored in current directory

**Configure Output Folder (.env):**
```bash
# Set default output folder for Google Docs
OUTPUT_FOLDER_ID=1MVUaQyfyzaaBt-hOeUC9JFSiQeqE3no5
```

### Interactive Menu Options

Once the application starts (in either Gmail or Drive mode), you'll see:

1. **List of available transcripts/documents** - Shows all content from your selected source
2. **Analysis options:**
   - Enter a number (e.g., `1`) - Analyze a specific transcript
   - Enter `all` - Analyze all transcripts sequentially (with display and prompts)
   - Enter `batch` - Batch process all transcripts (skip display, auto-save)
   - Enter `range` (e.g., `1-5`) - Analyze a range of transcripts
   - Enter `q` - Quit the application

3. **After each analysis:**
   - View the results in formatted markdown
   - Choose to save the analysis to a file
   - Continue to the next transcript or return to the menu

**Batch Mode:** Selecting `batch` processes all transcripts without displaying analysis or prompting for confirmations. Perfect for processing many transcripts quickly - the tool will automatically save results to a combined file when done.

### Content Focus Customization

The analysis can be customized to focus on any domain or perspective. This changes how Claude analyzes the transcripts and generates article suggestions.

**Three ways to set content focus (in priority order):**

1. **Command-line flag (highest priority)** - Overrides all other settings:
   ```bash
   python3 cli.py --focus "product management for SaaS companies"
   ```

2. **Environment variable** - Set in `.env` file for persistent custom focus:
   ```bash
   CONTENT_FOCUS=DevOps best practices for enterprise teams
   ```

3. **Default** - If not specified, defaults to "AI strategy and innovation for business leaders"

**Example use cases:**

- **Product Management:** `--focus "product management best practices for SaaS"`
- **Engineering Leadership:** `--focus "engineering leadership and team management"`
- **DevOps:** `--focus "DevOps and infrastructure automation strategies"`
- **Marketing:** `--focus "B2B marketing strategies for tech companies"`
- **Sales:** `--focus "enterprise sales techniques and customer success"`
- **Design:** `--focus "UX design principles and user research"`

The content focus affects:
- Article topic recommendations
- Key insights extraction
- The angle and perspective of the analysis
- Which aspects of the conversation are emphasized

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

Each analysis includes **2-5 topics**, with each topic containing:

```markdown
**Source:** [Original email subject]

## TOPIC 1: [Topic Title]

**Description:** [1-3 sentences on why this would make a good article for the target audience]

**Key Insights:**
• [Insight 1 related to this topic]
• [Insight 2 related to this topic]
• [Insight 3 related to this topic]
• [Insight 4 related to this topic]
• [Insight 5 related to this topic]

**Notable Quotes:**
> **[Speaker Name]:** "[Exact verbatim quote from transcript]"

> **[Speaker Name]:** "[Another exact quote]"

> **[Speaker Name]:** "[Third exact quote]"

**Evidence/Data:** (Optional - when relevant data is mentioned)
• [Specific statistic, data point, or research finding]
• [Another piece of supporting evidence]

**Real-World Examples:** (Optional - when stories or examples are shared)
• [Real-world story, case study, or example from the conversation]
• [Another relevant example or perspective]

---

## TOPIC 2: [Topic Title]
...
```

**What's included in each topic:**
- **Compelling topic title** geared towards the target audience
- **1-3 sentence description** explaining why this would make a good article
- **2-5 key insights** specifically related to that topic
- **1-3 notable quotes** with speaker attribution (verbatim from transcript)
- **Evidence/Data** (optional) - statistics, research, or data points mentioned
- **Real-World Examples** (optional) - stories, case studies, or perspectives shared

### Saved Files

**Google Docs (Default):**
- Named by date: `MMDDYYYY` (e.g., `11062024`)
- Saved to configured OUTPUT_FOLDER_ID
- Returns URL for immediate viewing

**Local Markdown (with --save-local):**
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
├── google_drive_client.py     # Google Drive API for folder scanning
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

1. **Choose the right source mode for your workflow:**
   - **Gmail mode:** Best when transcripts arrive via email with consistent formatting
   - **Drive mode:** Best when transcripts are stored in a dedicated folder or managed outside email
2. **Customize content focus for your domain** - Use `--focus` to tailor analysis to your specific industry or content area
3. **Gmail mode tips:**
   - Choose transcripts with full Transcript tabs - These contain speaker names and verbatim dialogue
   - Use label filtering - Tag important conversations in Gmail with labels like "Blog potential"
4. **Drive mode tips:**
   - Organize transcripts in dedicated folders for easy scanning
   - Use DRIVE_RECURSIVE=true for nested folder structures
   - Name documents descriptively - the document name becomes the "topic"
5. **Review transcripts before analyzing** - The quality of analysis depends on transcript quality
6. **Save important analyses** - Use the save feature to keep analyses you want to reference
7. **Batch process related topics** - Use the `batch` option to analyze many conversations quickly
8. **Combine options effectively** - Mix `--focus`, `--source`, and mode-specific flags
9. **Refine topics** - The AI suggestions are starting points; use your editorial judgment

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
