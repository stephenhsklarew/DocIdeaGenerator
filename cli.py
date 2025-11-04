#!/usr/bin/env python3
"""
Newsletter Transcript Analyzer - AI Strategy & Innovation Content Generator

Usage:
  python cli.py                           # Interactive mode (combined output by default)
  python cli.py --separate-files          # Save each analysis to separate files
  python cli.py --focus "custom topic"    # Override content focus
  python cli.py --email "Notes: Meeting"  # Analyze specific email by subject
  python cli.py --list                    # List all available emails
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
from content_analyzer import ContentAnalyzer
from dotenv import load_dotenv

load_dotenv()

console = Console()

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

def save_analysis(result, filename=None):
    """Save analysis to a file"""
    if 'error' in result:
        console.print("[red]Cannot save analysis with errors.[/red]")
        return

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c for c in result['topic'] if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_topic = safe_topic.replace(' ', '_')[:50]
        filename = f"analysis_{safe_topic}_{timestamp}.md"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"# {result['topic']}\n")
        f.write(f"**Date:** {result['date']}\n\n")
        f.write("---\n\n")
        f.write(result['analysis'])

    console.print(f"[green]Analysis saved to: {filename}[/green]")

def save_combined_analysis(results, filename=None):
    """Save multiple analyses to a single combined file"""
    # Filter out results with errors
    valid_results = [r for r in results if 'error' not in r]

    if not valid_results:
        console.print("[red]No valid analyses to save.[/red]")
        return

    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_combined_{timestamp}.md"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write("# Combined Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%B %d, %Y at %I:%M %p')}\n")
        f.write(f"**Total Transcripts:** {len(valid_results)}\n\n")
        f.write("---\n\n")

        for idx, result in enumerate(valid_results, 1):
            # Add section header for each transcript
            f.write(f"# {idx}. {result['topic']}\n")
            f.write(f"**Date:** {result['date']}\n\n")
            f.write("---\n\n")
            f.write(result['analysis'])
            f.write("\n\n")

            # Add separator between sections (except after the last one)
            if idx < len(valid_results):
                f.write("\n" + "="*80 + "\n\n")

    console.print(f"[green]Combined analysis saved to: {filename}[/green]")
    console.print(f"[green]Saved {len(valid_results)} transcript(s) to a single file[/green]")

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

def main_menu(label=None, separate_files=False, content_focus=None):
    """Display the main menu and handle user interaction"""
    display_banner()

    try:
        # Get or prompt for start date (only if no label specified)
        start_date = get_start_date() if not label else None

        console.print("[bold]Connecting to Gmail...[/bold]")
        gmail = GmailClient(start_date=start_date, label=label)
        console.print("[green]✓ Connected successfully![/green]\n")

        if label:
            console.print(f"[cyan]Filtering by label: {label}[/cyan]")
        elif start_date:
            dt = datetime.strptime(start_date, '%m%d%Y')
            console.print(f"[cyan]Filtering transcripts from {dt.strftime('%B %d, %Y')} onwards...[/cyan]")

        console.print("[bold]Fetching transcripts...[/bold]")
        transcripts = gmail.get_transcripts()

        if not transcripts:
            console.print("[yellow]No transcripts found. Exiting.[/yellow]")
            return

        analyzer = ContentAnalyzer(content_focus=content_focus)

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
                            save_analysis(result)
                    else:
                        save_combined_analysis(results)

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
                            save_analysis(result)
                    else:
                        save_combined_analysis(results)

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
                                    save_analysis(result)
                            else:
                                save_combined_analysis(results)
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
                        save_analysis(result)
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


def analyze_specific_email(email_subject, start_date=None, label=None, separate_files=False, content_focus=None):
    """Analyze a specific email by subject line (supports partial matching)"""
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

            analyzer = ContentAnalyzer(content_focus=content_focus)

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
                        save_analysis(result)
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

    analyzer = ContentAnalyzer(content_focus=content_focus)
    result = analyzer.analyze_transcript(transcript)
    display_analysis(result)

    if Confirm.ask("Save this analysis?", default=True):
        save_analysis(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Qwilo - The Article Idea Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                           # Interactive mode (combined output by default)
  python cli.py --separate-files          # Interactive mode with separate files
  python cli.py --focus "product management for SaaS"  # Custom content focus
  python cli.py --email "Notes: Meeting"  # Analyze specific email by subject
  python cli.py --email "Daily Sync"      # Partial match works too
  python cli.py --list                    # List all available emails
  python cli.py --list --start-date 10232025  # List emails from date onwards
  python cli.py --list --label "AIQ"      # List emails with label "AIQ"
  python cli.py --email "Meeting" --label "Priority"  # Analyze with label filter
  python cli.py --focus "DevOps best practices" --separate-files  # Combine flags
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
        help='Save each analysis to a separate file (default: save all analyses to one combined file)'
    )
    parser.add_argument(
        '--focus',
        help='Content focus for article generation (default: AI strategy and innovation for business leaders)'
    )

    args = parser.parse_args()

    try:
        # Get start date from args or environment
        start_date = args.start_date or os.getenv('START_DATE', '').strip()
        label = args.label
        separate_files = args.separate_files
        content_focus = args.focus

        if args.list:
            # List mode
            display_banner()
            list_emails_only(start_date, label)

        elif args.email:
            # Direct email analysis mode
            display_banner()
            analyze_specific_email(args.email, start_date, label, separate_files, content_focus)

        else:
            # Interactive mode (default)
            main_menu(label=label, separate_files=separate_files, content_focus=content_focus)

    except KeyboardInterrupt:
        console.print("\n\n[bold blue]Thanks for using Qwilo. If you have improvement ideas, please email them to stephen@synaptiq.ai :)[/bold blue]\n")
        sys.exit(0)
