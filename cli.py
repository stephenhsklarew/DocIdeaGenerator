#!/usr/bin/env python3
"""
Newsletter Transcript Analyzer - AI Strategy & Innovation Content Generator

Usage:
  # Gmail mode (default)
  python cli.py                           # Interactive mode (test mode, each topic in separate file)
  python cli.py --combined-topics         # Save all topics from transcript in one file
  python cli.py --mode production         # Use production mode (GPT-4o)
  python cli.py --model gpt-4o-mini       # Use specific AI model (auto-detects provider)
  python cli.py --model claude-3-5-sonnet-20241022 --provider anthropic  # Specify model and provider
  python cli.py --focus "custom topic"    # Override content focus
  python cli.py --email "Notes: Meeting"  # Analyze specific email by subject
  python cli.py --list                    # List all available emails

  # Drive mode
  python cli.py --source drive            # Scan Google Drive folder (each topic separate file)
  python cli.py --source drive --combined-topics  # All topics in one file per transcript
  python cli.py --source drive --folder-id ABC123  # Use specific folder
  python cli.py --source drive --mode production   # Drive mode with production AI model
  python cli.py --source drive --model gemini-1.5-pro  # Drive mode with custom model
"""
import sys
import os
import argparse
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt, Confirm
from gmail_client import GmailClient
from google_drive_client import GoogleDriveClient
from google_docs_client import GoogleDocsClient
from content_analyzer import ContentAnalyzer
from dotenv import load_dotenv

load_dotenv()

console = Console()

def parse_topics_from_analysis(analysis_text: str) -> list:
    """Parse individual topics from analysis markdown text"""
    import re

    # Split on topic headers (## TOPIC N:)
    topic_pattern = r'## TOPIC \d+:'
    splits = re.split(topic_pattern, analysis_text)

    # First split is before any topics (usually empty or intro text)
    # Remaining splits are topic content
    topics = []
    topic_headers = re.findall(topic_pattern, analysis_text)

    for i, (header, content) in enumerate(zip(topic_headers, splits[1:]), 1):
        # Extract topic title from header
        title_match = re.search(r'## TOPIC \d+: (.+)', header + content.split('\n')[0])
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = f"Topic {i}"

        # Clean content (remove the title line if it was captured)
        lines = content.strip().split('\n')
        if lines and lines[0].strip():
            topic_content = header + ' ' + content
        else:
            topic_content = header + '\n' + content

        topics.append({
            'number': i,
            'title': title,
            'content': topic_content.strip()
        })

    return topics

def display_banner():
    """Display the application banner with ASCII logo"""
    # ASCII art version of Qwilo logo (each line exactly 62 chars)
    logo = """
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║         ▄▄▄▄                                               ║
║       ▄█████▌    ██████╗ ██╗    ██╗██╗██╗      ██████╗     ║
║      ████████    ██╔═══██╗██║    ██║██║██║     ██╔═══██╗   ║
║     ▐██████▀     ██║   ██║██║ █╗ ██║██║██║     ██║   ██║   ║
║      █████▌      ██║▄▄ ██║██║███╗██║██║██║     ██║   ██║   ║
║       ████       ╚██████╔╝╚███╔███╔╝██║███████╗╚██████╔╝   ║
║                   ╚══▀▀═╝  ╚══╝╚══╝ ╚═╝╚══════╝ ╚═════╝    ║
║                                                            ║
║             The Article Idea Generator                     ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
"""
    console.print(logo, style="bold cyan")

def display_transcripts(transcripts):
    """Display transcripts in a formatted table"""
    if not transcripts:
        console.print("\n[yellow]No transcripts found matching the pattern.[/yellow]")
        return

    table = Table(title="Available Transcripts", show_lines=True)
    table.add_column("No.", style="cyan", justify="right", width=4)
    table.add_column("Topic", style="magenta", width=40)
    table.add_column("Date", style="green", width=15)
    table.add_column("Size", style="yellow", width=8)

    for idx, transcript in enumerate(transcripts, 1):
        word_count = len(transcript['body'].split())
        table.add_row(
            str(idx),
            transcript['topic'],
            transcript['date'],
            f"{word_count} words"
        )

    console.print("\n")
    console.print(table)
    console.print(f"\n[bold]Total transcripts found: {len(transcripts)}[/bold]\n")

def display_analysis(result):
    """Display the analysis results"""
    console.print("\n" + "="*80 + "\n")

    if 'error' in result:
        console.print(Panel(
            f"[bold red]Error:[/bold red] {result['error']}",
            title=f"{result['topic']} - {result['date']}",
            border_style="red"
        ))
        return

    header = f"[bold cyan]{result['topic']}[/bold cyan] - [green]{result['date']}[/green]"
    console.print(Panel(header, style="bold"))

    console.print("\n")
    md = Markdown(result['analysis'])
    console.print(md)
    console.print("\n" + "="*80 + "\n")

