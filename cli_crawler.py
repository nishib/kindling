#!/usr/bin/env python3
"""CLI tool for managing the competitor intelligence crawler.

Usage:
    python cli_crawler.py discover [--priority=1]     # Show discovered sources
    python cli_crawler.py crawl [--priority=1] [--max-urls=5]  # Run crawl
    python cli_crawler.py events [--limit=20]         # Show recent events
    python cli_crawler.py status                      # Show crawl status
    python cli_crawler.py competitors                 # List all competitors
"""

import sys
import argparse
from datetime import datetime
from typing import Optional

from database import get_db
from competitor_sources import (
    get_active_competitors,
    get_all_sources,
    crawl_sources,
    get_recent_events,
)


def cmd_discover(args):
    """Show all discovered sources grouped by competitor."""
    print(f"\n🔍 Discovering sources (priority <= {args.priority})...\n")

    sources = get_all_sources(max_priority=args.priority)

    # Group by competitor
    by_comp = {}
    for src in sources:
        if src.competitor not in by_comp:
            by_comp[src.competitor] = []
        by_comp[src.competitor].append(src)

    for comp_name, comp_sources in sorted(by_comp.items()):
        print(f"📊 {comp_name} ({len(comp_sources)} sources)")
        for src in comp_sources:
            print(f"   [{src.source_type:15}] {src.label[:60]}")
            print(f"   {'':17} {src.url}")
        print()

    print(f"✅ Total: {len(sources)} sources from {len(by_comp)} competitors\n")


def cmd_crawl(args):
    """Run a crawl and show results."""
    print(f"\n🚀 Starting crawl (priority <= {args.priority}, max_urls={args.max_urls or 'unlimited'})...\n")

    db = next(get_db())
    try:
        stats = crawl_sources(db, max_urls=args.max_urls, max_priority=args.priority)

        print(f"\n📈 Crawl Results:")
        print(f"   Events created:   {stats['events_created']}")
        print(f"   Sources crawled:  {stats['sources_crawled']}")
        print(f"   Sources failed:   {stats['sources_failed']}")
        print(f"   Duration:         {stats['duration_seconds']}s")
        print(f"   Competitors:      {', '.join(stats['competitors'])}")

        if stats['events_created'] > 0:
            print(f"\n✅ Success! {stats['events_created']} new capability events detected.\n")
        else:
            print(f"\n✅ Crawl complete. No new changes detected.\n")

    except Exception as e:
        print(f"\n❌ Error during crawl: {e}\n")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def cmd_events(args):
    """Show recent capability events."""
    print(f"\n📰 Recent Capability Events (limit={args.limit})...\n")

    db = next(get_db())
    try:
        events = get_recent_events(db, limit=args.limit)

        if not events:
            print("   No events found. Run a crawl first!\n")
            return

        for i, event in enumerate(events, 1):
            print(f"{i}. [{event['competitor']:20}] {event['theme']:20} | {event['change_type']}")
            print(f"   {event['claim']}")
            print(f"   📅 {event['created_at']}")

            if args.verbose:
                print(f"\n   Beginner Summary:")
                for bullet in event['beginner_summary']:
                    print(f"      • {bullet}")
                print(f"\n   Evidence: {event['evidence_url']}")

            print()

    finally:
        db.close()


def cmd_status(args):
    """Show crawler status and stats."""
    print(f"\n📊 Crawler Status\n")

    db = next(get_db())
    try:
        from sqlalchemy import select, func
        from models import IntelEvent, SyncState

        # Get total events
        total_events = db.query(func.count(IntelEvent.id)).scalar()

        # Get last crawl time from state
        state_row = db.get(SyncState, "competitor_source_state")
        if state_row:
            last_crawl = state_row.updated_at
            print(f"   Last crawl:      {last_crawl}")
        else:
            print(f"   Last crawl:      Never")

        print(f"   Total events:    {total_events}")

        # Get events by competitor
        stmt = (
            select(IntelEvent.competitor, func.count(IntelEvent.id))
            .group_by(IntelEvent.competitor)
            .order_by(func.count(IntelEvent.id).desc())
        )
        results = db.execute(stmt).all()

        if results:
            print(f"\n   Events by competitor:")
            for comp, count in results:
                print(f"      {comp:25} {count:4} events")

        # Get events by theme
        stmt = (
            select(IntelEvent.theme, func.count(IntelEvent.id))
            .group_by(IntelEvent.theme)
            .order_by(func.count(IntelEvent.id).desc())
            .limit(10)
        )
        results = db.execute(stmt).all()

        if results:
            print(f"\n   Top themes:")
            for theme, count in results:
                print(f"      {theme:25} {count:4} events")

        print()

    finally:
        db.close()


def cmd_competitors(args):
    """List all competitors with priority and status."""
    print(f"\n🏢 Registered Competitors\n")

    competitors = get_active_competitors(max_priority=3)

    print(f"   {'Name':25} {'Category':15} {'Priority':10} {'Status':10}")
    print(f"   {'-'*25} {'-'*15} {'-'*10} {'-'*10}")

    for comp in competitors:
        status = "✓ Enabled" if comp.enabled else "✗ Disabled"
        priority_mark = "⭐" * comp.priority
        print(f"   {comp.name:25} {comp.category:15} {priority_mark:10} {status:10}")

    print(f"\n   Total: {len(competitors)} competitors")
    print(f"   Priority 1 (⭐): Top 5 competitors")
    print(f"   Priority 2 (⭐⭐): Mid-tier competitors")
    print(f"   Priority 3 (⭐⭐⭐): Additional competitors\n")


def main():
    parser = argparse.ArgumentParser(
        description="Competitor Intelligence Crawler CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_crawler.py discover                    # Show all top 5 competitor sources
  python cli_crawler.py discover --priority=3       # Show all competitor sources
  python cli_crawler.py crawl                       # Crawl top 5 competitors
  python cli_crawler.py crawl --max-urls=5          # Test crawl (5 URLs only)
  python cli_crawler.py events                      # Show recent capability events
  python cli_crawler.py events --limit=50 -v        # Show 50 events with details
  python cli_crawler.py status                      # Show crawler statistics
  python cli_crawler.py competitors                 # List all competitors
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Discover command
    discover_parser = subparsers.add_parser("discover", help="Show discovered sources")
    discover_parser.add_argument(
        "--priority",
        type=int,
        default=1,
        help="Max priority level (1=top 5, 2=mid-tier, 3=all)"
    )

    # Crawl command
    crawl_parser = subparsers.add_parser("crawl", help="Run a crawl")
    crawl_parser.add_argument(
        "--priority",
        type=int,
        default=1,
        help="Max priority level (1=top 5, 2=mid-tier, 3=all)"
    )
    crawl_parser.add_argument(
        "--max-urls",
        type=int,
        default=None,
        help="Limit number of URLs to crawl (for testing)"
    )

    # Events command
    events_parser = subparsers.add_parser("events", help="Show recent events")
    events_parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of events to show"
    )
    events_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed event information"
    )

    # Status command
    status_parser = subparsers.add_parser("status", help="Show crawler status")

    # Competitors command
    competitors_parser = subparsers.add_parser("competitors", help="List all competitors")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "discover": cmd_discover,
        "crawl": cmd_crawl,
        "events": cmd_events,
        "status": cmd_status,
        "competitors": cmd_competitors,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