def save_topic(result, topic, topic_num, total_topics, save_local=False, docs_client=None):
    """Save individual topic to Google Docs (default) or local file"""
    # Prepare content for single topic
    content = f"# {result['topic']}\n"
    content += f"**Date:** {result['date']}\n"
    content += f"**Topic {topic_num} of {total_topics}**\n\n"
    content += "---\n\n"
    content += topic['content']

    if save_local:
        # Save as local markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in topic['title'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')[:50]
        filename = f"topic_{topic_num}_{safe_title}_{timestamp}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"[green]Topic {topic_num} saved to: {filename}[/green]")
        return filename
    else:
        # Save as Google Doc (default)
        if not docs_client:
            docs_client = GoogleDocsClient()

        output_folder_id = os.getenv('OUTPUT_FOLDER_ID')
        if not output_folder_id:
            console.print("[yellow]Warning: OUTPUT_FOLDER_ID not set in .env. Document will be created in root Drive folder.[/yellow]")

        # Document title format: MMDDYYYY_Topic_N_TopicTitle
        date_str = datetime.now().strftime("%m%d%Y")
        safe_title = "".join(c for c in topic['title'] if c.isalnum() or c in (' ', '-', '_')).strip()[:40]
        doc_title = f"{date_str}_Topic_{topic_num}_{safe_title}"

        doc_info = docs_client.create_document(
            title=doc_title,
            content=content,
            folder_id=output_folder_id
        )

        if doc_info:
            console.print(f"[green]✓ Topic {topic_num} saved to Google Doc: {doc_title}[/green]")
            console.print(f"[cyan]View at: {doc_info['url']}[/cyan]")
            return doc_info['url']
        else:
            console.print(f"[red]Failed to create Google Doc for topic {topic_num}.[/red]")
            return None

def save_analysis(result, save_local=False, docs_client=None, combined_topics=False):
    """Save analysis to Google Docs (default) or local file

    Args:
        result: Analysis result dictionary
        save_local: Save as local markdown instead of Google Doc
        docs_client: GoogleDocsClient instance (optional)
        combined_topics: If True, save all topics in one file (old behavior).
                        If False (default), save each topic separately
    """
    if 'error' in result:
        console.print("[red]Cannot save analysis with errors.[/red]")
        return

    # Parse topics from analysis
    topics = parse_topics_from_analysis(result['analysis'])

    if not combined_topics and topics:
        # NEW DEFAULT: Save each topic separately
        console.print(f"[cyan]Saving {len(topics)} topics individually...[/cyan]")
        for topic in topics:
            save_topic(result, topic, topic['number'], len(topics), save_local, docs_client)
    else:
        # LEGACY: Save all topics combined in one file
        # Prepare content
        content = f"# {result['topic']}\n"
        content += f"**Date:** {result['date']}\n\n"
        content += "---\n\n"
        content += result['analysis']

        if save_local:
            # Save as local markdown file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_topic = "".join(c for c in result['topic'] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_topic = safe_topic.replace(' ', '_')[:50]
            filename = f"analysis_{safe_topic}_{timestamp}.md"

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)

            console.print(f"[green]Combined analysis saved to: {filename}[/green]")
        else:
            # Save as Google Doc (default)
            if not docs_client:
                docs_client = GoogleDocsClient()

            output_folder_id = os.getenv('OUTPUT_FOLDER_ID')
            if not output_folder_id:
                console.print("[yellow]Warning: OUTPUT_FOLDER_ID not set in .env. Document will be created in root Drive folder.[/yellow]")

            # Document title is just MMDDYYYY
            doc_title = datetime.now().strftime("%m%d%Y")

            doc_info = docs_client.create_document(
                title=doc_title,
                content=content,
                folder_id=output_folder_id
            )

            if doc_info:
                console.print(f"[green]✓ Combined analysis saved to Google Doc: {doc_title}[/green]")
                console.print(f"[cyan]View at: {doc_info['url']}[/cyan]")
            else:
                console.print("[red]Failed to create Google Doc. Use --save-local flag to save as markdown instead.[/red]")

def save_combined_analysis(results, save_local=False, docs_client=None):
    """Save multiple analyses to a single combined Google Doc or file"""
    # Filter out results with errors
    valid_results = [r for r in results if 'error' not in r]

    if not valid_results:
        console.print("[red]No valid analyses to save.[/red]")
        return

    # Prepare combined content
    content = "# Combined Analysis Report\n\n"
    content += f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n"
    content += f"**Total Transcripts:** {len(valid_results)}\n\n"
    content += "---\n\n"

    for idx, result in enumerate(valid_results, 1):
        # Add section header for each transcript
        content += f"# {idx}. {result['topic']}\n"
        content += f"**Date:** {result['date']}\n\n"
        content += "---\n\n"
        content += result['analysis']
        content += "\n\n"

        # Add separator between sections (except after the last one)
        if idx < len(valid_results):
            content += "\n" + "="*80 + "\n\n"

    if save_local:
        # Save as local markdown file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_combined_{timestamp}.md"

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"[green]Combined analysis saved to: {filename}[/green]")
        console.print(f"[green]Saved {len(valid_results)} transcript(s) to a single file[/green]")
    else:
        # Save as Google Doc (default)
        if not docs_client:
            docs_client = GoogleDocsClient()

        output_folder_id = os.getenv('OUTPUT_FOLDER_ID')
        if not output_folder_id:
            console.print("[yellow]Warning: OUTPUT_FOLDER_ID not set in .env. Document will be created in root Drive folder.[/yellow]")

        # Document title is just MMDDYYYY
        doc_title = datetime.now().strftime("%m%d%Y")

        doc_info = docs_client.create_document(
            title=doc_title,
            content=content,
            folder_id=output_folder_id
        )

        if doc_info:
            console.print(f"[green]✓ Combined analysis saved to Google Doc: {doc_title}[/green]")
            console.print(f"[cyan]View at: {doc_info['url']}[/cyan]")
            console.print(f"[green]Saved {len(valid_results)} transcript(s) to a single document[/green]")
        else:
            console.print("[red]Failed to create Google Doc. Use --save-local flag to save as markdown instead.[/red]")

def get_start_date() -> str:
    """Prompt for start date if not in environment"""
    start_date = os.getenv('START_DATE', '').strip()

    if not start_date:
        console.print("\n[cyan]Date Filter Configuration[/cyan]")
        console.print("You can filter transcripts to only show those from a specific date forward.")
        console.print("Format: MMDDYYYY (e.g., 10232025 for October 23, 2025)")

        if Confirm.ask("Would you like to set a start date filter?", default=False):
            while True:
                date_input = Prompt.ask("Enter start date (MMDDYYYY)").strip()

                # Validate format
                try:
                    datetime.strptime(date_input, '%m%d%Y')
                    start_date = date_input
                    console.print(f"[green]✓ Start date set to: {date_input}[/green]\n")
                    break
                except ValueError:
                    console.print("[red]Invalid format. Please use MMDDYYYY (e.g., 10232025)[/red]")

    return start_date

def main_menu_drive(folder_id=None, name_pattern=None, modified_after=None, separate_files=False, combined_topics=False, content_focus=None, save_local=False, mode='test', model_override=None, provider_override=None):
    """Display the main menu and handle user interaction for Drive mode"""
    display_banner()

    try:
        console.print("[bold]Connecting to Google Drive...[/bold]")
        drive_client = GoogleDriveClient(folder_id=folder_id)
        docs_client = GoogleDocsClient()
        console.print("[green]✓ Connected successfully![/green]\n")

        if drive_client.folder_id:
            console.print(f"[cyan]Scanning folder: {drive_client.folder_id}[/cyan]")
        if drive_client.recursive:
            console.print(f"[cyan]Recursive scan: Enabled[/cyan]")

        # Display mode
        if model_override:
            mode_display = f"Custom Model: {model_override}"
            if provider_override:
                mode_display += f" (Provider: {provider_override})"
        else:
            mode_display = "Test Mode (Gemini 1.5 Flash)" if mode == 'test' else "Production Mode (GPT-4o)"
        console.print(f"[cyan]AI Mode: {mode_display}[/cyan]\n")

        console.print("[bold]Fetching documents...[/bold]")
        documents = drive_client.list_documents(
            name_pattern=name_pattern,
            modified_after=modified_after
        )

        if not documents:
            console.print("[yellow]No documents found in the folder. Exiting.[/yellow]")
            return

        # Convert Drive documents to transcript format for compatibility
        transcripts = []
        console.print(f"[bold]Loading content from {len(documents)} documents...[/bold]")

        for doc in documents:
            console.print(f"  → Loading: {doc['name']}")
            content = docs_client.get_plain_document_content(doc['id'])

            if content:
                # Parse date from modified time
                try:
                    dt = datetime.fromisoformat(doc['modified'].replace('Z', '+00:00'))
                    date_str = dt.strftime('%b %d, %Y')
                except:
                    date_str = doc.get('modified', 'Unknown date')

                transcripts.append({
                    'id': doc['id'],
                    'subject': doc['name'],  # Use document name as subject
                    'topic': doc['name'],
                    'date': date_str,
                    'body': content,
                    'source': 'drive',
                    'folder_path': doc.get('folder_path', '')
                })

        console.print(f"[green]✓ Loaded {len(transcripts)} documents[/green]\n")

        analyzer = ContentAnalyzer(content_focus=content_focus, mode=mode, model_override=model_override, provider_override=provider_override)

        while True:
            display_transcripts(transcripts)

            console.print("[bold cyan]Options:[/bold cyan]")
            console.print("  • Enter a number (1-{}) to analyze a specific document".format(len(transcripts)))
            console.print("  • Enter 'all' to analyze all documents")
            console.print("  • Enter 'batch' to batch process all (skip display, auto-save)")
            console.print("  • Enter 'range' to analyze a range (e.g., 1-5)")
            console.print("  • Enter 'q' to quit\n")

            choice = Prompt.ask("What would you like to do?").strip().lower()

            if choice == 'q':
                console.print("\n[bold blue]Thanks for using Qwilo. If you have improvement ideas, please email them to stephen@synaptiq.ai :)[/bold blue]\n")
                break

            elif choice == 'all':
                console.print(f"\n[bold]Analyzing {len(transcripts)} documents...[/bold]\n")

                results = []
                for idx, transcript in enumerate(transcripts, 1):
                    console.print(f"[cyan]Analyzing {idx}/{len(transcripts)}: {transcript['topic']}[/cyan]")
                    result = analyzer.analyze_transcript(transcript)
                    display_analysis(result)
                    results.append(result)

                    if idx < len(transcripts):
                        if not Confirm.ask("Continue to next document?", default=True):
                            break

                # Save results - either combined or separate files
                if results and Confirm.ask("Save analysis?", default=True):
                    if separate_files:
                        console.print("\n[cyan]Saving separate files...[/cyan]")
                        for result in results:
                            save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                    else:
                        save_combined_analysis(results, save_local=save_local, docs_client=docs_client)

            elif choice == 'batch':
                console.print(f"\n[bold cyan]Batch Mode:[/bold cyan] Processing {len(transcripts)} documents...\n")

                results = []
                for idx, transcript in enumerate(transcripts, 1):
                    console.print(f"[cyan]Analyzing {idx}/{len(transcripts)}: {transcript['topic']}[/cyan]")
                    result = analyzer.analyze_transcript(transcript)
                    results.append(result)

                # Auto-save results
                if results:
                    if separate_files:
                        console.print("\n[cyan]Saving separate files...[/cyan]")
                        for result in results:
                            save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                    else:
                        save_combined_analysis(results, save_local=save_local, docs_client=docs_client)

            elif choice == 'range':
                range_input = Prompt.ask("Enter range (e.g., 1-5)")
                try:
                    start, end = map(int, range_input.split('-'))
                    if 1 <= start <= end <= len(transcripts):
                        results = []
                        for idx in range(start - 1, end):
                            console.print(f"\n[cyan]Analyzing: {transcripts[idx]['topic']}[/cyan]")
                            result = analyzer.analyze_transcript(transcripts[idx])
                            display_analysis(result)
                            results.append(result)

                            if idx < end - 1:
                                if not Confirm.ask("Continue to next document?", default=True):
                                    break

                        # Save results - either combined or separate files
                        if results and Confirm.ask("Save analysis?", default=True):
                            if separate_files:
                                console.print("\n[cyan]Saving separate files...[/cyan]")
                                for result in results:
                                    save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                            else:
                                save_combined_analysis(results, save_local=save_local, docs_client=docs_client)
                    else:
                        console.print("[red]Invalid range. Please try again.[/red]")
                except ValueError:
                    console.print("[red]Invalid format. Use format like: 1-5[/red]")

            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(transcripts):
                    transcript = transcripts[idx]
                    console.print(f"\n[bold cyan]Analyzing: {transcript['topic']}[/bold cyan]\n")

                    result = analyzer.analyze_transcript(transcript)
                    display_analysis(result)

                    if Confirm.ask("Save this analysis?", default=True):
                        save_analysis(result, combined_topics=combined_topics)
                else:
                    console.print("[red]Invalid number. Please try again.[/red]")

            else:
                console.print("[red]Invalid option. Please try again.[/red]")

            console.print("\n")

    except FileNotFoundError as e:
        console.print(f"[bold red]Setup Error:[/bold red] {e}")
        console.print("\n[yellow]Please follow the setup instructions in README.md[/yellow]\n")
    except ValueError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        console.print("\n[yellow]Please check your .env file configuration[/yellow]\n")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())

def batch_process_all(start_date=None, label=None, separate_files=False, combined_topics=False, content_focus=None, save_local=False, mode='test', model_override=None, provider_override=None):
    """Batch process all emails matching criteria (non-interactive mode)"""
    display_banner()

    try:
        console.print("[bold]Connecting to Gmail...[/bold]")
        gmail = GmailClient(start_date=start_date, label=label)
        docs_client = GoogleDocsClient()
        console.print("[green]✓ Connected successfully![/green]\n")

        if label:
            console.print(f"[cyan]Filtering by label: {label}[/cyan]")
        if start_date:
            dt = datetime.strptime(start_date, '%m%d%Y')
            console.print(f"[cyan]Filtering transcripts from {dt.strftime('%B %d, %Y')} onwards...[/cyan]")

        # Display mode
        if model_override:
            mode_display = f"Custom Model: {model_override}"
            if provider_override:
                mode_display += f" (Provider: {provider_override})"
        else:
            mode_display = "Test Mode (Gemini 1.5 Flash)" if mode == 'test' else "Production Mode (GPT-4o)"
        console.print(f"[cyan]AI Mode: {mode_display}[/cyan]\n")

        console.print("[bold]Fetching transcripts...[/bold]")
        transcripts = gmail.get_transcripts()

        if not transcripts:
            console.print("[yellow]No transcripts found.[/yellow]")
            return

        console.print(f"[bold cyan]Batch Mode:[/bold cyan] Processing {len(transcripts)} transcripts...\n")

        analyzer = ContentAnalyzer(content_focus=content_focus, mode=mode, model_override=model_override, provider_override=provider_override)
        results = []

        for idx, transcript in enumerate(transcripts, 1):
            console.print(f"[cyan]Analyzing {idx}/{len(transcripts)}: {transcript['topic']}[/cyan]")
            result = analyzer.analyze_transcript(transcript)
            results.append(result)

        # Auto-save results
        if results:
            console.print("\n[cyan]Saving results...[/cyan]")
            for result in results:
                save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
            console.print(f"\n[green]✓ Successfully processed and saved {len(results)} transcripts![/green]")

    except Exception as e:
        console.print(f"[red]Error during batch processing: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

def main_menu(label=None, separate_files=False, combined_topics=False, content_focus=None, save_local=False, mode='test', model_override=None, provider_override=None):
    """Display the main menu and handle user interaction"""
    display_banner()

    try:
        # Get or prompt for start date (only if no label specified)
        start_date = get_start_date() if not label else None

        console.print("[bold]Connecting to Gmail...[/bold]")
        gmail = GmailClient(start_date=start_date, label=label)
        docs_client = GoogleDocsClient()  # For saving to Google Docs
        console.print("[green]✓ Connected successfully![/green]\n")

        if label:
            console.print(f"[cyan]Filtering by label: {label}[/cyan]")
        elif start_date:
            dt = datetime.strptime(start_date, '%m%d%Y')
            console.print(f"[cyan]Filtering transcripts from {dt.strftime('%B %d, %Y')} onwards...[/cyan]")

        # Display mode
        if model_override:
            mode_display = f"Custom Model: {model_override}"
            if provider_override:
                mode_display += f" (Provider: {provider_override})"
        else:
            mode_display = "Test Mode (Gemini 1.5 Flash)" if mode == 'test' else "Production Mode (GPT-4o)"
        console.print(f"[cyan]AI Mode: {mode_display}[/cyan]\n")

        console.print("[bold]Fetching transcripts...[/bold]")
        transcripts = gmail.get_transcripts()

        if not transcripts:
            console.print("[yellow]No transcripts found. Exiting.[/yellow]")
            return

        analyzer = ContentAnalyzer(content_focus=content_focus, mode=mode, model_override=model_override, provider_override=provider_override)

        while True:
            display_transcripts(transcripts)

            console.print("[bold cyan]Options:[/bold cyan]")
            console.print("  • Enter a number (1-{}) to analyze a specific transcript".format(len(transcripts)))
            console.print("  • Enter 'all' to analyze all transcripts")
            console.print("  • Enter 'batch' to batch process all (skip display, auto-save)")
            console.print("  • Enter 'range' to analyze a range (e.g., 1-5)")
            console.print("  • Enter 'q' to quit\n")

            choice = Prompt.ask("What would you like to do?").strip().lower()

            if choice == 'q':
                console.print("\n[bold blue]Thanks for using Qwilo. If you have improvement ideas, please email them to stephen@synaptiq.ai :)[/bold blue]\n")
                break

            elif choice == 'all':
                console.print(f"\n[bold]Analyzing {len(transcripts)} transcripts...[/bold]\n")

                results = []
                for idx, transcript in enumerate(transcripts, 1):
                    console.print(f"[cyan]Analyzing {idx}/{len(transcripts)}: {transcript['topic']}[/cyan]")
                    result = analyzer.analyze_transcript(transcript)
                    display_analysis(result)
                    results.append(result)

                    if idx < len(transcripts):
                        if not Confirm.ask("Continue to next transcript?", default=True):
                            break

                # Save results - either combined or separate files
                if results and Confirm.ask("Save analysis?", default=True):
                    if separate_files:
                        console.print("\n[cyan]Saving separate files...[/cyan]")
                        for result in results:
                            save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                    else:
                        save_combined_analysis(results, save_local=save_local, docs_client=docs_client)

            elif choice == 'batch':
                console.print(f"\n[bold cyan]Batch Mode:[/bold cyan] Processing {len(transcripts)} transcripts...\n")

                results = []
                for idx, transcript in enumerate(transcripts, 1):
                    console.print(f"[cyan]Analyzing {idx}/{len(transcripts)}: {transcript['topic']}[/cyan]")
                    result = analyzer.analyze_transcript(transcript)
                    results.append(result)

                # Auto-save results
                if results:
                    if separate_files:
                        console.print("\n[cyan]Saving separate files...[/cyan]")
                        for result in results:
                            save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                    else:
                        save_combined_analysis(results, save_local=save_local, docs_client=docs_client)

            elif choice == 'range':
                range_input = Prompt.ask("Enter range (e.g., 1-5)")
                try:
                    start, end = map(int, range_input.split('-'))
                    if 1 <= start <= end <= len(transcripts):
                        results = []
                        for idx in range(start - 1, end):
                            console.print(f"\n[cyan]Analyzing: {transcripts[idx]['topic']}[/cyan]")
                            result = analyzer.analyze_transcript(transcripts[idx])
                            display_analysis(result)
                            results.append(result)

                            if idx < end - 1:
                                if not Confirm.ask("Continue to next transcript?", default=True):
                                    break

                        # Save results - either combined or separate files
                        if results and Confirm.ask("Save analysis?", default=True):
                            if separate_files:
                                console.print("\n[cyan]Saving separate files...[/cyan]")
                                for result in results:
                                    save_analysis(result, save_local=save_local, docs_client=docs_client, combined_topics=combined_topics)
                            else:
                                save_combined_analysis(results, save_local=save_local, docs_client=docs_client)
                    else:
                        console.print("[red]Invalid range. Please try again.[/red]")
                except ValueError:
                    console.print("[red]Invalid format. Use format like: 1-5[/red]")

            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(transcripts):
                    transcript = transcripts[idx]
                    console.print(f"\n[bold cyan]Analyzing: {transcript['topic']}[/bold cyan]\n")

                    result = analyzer.analyze_transcript(transcript)
                    display_analysis(result)

                    if Confirm.ask("Save this analysis?", default=True):
                        save_analysis(result, combined_topics=combined_topics)
                else:
                    console.print("[red]Invalid number. Please try again.[/red]")

            else:
                console.print("[red]Invalid option. Please try again.[/red]")

            console.print("\n")

    except FileNotFoundError as e:
        console.print(f"[bold red]Setup Error:[/bold red] {e}")
        console.print("\n[yellow]Please follow the setup instructions in README.md[/yellow]\n")
    except ValueError as e:
        console.print(f"[bold red]Configuration Error:[/bold red] {e}")
        console.print("\n[yellow]Please check your .env file configuration[/yellow]\n")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        import traceback
        console.print(traceback.format_exc())

def list_emails_only(start_date=None, label=None):
    """List all available emails without interactive menu"""
    console.print("[bold]Connecting to Gmail...[/bold]")
    gmail = GmailClient(start_date=start_date, label=label)
    console.print("[green]✓ Connected successfully![/green]\n")

    if label:
        console.print(f"[cyan]Filtering by label: {label}[/cyan]")

    console.print("[bold]Fetching transcripts...[/bold]")
    transcripts = gmail.get_transcripts()

    if not transcripts:
        console.print("[yellow]No transcripts found.[/yellow]")
        return

    display_transcripts(transcripts)


def analyze_specific_email(email_subject, start_date=None, label=None, separate_files=False, combined_topics=False, content_focus=None, save_local=False, mode='test', model_override=None, provider_override=None, auto_confirm=False):
    """Analyze a specific email by subject line (supports partial matching)"""
    console.print("[bold]Connecting to Gmail...[/bold]")
    gmail = GmailClient(start_date=start_date, label=label)
    docs_client = GoogleDocsClient()  # For saving to Google Docs
    console.print("[green]✓ Connected successfully![/green]\n")

    if label:
        console.print(f"[cyan]Filtering by label: {label}[/cyan]")

    # Display mode
    if model_override:
        mode_display = f"Custom Model: {model_override}"
        if provider_override:
            mode_display += f" (Provider: {provider_override})"
    else:
        mode_display = "Test Mode (Gemini 1.5 Flash)" if mode == 'test' else "Production Mode (GPT-4o)"
    console.print(f"[cyan]AI Mode: {mode_display}[/cyan]\n")

    console.print("[bold]Fetching transcripts...[/bold]")
    transcripts = gmail.get_transcripts()

    if not transcripts:
        console.print("[yellow]No transcripts found.[/yellow]")
        return

    # Find matching transcripts (case-insensitive partial match)
    email_subject_lower = email_subject.lower()
    matches = [t for t in transcripts if email_subject_lower in t['subject'].lower() or email_subject_lower in t['topic'].lower()]

    if not matches:
        console.print(f"[yellow]No emails found matching: '{email_subject}'[/yellow]\n")
        console.print("[cyan]Available emails:[/cyan]")
        display_transcripts(transcripts)
        return

    if len(matches) > 1:
        console.print(f"[yellow]Found {len(matches)} emails matching '{email_subject}':[/yellow]\n")
        display_transcripts(matches)

        choice = Prompt.ask(f"Which one would you like to analyze? (1-{len(matches)}, or 'all')", default="1")

        if choice.lower() == 'all':
            console.print(f"\n[bold]Analyzing all {len(matches)} matching transcripts...[/bold]\n")

            analyzer = ContentAnalyzer(content_focus=content_focus, mode=mode, model_override=model_override, provider_override=provider_override)

            results = []
            for idx, transcript in enumerate(matches, 1):
                console.print(f"[cyan]Analyzing {idx}/{len(matches)}: {transcript['topic']}[/cyan]")
                result = analyzer.analyze_transcript(transcript)
                display_analysis(result)
                results.append(result)

                if idx < len(matches):
                    if not Confirm.ask("Continue to next transcript?", default=True):
                        break

            # Save results - either combined or separate files
            if results and Confirm.ask("Save analysis?", default=True):
                if separate_files:
                    console.print("\n[cyan]Saving separate files...[/cyan]")
                    for result in results:
                        save_analysis(result, combined_topics=combined_topics)
                else:
                    save_combined_analysis(results)
            return
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(matches):
                    transcript = matches[idx]
                else:
                    console.print("[red]Invalid selection.[/red]")
                    return
            except ValueError:
                console.print("[red]Invalid input.[/red]")
                return
    else:
        transcript = matches[0]

    # Analyze the selected transcript
    console.print(f"\n[bold cyan]Analyzing: {transcript['topic']}[/bold cyan]\n")

    analyzer = ContentAnalyzer(content_focus=content_focus, mode=mode, model_override=model_override, provider_override=provider_override)
    result = analyzer.analyze_transcript(transcript)
    display_analysis(result)

    # Auto-confirm in non-interactive mode, otherwise prompt
    if auto_confirm or Confirm.ask("Save this analysis?", default=True):
        save_analysis(result, save_local=save_local, combined_topics=combined_topics)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Qwilo - The Article Idea Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                           # Interactive mode (each topic separate file)
  python cli.py --combined-topics         # All topics in one file per transcript
  python cli.py --mode production         # Interactive mode (production mode, GPT-4o)
  python cli.py --model gpt-4o-mini       # Use specific model (auto-detects OpenAI)
  python cli.py --model claude-3-5-sonnet-20241022  # Use Claude Sonnet (auto-detects Anthropic)
  python cli.py --model gemini-1.5-pro --provider google  # Specify model and provider explicitly
  python cli.py --focus "product management for SaaS"  # Custom content focus
  python cli.py --email "Notes: Meeting"  # Analyze specific email by subject
  python cli.py --email "Daily Sync"      # Partial match works too
  python cli.py --list                    # List all available emails
  python cli.py --list --start-date 10232025  # List emails from date onwards
  python cli.py --list --label "AIQ"      # List emails with label "AIQ"
  python cli.py --email "Meeting" --label "Priority"  # Analyze with label filter
  python cli.py --focus "DevOps best practices" --combined-topics  # Combine flags
  python cli.py --source drive --mode production  # Drive mode with GPT-4o
  python cli.py --source drive --model claude-3-opus-20240229  # Drive mode with custom model
  python cli.py --source drive --combined-topics  # Drive mode, combined topics per transcript
        """
    )
    parser.add_argument(
        '--email', '-e',
        help='Email subject to analyze (supports partial matching)'
    )
    parser.add_argument(
        '--list', '-l',
        action='store_true',
        help='List all available emails without analyzing'
    )
    parser.add_argument(
        '--start-date',
        help='Filter emails from this date forward (format: MMDDYYYY, e.g., 10232025)'
    )
    parser.add_argument(
        '--label',
        help='Filter emails by Gmail label (e.g., "AIQ", "Priority")'
    )
    parser.add_argument(
        '--separate-files',
        action='store_true',
        help='Save each transcript analysis to a separate file (deprecated, per-topic saving is now default)'
    )
    parser.add_argument(
        '--combined-topics',
        action='store_true',
        help='Save all topics from each transcript in one file (default: save each topic separately)'
    )
    parser.add_argument(
        '--save-local',
        action='store_true',
        help='Save analysis as local markdown file instead of Google Doc (default: Google Doc)'
    )
    parser.add_argument(
        '--yes', '-y',
        action='store_true',
        help='Auto-confirm all prompts (non-interactive mode for automation)'
    )
    parser.add_argument(
        '--batch', '-b',
        action='store_true',
        help='Batch mode: process all emails matching criteria and auto-save (non-interactive)'
    )
    parser.add_argument(
        '--focus',
        help='Content focus for article generation (default: AI strategy and innovation for business leaders)'
    )
    parser.add_argument(
        '--source',
        choices=['gmail', 'drive'],
        default=None,
        help='Source mode: gmail (fetch from Gmail) or drive (scan Google Drive folder). Default: from SOURCE_MODE env or gmail'
    )
    parser.add_argument(
        '--folder-id',
        help='Google Drive folder ID (only for --source drive). Overrides DRIVE_FOLDER_ID from .env'
    )
    parser.add_argument(
        '--mode',
        choices=['test', 'production'],
        default='test',
        help='AI mode: test (uses Gemini 1.5 Flash) or production (uses GPT-4o). Default: test'
    )
    parser.add_argument(
        '--model',
        help='Override AI model (e.g., gpt-4o, claude-3-5-sonnet-20241022, gemini-1.5-pro). Overrides --mode setting.'
    )
    parser.add_argument(
        '--provider',
        choices=['anthropic', 'openai', 'google'],
        help='AI provider to use with --model (anthropic, openai, or google). Auto-detected if not specified.'
    )

    args = parser.parse_args()

    try:
        # Determine source mode
        source_mode = args.source or os.getenv('SOURCE_MODE', 'gmail').lower()

        # Get parameters
        start_date = args.start_date or os.getenv('START_DATE', '').strip()
        label = args.label
        separate_files = args.separate_files
        combined_topics = args.combined_topics  # Combine topics in one file
        content_focus = args.focus
        folder_id = args.folder_id  # For Drive mode
        save_local = args.save_local  # Save as markdown instead of Google Doc
        auto_confirm = args.yes  # Auto-confirm all prompts (non-interactive mode)
        mode = args.mode  # AI mode: test or production
        model_override = args.model  # Specific model override
        provider_override = args.provider  # Specific provider override

        # Route to appropriate mode
        if source_mode == 'drive':
            # Drive mode - Gmail-specific flags are ignored
            if args.list or args.email or label:
                console.print("[yellow]Warning: --list, --email, and --label flags are only for Gmail mode and will be ignored in Drive mode[/yellow]\n")

            # Interactive Drive mode
            main_menu_drive(
                folder_id=folder_id,
                modified_after=start_date,
                separate_files=separate_files,
                combined_topics=combined_topics,
                content_focus=content_focus,
                save_local=save_local,
                mode=mode,
                model_override=model_override,
                provider_override=provider_override
            )

        else:
            # Gmail mode (default)
            if folder_id:
                console.print("[yellow]Warning: --folder-id flag is only for Drive mode and will be ignored in Gmail mode[/yellow]\n")

            if args.list:
                # List mode
                display_banner()
                list_emails_only(start_date, label)

            elif args.email:
                # Direct email analysis mode
                display_banner()
                analyze_specific_email(args.email, start_date, label, separate_files, combined_topics, content_focus, save_local, mode, model_override, provider_override, auto_confirm)

            elif args.batch:
                # Batch mode - process all emails matching criteria
                batch_process_all(start_date=start_date, label=label, separate_files=separate_files, combined_topics=combined_topics, content_focus=content_focus, save_local=save_local, mode=mode, model_override=model_override, provider_override=provider_override)

            else:
                # Interactive mode (default)
                main_menu(label=label, separate_files=separate_files, combined_topics=combined_topics, content_focus=content_focus, save_local=save_local, mode=mode, model_override=model_override, provider_override=provider_override)

    except KeyboardInterrupt:
        console.print("\n\n[bold blue]Thanks for using Qwilo. If you have improvement ideas, please email them to stephen@synaptiq.ai :)[/bold blue]\n")
        sys.exit(0)
